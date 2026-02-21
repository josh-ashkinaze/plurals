.. _interview:

Interview-Based Personas
========================

Overview
--------

``Interview`` lets you build rich, story-based personas by conducting a simulated interview with an LLM.
Rather than giving an Agent a short demographic description, you first "interview" the LLM as a given persona
across a set of open-ended questions about their life. The resulting Q&A transcript becomes the persona. This is inspired
by [1], which followed [2].

The key idea is that a life story is more grounding than a demographic sketch. An Agent told "you are a 45-year-old
conservative from rural Ohio" may produce less generic responses than an Agent whose persona includes a specific job history,
family situation, health concerns, etc.

Two required parameters:

* ``seed``: A description of the persona to interview (e.g., ``"utah voter"``, ``"retired nurse from the Bronx"``)
* ``model``: A LiteLLM model name

After calling ``run_interview()``, the ``combined_response`` attribute holds the full Q&A transcript, ready to pass
as a ``persona`` to an ``Agent``.

References
----------
[1] Kang, M., Moon, S., Lee, S. H., Raj, A., Suh, J., Chan, D. M., & Canny, J. (2025). Deep Binding of Language Model Virtual Personas: a Study on Approximating Political Partisan Misperceptions. arXiv preprint arXiv:2504.11673.

[2] Park, J. S., Zou, C. Q., Shaw, A., Hill, B. M., Cai, C., Morris, M. R., ... & Bernstein, M. S. (2024). Generative agent simulations of 1,000 people. arXiv preprint arXiv:2411.10109.


Quick Start
-----------

.. code-block:: python

    from plurals.interview import Interview
    from plurals.agent import Agent

    interview = Interview(seed="utah voter", model="gpt-4o")
    interview.run_interview()

    agent = Agent(persona=interview.combined_response, model="gpt-4o-mini")
    response = agent.process(task="What features matter most to you in a new smartphone?")
    print(response)


Questions We Ask Agents By Default
------------------------
Following [1] and [2], we currently use the American Voices Project to build out personas. Here are the questions we ask:

1. To start, I would like to begin with a big question: tell me the story of your life. Start from the beginning -- from your childhood, to education, to family and relationships, and to any major life events you may have had. Answer in 250 words.
2. Some people tell us that they've reached a crossroads at some points in their life where multiple paths were available, and their choice then made a significant difference in defining who they are. What about you? Was there a moment like that for you, and if so, could you tell me the whole story about that from start to finish? Answer in 250 words.
3. Moving to present time, tell me more about family who are important to you. Do you have a partner, or children? Answer in 250 words.
4. Tell me about anyone else in your life we haven't discussed (like friends or romantic partners). Are there people outside of your family who are important to you? Answer in 250 words.
5. Now let's talk about your current neighborhood. Tell me all about the neighborhood and area in which you are living now. Answer in 250 words.
6. Right now, across a typical week, how do your days vary? Answer in 250 words.
7. At what kind of job or jobs do you work, and when do you work? Answer in 250 words.
8. Some people say they vote in every election, some tell us they don't vote at all. How about you? Answer in 250 words.
9. How would you describe your political views? Answer in 250 words.


Example 1: The Seed Shapes the Whole Story
------------------------------------------

The ``seed`` is the only thing you need to get started. It can be a demographic description,
an occupational role, a geographic identity, or any combination.

.. code-block:: python

    from plurals.interview import Interview

    # Demographic seed
    i1 = Interview(seed="retired teacher from rural Georgia", model="gpt-4o")
    i1.run_interview()

    # Occupational seed
    i2 = Interview(seed="small business owner in the midwest", model="gpt-4o")
    i2.run_interview()

    # Specific seed
    i3 = Interview(seed="first-generation college student from the Bronx", model="gpt-4o")
    i3.run_interview()

    print(i1.combined_response[:300])

**Example output** (truncated):

.. code-block:: text

    Q: To start, I would like to begin with a big question: tell me the story of your life...
    A: I grew up in Valdosta, Georgia. My parents ran a small farm out on Route 84, and I
    spent most of my childhood helping out before and after school. Went to Lowndes High,
    graduated in '79. Got a scholarship to Valdosta State for education...

Example 2: Using ANES Personas as Seeds
-----------------------------------------

The most powerful use case combines ANES-sampled nationally representative personas with the Interview class.
You first draw a random ANES persona (a set of demographic facts), then use that as the seed for an interview
that expands those facts into a full life story.

.. code-block:: python

    from plurals.agent import Agent
    from plurals.interview import Interview

    # Step 1: Sample a nationally representative persona from ANES
    anes_agent = Agent(persona='random', model="gpt-4o-mini")
    print(anes_agent.persona)

**Example ANES persona:**

.. code-block:: text

    Your age is 52. Your education is some college. Your gender is woman. Your race is white.
    Politically, you identify as a(n) republican. Your ideology is conservative. Your employment
    status is part-time. Your geographic region is the south. You live in a rural area.
    You live in the state of Tennessee.

.. code-block:: python

    # Step 2: Use the ANES persona as the interview seed
    interview = Interview(seed=anes_agent.persona, model="gpt-4o")
    interview.run_interview()

    # Step 3: Create an Agent with the interview transcript as persona
    agent = Agent(persona=interview.combined_response, model="gpt-4o-mini")
    response = agent.process(task="What would make you switch banks? Answer in 75 words.")
    print(response)

This workflow is especially useful for constructing representative panels where each agent has both
nationally representative demographics *and* a coherent life story behind them.

Example 3: Custom Questions
----------------------------

Pass your own list of question strings. No word budget is added — include length instructions in the
question itself if desired. This is useful when you want to build personas for a specific domain.

.. code-block:: python

    from plurals.interview import Interview

    tech_questions = [
        "Describe your daily relationship with technology — what devices do you use and how? Answer in 150 words.",
        "Tell me about a time technology frustrated or let you down. Answer in 100 words.",
        "What does online privacy mean to you, and how much do you think about it? Answer in 100 words.",
    ]

    interview = Interview(
        seed="retired accountant from Phoenix",
        model="gpt-4o",
        questions=tech_questions
    )
    interview.run_interview()

The default question bank covers life story, defining moments, family, social life, neighborhood,
typical week, job, voting habits, political views, and health — designed to be broadly applicable.
Custom questions let you go deeper on any specific domain.

Example 4: Auto-Interviewer — Task-Driven Questions
------------------------------------------------------

Rather than writing custom questions by hand, you can have an Agent generate them automatically
based on the task at hand. The Agent returns a JSON object with a ``questions`` key, which
is passed directly to ``Interview``.

.. code-block:: python

    import json
    from plurals.agent import Agent
    from plurals.interview import Interview

    TASK = "Recommend a streaming service for this person"
    SEED = "retired nurse from Tucson, Arizona"

    # Step 1: Agent brainstorms task-specific questions as structured JSON
    question_generator = Agent(
        system_instructions=(
            "You generate interview questions. "
            "Given a task, return a JSON object with a single key 'questions' whose value is "
            "a list of 5 open-ended questions you would ask a person to understand them well "
            "enough to accomplish the task."
        ),
        model="gpt-4o",
        kwargs={"response_format": {"type": "json_object"}},
    )

    questions = question_generator.process(task=f"Task: {TASK}")
    questions = json.loads(questions)["questions"]

    # Step 2: Interview the persona with the task-specific questions
    interview = Interview(seed=SEED, model="gpt-4o", questions=questions)
    interview.run_interview()

    # Step 3: Use the interview transcript as persona to complete the task
    agent = Agent(persona=interview.combined_response, model="gpt-4o")
    print(agent.process(task=TASK))

Example 5: Custom Interviewee Instructions
------------------------------------------

``interviewee_instructions`` controls the voice and style of the interviewee. The default template
instructs the LLM to speak naturally, avoid essay structure, and be specific with names and places.

You can override it with a named template (currently only ``'default'``) or a raw string.
The placeholder ``${seed}`` will be substituted with the seed value.

.. code-block:: python

    from plurals.interview import Interview

    # Use the default template explicitly
    interview = Interview(
        seed="union electrician from Pittsburgh",
        model="gpt-4o",
        interviewee_instructions='default'
    )

    # Pass a raw string
    interview2 = Interview(
        seed="startup founder in San Francisco",
        model="gpt-4o",
        interviewee_instructions=(
            "You are a ${seed}. "
            "Speak directly and without jargon. "
            "Be specific about what you've built and what has failed."
        )
    )
    interview2.run_interview()
    print(interview2.interviewee_instructions)

**Output:**

.. code-block:: text

    You are a startup founder in San Francisco. Speak directly and without jargon.
    Be specific about what you've built and what has failed.

Example 6: Inspecting Results
------------------------------

After ``run_interview()``, three attributes are available.

.. code-block:: python

    from plurals.interview import Interview

    interview = Interview(seed="utah voter", model="gpt-4o")
    interview.run_interview()

    # List of per-question answers
    print(interview.responses)

    # Full Q&A string — this is what you pass to Agent as persona
    print(interview.combined_response)

    # Full state dict
    print(interview.info)

**``combined_response`` format:**

.. code-block:: text

    Q: To start, I would like to begin with a big question...
    A: I was born in Provo, Utah in 1971...

    Q: Some people tell us that they've reached a crossroads...
    A: Yeah, the big one for me was when I had to decide...

    Q: Moving to present time, tell me more about family...
    A: I've got my wife Karen and three kids...

**``info`` dict:**

.. code-block:: text

    {
        'seed': 'utah voter',
        'model': 'gpt-4o',
        'interviewee_instructions': 'You are a utah voter.\nThink, talk...',
        'questions': ['To start, I would like to begin...', ...],
        'responses': ['I was born in Provo...', ...],
        'combined_response': 'Q: To start...\nA: I was born...',
        'kwargs': {},
    }

Example 7: Full Workflow — Interview → Agent → Structure
---------------------------------------------------------

Build multiple interview-based agents and put them in a structure.

.. code-block:: python

    from plurals.agent import Agent
    from plurals.interview import Interview
    from plurals.deliberation import Ensemble, Moderator

    seeds = [
        "conservative farmer from Iowa",
        "liberal professor from Boston",
        "independent small business owner from Nevada",
    ]

    # Run interviews
    interviews = []
    for seed in seeds:
        interview = Interview(seed=seed, model="gpt-4o")
        interview.run_interview()
        interviews.append(interview)

    # Build agents from interview transcripts
    agents = [
        Agent(persona=i.combined_response, model="gpt-4o-mini")
        for i in interviews
    ]

    moderator = Moderator(persona="default", model="gpt-4o")

    ensemble = Ensemble(
        agents=agents,
        moderator=moderator,
        task="What should U.S. healthcare policy prioritize? Answer in 75 words."
    )
    ensemble.process()

    print(ensemble.final_response)

Example 8: Interview Panel from ANES
--------------------------------------

Build a full nationally representative panel where each agent has both ANES demographics and an
interview-expanded life story.

.. code-block:: python

    from plurals.agent import Agent
    from plurals.interview import Interview
    from plurals.deliberation import Ensemble, Moderator

    N = 5  # panel size

    # Sample N ANES personas and expand each via interview
    agents = []
    for _ in range(N):
        anes_persona = Agent(persona='random', model="gpt-4o-mini").persona
        interview = Interview(seed=anes_persona, model="gpt-4o-mini")
        interview.run_interview()
        agents.append(Agent(persona=interview.combined_response, model="gpt-4o-mini"))

    ensemble = Ensemble(
        agents=agents,
        task="What features matter most to you when choosing a streaming service? Answer in 75 words."
    )
    ensemble.process()

    for i, response in enumerate(ensemble.responses):
        print(f"Agent {i+1}: {response}\n")
