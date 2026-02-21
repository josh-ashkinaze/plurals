import warnings
from typing import Any, Dict, List, Optional, Union

from litellm import completion

from plurals.helpers import load_yaml, SmartString

_SEPARATOR = "---SEP---"


class Interview:
    """
    Conducts a batched interview with an LLM to build out a persona's life story.

    The LLM is prompted to roleplay as ``seed`` and answer all interview questions
    in a single API call. Answers are separated by a sentinel string and parsed into
    individual responses, which are also joined into a combined Q&A string suitable
    for use as an ``Agent`` persona.

    Args:
        seed (str): Description of the persona being interviewed (e.g., "utah voter").
        model (str): LiteLLM model name (e.g., "gpt-4o").
        questions (str or list[str]): ``'default'`` to use the built-in question bank
            from ``instructions.yaml`` (word budgets already embedded), or a plain
            list of question strings.
        interviewee_instructions (str): Controls the voice and style of the interviewee.
            Pass ``'default'`` to use the built-in template from ``instructions.yaml``
            (which includes plain language, conversational tone, and guidance to speak
            naturally rather than in essay form), or pass any raw string. The placeholder
            ``${seed}`` will be substituted with the seed value.
        **kwargs: Additional keyword arguments forwarded to ``litellm.completion``
            (e.g., ``temperature``, ``max_tokens``).

    Attributes:
        interviewee_instructions (str): The resolved system prompt used in the interview.
        responses (list[str] or None): Per-question answers after ``run_interview()``.
        combined_response (str or None): Full Q&A string after ``run_interview()``,
            ready to pass as ``persona`` to an ``Agent``.

    **Examples:**

        **Basic usage**: Run the default interview and feed the result into an Agent.

        .. code-block:: python

            from plurals.interview import Interview
            from plurals.agent import Agent

            interview = Interview(seed="utah voter", model="gpt-4o")
            interview.run_interview()

            agent = Agent(persona=interview.combined_response, model="gpt-4o-mini")
            agent.process(task="How do you feel about immigration policy?")

        **Different seeds**: The seed shapes the entire persona — try anything from
        demographic descriptions to occupational roles.

        .. code-block:: python

            # A broad demographic seed
            interview = Interview(seed="retired teacher from rural Georgia", model="gpt-4o")
            interview.run_interview()

            # A more specific seed
            interview2 = Interview(seed="first-generation college student from the Bronx", model="gpt-4o")
            interview2.run_interview()

            # A role-based seed
            interview3 = Interview(seed="small business owner in the midwest", model="gpt-4o")
            interview3.run_interview()

        **Custom questions**: Pass your own list of question strings. No word budget
        is added — include any length instructions in the question itself if desired.

        .. code-block:: python

            my_questions = [
                "Tell me about your relationship with technology and social media.",
                "How has your community changed over the past decade?",
                "What does financial security mean to you? Answer in 150 words.",
            ]

            interview = Interview(seed="suburban parent", model="gpt-4o", questions=my_questions)
            interview.run_interview()

        **Custom interviewee instructions**: Override the default voice/style prompt.
        The ``${seed}`` placeholder is substituted with the seed value.

        .. code-block:: python

            # Use a named template from instructions.yaml (currently only 'default')
            interview = Interview(seed="utah voter", model="gpt-4o", interviewee_instructions='default')

            # Or pass a raw string — ${seed} will be substituted
            interview = Interview(
                seed="retired steelworker from Pittsburgh",
                model="gpt-4o",
                interviewee_instructions="You are a ${seed}. Be blunt and use working-class language.",
            )
            interview.run_interview()
            print(interview.interviewee_instructions)
            # You are a retired steelworker from Pittsburgh. Be blunt and use working-class language.

        **Passing model kwargs**: Control model behavior with any LiteLLM-supported
        keyword arguments.

        .. code-block:: python

            interview = Interview(
                seed="progressive activist from Seattle",
                model="gpt-4o",
                temperature=0.9,
                max_tokens=4000,
            )
            interview.run_interview()

        **Inspecting results**: After ``run_interview()``, you can access per-question
        answers, the full Q&A string, or the complete info dict.

        .. code-block:: python

            interview = Interview(seed="utah voter", model="gpt-4o")
            interview.run_interview()

            # List of answers, one per question
            print(interview.responses)

            # Full Q&A string (what gets passed to Agent as persona)
            print(interview.combined_response)

            # Full state dict
            print(interview.info)

        .. code-block:: text

            {
                'seed': 'utah voter',
                'model': 'gpt-4o',
                'interviewee_instructions': 'You are a utah voter...',
                'questions': ['To start, I would like to begin...', ...],
                'responses': ['I grew up in Salt Lake City...', ...],
                'combined_response': 'Q: To start...\\nA: I grew up...',
                'kwargs': {},
            }

        **Full workflow**: Interview → Agent → Structure.

        .. code-block:: python

            from plurals.interview import Interview
            from plurals.agent import Agent
            from plurals.deliberation import Ensemble

            # Build two persona-rich agents via interview
            interview1 = Interview(seed="conservative farmer from Iowa", model="gpt-4o")
            interview1.run_interview()

            interview2 = Interview(seed="liberal professor from Boston", model="gpt-4o")
            interview2.run_interview()

            agent1 = Agent(persona=interview1.combined_response, model="gpt-4o-mini")
            agent2 = Agent(persona=interview2.combined_response, model="gpt-4o-mini")

            ensemble = Ensemble([agent1, agent2], task="What should U.S. climate policy look like?")
            ensemble.process()
            print(ensemble.responses)
    """

    def __init__(
        self,
        seed: str,
        model: str,
        questions: Union[str, List[str]] = 'default',
        interviewee_instructions: str = 'default',
        **kwargs,
    ):
        self.seed = seed
        self.model = model
        self.kwargs = kwargs
        self._responses: Optional[List[str]] = None
        self._combined_response: Optional[str] = None

        data = load_yaml('instructions.yaml')

        if questions == 'default':
            self._questions: List[str] = data['interview_questions']
        else:
            self._questions = list(questions)

        templates = data.get('interviewer_system_instructions', {})
        raw_template = templates.get(interviewee_instructions, interviewee_instructions)
        self.interviewee_instructions: str = SmartString(raw_template).format(seed=seed)

    def _build_prompt(self) -> str:
        header = (
            f"Answer each of the following interview questions as a {self.seed}.\n\n"
            f"INSTRUCTIONS\n"
            f"- Be very specific. Use concrete names, places, dates, and experiences rather than generic descriptions. "
            f"For example, name the actual town, the actual job title, the actual people.\n"
            f"- It is okay for your answers to be contradictory, incomplete, or uncertain — real people are.\n"
            f"- Do not repeat the question number or question text in your answer — just give the answer directly.\n"
            f"- Separate each answer with {_SEPARATOR} on its own line, in the same order as the questions.\n"
        )
        lines = [header]
        for i, question in enumerate(self._questions, 1):
            lines.append(f"Question {i}: {question}")
        return "\n".join(lines)

    def run_interview(self) -> None:
        """Make a single LLM call with all questions and parse the response."""
        messages = [
            {"role": "system", "content": self.interviewee_instructions},
            {"role": "user", "content": self._build_prompt()},
        ]

        response = completion(model=self.model, messages=messages, **self.kwargs)
        raw_text = response.choices[0].message.content

        parts = [p.strip() for p in raw_text.split(_SEPARATOR)]
        if len(parts) != len(self._questions):
            warnings.warn(
                f"Expected {len(self._questions)} answers but parsed {len(parts)}. "
                "Some questions may be missing or merged."
            )

        self._responses = parts

        qa_pairs = [f"Q: {q}\nA: {a}" for q, a in zip(self._questions, parts)]
        self._combined_response = "\n\n".join(qa_pairs)

    @property
    def responses(self) -> Optional[List[str]]:
        """Per-question answers, available after ``run_interview()``."""
        return self._responses

    @property
    def combined_response(self) -> Optional[str]:
        """Full Q&A string, available after ``run_interview()``."""
        return self._combined_response

    @property
    def info(self) -> Dict[str, Any]:
        """Return the full state of the Interview."""
        if self._combined_response is None:
            warnings.warn("The interview has not been run yet. Call run_interview() first.")
        return {
            "seed": self.seed,
            "model": self.model,
            "interviewee_instructions": self.interviewee_instructions,
            "questions": self._questions,
            "responses": self._responses,
            "combined_response": self._combined_response,
            "kwargs": self.kwargs,
        }
