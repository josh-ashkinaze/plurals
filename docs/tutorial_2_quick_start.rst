Quick Start Guide
=================

Installation
------------

.. code-block:: bash

    pip install plurals

Set API keys
------------

Set your API keys as environment variables.

.. code-block:: python

        import os

        os.environ["OPENAI_API_KEY"] = 'yourkey'
        os.environ["ANTHROPIC_API_KEY"] = 'yourkey'


Example combining ANES integration, Moderators, and different Structures
------------------------------------------------------------------------

We first start with a ``Chain`` structure, which is just a sequence of Agents who process tasks sequentially.
Each Agent sees the prior Agents' response(s).

- Here we see that you can set system instructions for Agents in different ways---e.g.: relying on American National Election Studies (ANES) for personas, setting them manually, or no system instructions.

- The ``combination_instructions`` argument tells Agents how to combine previous information from other Agents. Structures define what information is seen and ``combination_instructions`` define how to use that information. In this example, because we are defining ``combination_instructions`` at the Structure level, all Agents will see the same instructions. Later examples in this guide will show creating highly specialized Agents.

Chain
~~~~~


.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Chain, Moderator, Ensemble, Debate, Graph

    task = "What is a novel and feasible way to reduce carbon emissions? Answer in 50 words only."


    # Set system instructions directly
    agent1 = Agent(system_instructions="You are an expert behavioral scientist.", model="gpt-4o")

    # A random citizen from ANES is drawn and their demographics are used as the persona,
    # with a persona_template (which gives more instructions to the model on how to enact the persona)
    # for ANES
    agent2 = Agent(persona="random", persona_template='anes', model="gpt-4o")

    # One Agent using default settings (i.e: no custom system instructions, uses default API settings)
    agent3 = Agent(model='gpt-4o-mini')

    # Create a Moderator with a default template
    moderator = Moderator(persona="default", model="gpt-4-turbo")

    # Put Agents in a Chain and define custom combination instructions. These instructions are added
    # to the user prompt when the Agent is processing the task and prior responses are in view.
    chain = Chain(
        agents=[agent1, agent2, agent3],
        moderator=moderator,
        task=task,
        combination_instructions="Critique and revise previous responses: <start>${previous_responses}</end>"
    )
    chain.process()
    print(chain.final_response)

Once we defined our Agents and tasks we could have ran different structures, too.

Ensemble
~~~~~~~~

Here, no responses are shared between Agents. They all process the task independently. Ensembles are useful for tasks
where responses are not dependent on each other, and perhaps we just want a moderator to summarize a bunch of LLM responses.

.. code-block:: python

    ensemble = Ensemble(
        agents=[agent1, agent2, agent3],
        moderator=moderator,
        task=task
    )
    ensemble.process()
    for response in ensemble.responses:
        print(response)

Debate
~~~~~~

We could simulate a debate where agents go back and forth 3 times. It's best to use the `debate` combination instructions for debates.
This example also shows how Agents can have their own tasks, which can even be adversarial. This is a toy example to start, though our
paper leverages the ability to customize Agent goals for creating resonant messaging.

.. code-block:: python

    agent1 = Agent(
        task = "Convince the other Agent that cats are better than dogs.",
        model="gpt-4o"
    )

    agent2 = Agent(
        task = "Convince the other Agent that dogs are better than cats.",
        model="gpt-4-turbo"
    )

    debate = Debate(
        agents=[agent1, agent2],
        cycles=3,  # go back and forth 3 times
        combination_instructions='debate'  # combination instructions optimized for debates
    )
    debate.process()

    for response in debate.responses:
        print(response)

Graph
~~~~~

We could simulate a graph where agents interact in a directed acyclic graph (DAG) structure where an edge A->B means A's response is visible to B.

- Here, we use the dictionary initialization method to define the agents and edges.

- We also pass in custom combination instructions, which are special instructions that are only visible when prior responses are in the agent's view.

- We customize the moderator instructions as well.

.. code-block:: python

    task = "What is an innovative way to reduce carbon emissions? Answer in 50 words."

    agent_dict = {
        'liberal': Agent(ideology="liberal", model="gpt-4o"),
        'random': Agent(persona="random", model="gpt-4o"),
        'default': Agent(model='gpt-4')
    }


    edges = [
        ('default', 'liberal'),
        ('default', 'random'),
    ]

    moderator = Moderator(
        model="gpt-4o",
        combination_instructions="Return the responses that are both innovative and feasible: <start>${previous_responses}</end>"
    )

    graph = Graph(
        agents=agent_dict,
        edges=edges,
        task=task,
        combination_instructions="Critique previous responses and then improve them: <start>${previous_responses}</end>",
        moderator=moderator
    )


