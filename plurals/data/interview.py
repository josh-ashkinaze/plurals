# plurals/interview.py
from __future__ import annotations

"""
Interview based persona generation utilities.

This module provides the :class:`Interviewer` helper, which runs a multi turn
interview given a short seed description and produces a combined transcript
that can be used as a persona string in :class:`plurals.agent.Agent`.

Typical usage::

    from plurals.interview import Interviewer
    from plurals.agent import Agent

    seed = "utah voter"

    interview = Interviewer(seed=seed, model="gpt-4o")
    interview.run_interview()

    agent = Agent(
        persona=interview.combined_response,
        persona_template="interview",
        model="gpt-4o-mini",
    )
"""

import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Union

from plurals.agent import Agent
import litellm

# Optional: if the app using Plurals relies on .env files, they can call
# load_dotenv() at application startup.
# from dotenv import load_dotenv  # noqa: F401


DEFAULT_QUESTIONS: List[str] = [
    "Tell me the story of your life, from childhood to major life events.",
    "Was there a crossroads that defined who you are? Tell that story.",
    "Who outside of family matters most to you (friends, partners)?",
    "Describe your current neighborhood and area.",
    "Have there been any recent changes to your daily routine?",
    "How would you describe your political views?",
]

#: Simple preset registry. In a later version this can be loaded from YAML.
QUESTIONS_PRESETS: Dict[str, List[str]] = {
    "default": DEFAULT_QUESTIONS,
    # "politics_basic": [...],
    # "identity_deep": [...],
}


@dataclass
class QAItem:
    """
    Single question and answer item from an interview.

    :param question: The question that was asked.
    :type question: str
    :param answer: The model's answer to the question.
    :type answer: str
    """

    question: str
    answer: str


class Interviewer:
    """
    Interview based persona generator that produces a narrative persona string
    compatible with ``Agent(persona=...)``.

    This helper runs a multi turn interview given a short seed description and
    returns a combined interview transcript that can be used as a persona
    in the existing persona templates, for example
    ``persona_template="interview"``.

    Typical usage::

        from plurals.interview import Interviewer
        from plurals.agent import Agent

        seed = "utah voter"

        # Using default questions
        interview = Interviewer(seed=seed, model="gpt-4o")
        interview.run_interview()
        agent = Agent(
            persona=interview.combined_response,
            persona_template="interview",
            model="gpt-4o-mini",
        )

        # Using a named question preset
        interview = Interviewer(
            seed=seed,
            model="gpt-4o",
            questions="default",
        )
        interview.run_interview()
        agent = interview.create_agent(
            persona_template="interview",
            model="gpt-4o-mini",
        )

        # Using custom questions
        questions = ["How old are you?", "What is your name?"]
        interview = Interviewer(
            seed=seed,
            model="gpt-4o",
            questions=questions,
        )
        interview.run_interview()
        agent = interview.create_agent(
            persona_template="interview",
            model="gpt-4o-mini",
        )

    The interview logic is completely separate from the core agent and
    deliberation code. It is an optional preprocessing utility: you can use it
    offline to construct persona transcripts and then inject those into agents.

    :param seed: Short seed or backstory for the persona, for example
                 ``"A 35 year old teacher in Ohio"`` or ``"utah voter"``.
    :type seed: str
    :param questions: Either ``None`` to use the default question list, a string
                      to look up a named preset in :data:`QUESTIONS_PRESETS`,
                      or an explicit list of question strings.
    :type questions: str or list of str or None
    :param model: Model name used with :func:`litellm.completion`.
    :type model: str
    :param kwargs: Extra keyword arguments passed through to
                   :func:`litellm.completion`, for example ``temperature`` or
                   ``max_tokens``.
    :type kwargs: dict or None

    :ivar seed: Seed description used to frame the interview.
    :vartype seed: str
    :ivar model: Model name passed to ``litellm.completion``.
    :vartype model: str
    """

    def __init__(
        self,
        seed: str,
        questions: Optional[Union[str, List[str]]] = None,
        model: str = "gpt-4o-mini",
        kwargs: Optional[Dict[str, Any]] = None,
    ):
        self.seed = seed.strip()
        self.model = model
        self.kwargs: Dict[str, Any] = kwargs or {}

        # Resolve questions according to the rules above.
        self._questions: List[str] = self._resolve_questions(questions)

        self._qa: List[QAItem] = []
        self._combined_response: str = ""
        self._full_text: str = ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run_interview(self) -> None:
        """
        Run the full interview flow.

        This clears any previous state, asks each question in order, and
        populates :pyattr:`responses` and :pyattr:`combined_response`.

        This method does not return anything. Use
        :pyattr:`combined_response` to access the persona string and
        :pyattr:`responses` to inspect individual question and answer pairs.
        """
        self._qa.clear()
        self._combined_response = ""
        self._full_text = ""

        for q in self._questions:
            history_text = self._history_to_text()
            messages = self._build_messages(question=q, history_text=history_text)
            answer = self._ask(messages)
            self._qa.append(QAItem(question=q, answer=answer))

        # Combined response is the full Q and A transcript in text form.
        self._combined_response = self._history_to_text()

        parts: List[str] = []
        parts.append("=== PERSONA SEED ===")
        parts.append(self.seed or "(none)")
        parts.append("")
        parts.append("=== INTERVIEW ===")
        for i, item in enumerate(self._qa, 1):
            parts.append(f"\nQ{i}: {item.question}\nA{i}: {item.answer}")
        parts.append("\n=== COMBINED RESPONSE (Q/A CONCAT) ===")
        parts.append(self._combined_response.strip())
        self._full_text = "\n".join(parts)

    def process(self) -> None:
        """
        Backwards compatible alias for :meth:`run_interview`.
        """
        self.run_interview()

    def save_interview(self, out_path: str) -> str:
        """
        Save the current interview to a JSON file.

        The JSON structure includes:

        - ``seed``
        - ``model``
        - resolved question list
        - question and answer pairs in ``responses``
        - ``combined_response``
        - ``full_text`` which includes the seed, labeled interview and combined text

        :param out_path: Path to the JSON file to write.
        :type out_path: str
        :raises ValueError: If :meth:`run_interview` has not been called yet.
        :return: The path that was written.
        :rtype: str
        """
        if not self._qa and not self._combined_response:
            raise ValueError("Nothing to save. Run run_interview() first.")
        data = self.to_dict(include_full=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return out_path

    def to_dict(self, include_full: bool = False) -> Dict[str, Any]:
        """
        Export the current state to a Python dict.

        Useful for caching, tests, or custom analysis.

        :param include_full: If true, include the ``full_text`` field that
                             contains the seed, labeled interview and combined
                             transcript.
        :type include_full: bool
        :return: A dictionary representation of the interview.
        :rtype: dict
        """
        d: Dict[str, Any] = {
            "seed": self.seed,
            "model": self.model,
            "questions": self._questions[:],
            "responses": [asdict(x) for x in self._qa],
            "combined_response": self._combined_response,
        }
        if include_full:
            d["full_text"] = self._full_text
        return d

    @classmethod
    def from_json(cls, path: str) -> "Interviewer":
        """
        Load an :class:`Interviewer` from a previously saved JSON file.

        This restores:

        - seed
        - model
        - questions
        - responses
        - combined_response
        - full_text

        :param path: Path to a JSON file created by :meth:`save_interview`.
        :type path: str
        :return: A new :class:`Interviewer` instance with state restored.
        :rtype: Interviewer
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        obj = cls(
            seed=data.get("seed", ""),
            model=data.get("model", "gpt-4o-mini"),
            questions=data.get("questions", "default"),
        )
        obj._qa = [QAItem(**item) for item in data.get("responses", [])]
        obj._combined_response = data.get("combined_response", "")
        obj._full_text = data.get("full_text", "")
        return obj

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def responses(self) -> List[QAItem]:
        """
        List of :class:`QAItem` for this interview.

        Each item has:

        - ``question``: the question string
        - ``answer``: the model's answer

        :return: A shallow copy of the internal question and answer list.
        :rtype: list[QAItem]
        """
        return list(self._qa)

    @property
    def combined_response(self) -> str:
        """
        Combined persona narrative string derived from the question and
        answer pairs.

        This is the string that should be passed to ``Agent(persona=...)`` or
        used in the ``persona_template="interview"`` instructions.

        :return: The combined interview transcript as a single string.
        :rtype: str
        """
        return self._combined_response.strip()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolve_questions(
        self,
        questions: Optional[Union[str, List[str]]],
    ) -> List[str]:
        """
        Resolve the questions argument to a concrete list of question strings.

        Rules:

        - ``None``        -> :data:`DEFAULT_QUESTIONS`
        - ``list[str]``   -> returned as is
        - ``str``         -> looked up in :data:`QUESTIONS_PRESETS`

        :param questions: Question configuration passed to ``__init__``.
        :type questions: str or list of str or None
        :return: A concrete list of question strings.
        :rtype: list[str]
        :raises TypeError: If the input type is not supported.
        :raises ValueError: If a preset name is unknown.
        """
        if questions is None:
            return DEFAULT_QUESTIONS[:]

        if isinstance(questions, list):
            return questions

        if isinstance(questions, str):
            preset = QUESTIONS_PRESETS.get(questions)
            if preset is None:
                raise ValueError(f"Unknown interview question preset: {questions!r}")
            return preset[:]

        raise TypeError(
            "questions must be None, a list of strings, or a preset name string"
        )

    def _build_messages(self, question: str, history_text: str) -> List[Dict[str, str]]:
        """
        Construct chat API messages for :func:`litellm.completion`.

        :param question: The current question that should be asked.
        :type question: str
        :param history_text: The formatted history of previous questions and
                             answers that should be provided as context.
        :type history_text: str
        :return: A list of messages compatible with the litellm chat API.
        :rtype: list[dict]
        """
        system = (
            "You are roleplaying the person described below.\n\n"
            f"{self.seed}\n\n"
            "Answer interview questions authentically and consistently with this "
            "background. Be detailed, personal, and natural."
        ).strip()

        user_parts: List[str] = []
        if history_text:
            user_parts.append(history_text)
        user_parts.append(f"Current question: {question}")
        user_parts.append("Provide a detailed, personal response.")
        user_msg = "\n\n".join(user_parts)

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ]

    def _history_to_text(self) -> str:
        """
        Turn the current question and answer history into a plain text block.

        This representation is used both as context for future questions and
        as the base for :pyattr:`combined_response`.

        :return: A plain text representation of the interview so far.
        :rtype: str
        """
        if not self._qa:
            return ""
        lines: List[str] = []
        for i, item in enumerate(self._qa, 1):
            lines.append(f"Q{i}: {item.question}")
            lines.append(f"A{i}: {item.answer}")
        return "\n".join(lines)

    def _ask(self, messages: List[Dict[str, str]]) -> str:
        """
        Invoke the chat model and return the content string.

        Any exception raised by the underlying model call is caught and printed,
        and an empty string is returned so that downstream code can decide how
        to handle failures.

        :param messages: Chat messages passed to :func:`litellm.completion`.
        :type messages: list[dict]
        :return: The content string returned by the model, or an empty string
                 if the call fails.
        :rtype: str
        """
        try:
            resp = litellm.completion(
                model=self.model,
                messages=messages,
                **self.kwargs,
            )
            # litellm 0.21 and later returns resp.choices[0].message.content
            content = getattr(resp.choices[0].message, "content", "")
            return (content or "").strip()
        except Exception as e:
            print("Interviewer generation failed:", e)
            return ""
