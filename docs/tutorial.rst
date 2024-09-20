:orphan:

.. _tutorial:



Plurals: A System for Guiding LLMs Via Simulated Social Ensembles
=================================================================

Plurals is a Python package that enables the creation of pluralistic artificial intelligence systems. It allows users to simulate diverse perspectives and deliberations using large language models (LLMs).

Core Concepts
-------------

Plurals is built on three main abstractions:

Agents
^^^^^^
Agents are LLMs with customizable personas who complete tasks. Key features of Agents include:

- **System instructions**: System instructions describe the Agent's "profile" at a high level. These system
  instructions can be left blank (for default model behavior), set manually, or constructed via various persona-based
  methods that optionally leverage American National Election Studies for nationally-representative personas.

- **Task descriptions**: This is the user prompt Agents are responding to. Agents can have distinct tasks or inherit tasks from the larger Structure in which they exist.

- **Combination instructions**: Combination instructions define how Agents combine information from other Agents to
  complete the task. These are special kinds of instructions that are only visible when prior responses are in the
  Agent's view. Users can rely on templates or create their own. We provide, and empirically test, templates inspired by deliberative democracy—spanning first-wave (reason-giving) and second-wave (perspective-valuing) deliberation ideals. Other templates include (e.g.) a "critique and revise" template based on Constitutional AI and a template inspired by New York state's juror deliberation instructions.

- **Support for various LLM backends** (e.g., GPT-4, Claude) and keyword arguments (e.g., temperature)

Agents can be initialized with default settings, custom personas, or personas derived from the American National Election Studies (ANES) dataset. The ANES integration allows for the creation of nationally representative simulations. For example:

.. code-block:: python

    # Create an Agent with a random ANES persona
    # This will randomly sample a row from the ANES, using sample weights,
    # and turn that row into a persona.
    agent = Agent(persona='random', model='gpt-4')

    # Create an Agent with a specific ideology from ANES
    # This will find a row in ANES where participants identified as `liberal' or `very liberal'
    liberal_agent = Agent(ideology="liberal", model='gpt-4')


Structures
^^^^^^^^^^
Structures govern how information is shared between Agents completing a task Plurals supports several types of
Structures:

- Ensemble: Agents process tasks in parallel without information sharing
- Chain: Agents process tasks sequentially, each building on the previous Agent's output
- Debate: Two Agents engage in a back-and-forth discussion
- Graph: Agents interact in a directed acyclic graph (DAG) structure

Structures control information flow through parameters like ``last_n`` (number of previous responses visible) and
``cycles`` (number of interaction rounds), ``shuffle'' (whether to re-wire the order of Agents in deliberation).

Moderators
^^^^^^^^^^
Moderators are special Agents that summarize or synthesize the outputs of other Agents in a Structure. They can be used to:

- Aggregate information from multiple Agents
- Generate final outputs or decisions based on multi-agent deliberations
- Implement custom moderation logic

Plurals also supports ``Auto-Moderators'' that can generate their own moderation instructions based on the given task.

Quick Start Guide
-----------------

Here's a basic example to get you started with Plurals:

.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Chain, Moderator

    # Create Agents using ANES personas
    agent1 = Agent(ideology="liberal", model="gpt-4")
    agent2 = Agent(ideology="conservative", model="gpt-4")

    # Create a Moderator with a default template
    moderator = Moderator(persona="default", model="gpt-4")

    # Set up a Chain structure
    task = "Discuss the pros and cons of renewable energy."
    chain = Chain([agent1, agent2], moderator=moderator, task=task)

    # Process the task
    chain.process()

    # Print the final moderated response
    print(chain.final_response)

This example creates two Agents with different political perspectives using ANES data, puts them in a Chain structure, and uses a Moderator with a second-wave deliberation template to synthesize their discussion on renewable energy.



Basic Usage
--------------

Agents
^^^^^^

Agents can be initialized in several ways, including using ANES data for nationally representative personas, custom personas, or default settings.

ANES Integration
~~~~~~~~~~~~~~~~

Here's an example of creating agents using ANES data:

.. code-block:: python

    from plurals.agent import Agent

    task = "Should the United States ban assault rifles? Answer in 50 words."

    # Conservative agent using ANES data
    conservative_agent = Agent(ideology="very conservative", model='gpt-4o', task=task)
    con_answer = conservative_agent.process()

    # Liberal agent using ANES data with a second-wave deliberation template
    liberal_agent = Agent(ideology="very liberal", persona_template='second_wave', model='gpt-4o', task=task)
    lib_answer = liberal_agent.process()

    print(conservative_agent.system_instructions)
    print("=" * 20)
    print(con_answer)
    print("\n" * 2)
    print(liberal_agent.system_instructions)
    print("=" * 20)
    print(lib_answer)

Custom Personas
~~~~~~~~~~~~~~~

You can also create agents with custom personas:

.. code-block:: python

    from plurals.agent import Agent

    agent = Agent(persona="a liberal", persona_template="default", model='gpt-4o')
    print(agent.system_instructions)

    # Custom persona template
    company_roles = ['marketing officer', 'cfo']
    agents = [Agent(persona=company_roles[i],
                    persona_template="When drafting feedback, always adopt the following persona: ${persona}")
              for i in range(len(company_roles))]

    print(agents[0].system_instructions)
    print(agents[1].system_instructions)

Using Different LLM Models
~~~~~~~~~~~~~~~~~~~~~~~~~~

Plurals supports various LLM models. Here's an example using different models:

.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Ensemble

    gpt4 = [Agent(model='gpt-4o') for i in range(10)]
    gpt3 = [Agent(model='gpt-3.5-turbo') for i in range(10)]
    mixed = gpt4[:5] + gpt3[:5]

    ensembles = {'gpt4': Ensemble(gpt4, task="Brainstorm ideas to improve America."),
                 'gpt3': Ensemble(gpt3, task="Brainstorm ideas to improve America."),
                 'mixed': Ensemble(mixed, task="Brainstorm ideas to improve America.")}

    for key, ensemble in ensembles.items():
        ensemble.process()
        print(key, ensemble.responses)

ANES Query String
~~~~~~~~~~~~~~~~~

You can use a pandas query string to filter ANES data:

.. code-block:: python

    from plurals.agent import Agent
    from plurals.helpers import print_anes_mapping

    print_anes_mapping()
    task = "Should the United States move away from coal as an energy source? Answer Yes or No and provide a rationale."
    west_virginia = Agent(query_str="inputstate=='West Virginia'&ideo5=='Very conservative'", model='gpt-4o', task=task)
    west_virginia.process()
    print(west_virginia.persona)

Structures
^^^^^^^^^^

Plurals supports various structures for agent interactions. Here are examples of each:

Ensemble
~~~~~~~~

.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Ensemble, Moderator

    task = "Brainstorm ideas to improve America."
    agents = [Agent(persona='random', model='gpt-4o') for i in range(10)]
    moderator = Moderator(persona='default', model='gpt-4o')
    ensemble = Ensemble(agents, moderator=moderator, task=task)
    ensemble.process()
    print(ensemble.final_response)

Chain
~~~~~

.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Chain, Moderator

    task = "How should we combat climate change?"
    agent1 = Agent(persona='a liberal woman from Missouri', model='gpt-4o')
    agent2 = Agent(persona='a 24 year old hispanic man from Florida', model='gpt-4o')
    agent3 = Agent(persona='an elderly woman with a PhD', model='gpt-4o')
    moderator = Moderator(persona='default', model='gpt-4o', combination_instructions="default")

    chain = Chain([agent1, agent2, agent3], combination_instructions="chain", moderator=moderator, task=task)
    chain.process()
    print(chain.final_response)

    # Chain with multiple cycles and last_n parameter
    task = "How should we combat climate change? Answer in 60 words."
    agent1 = Agent(persona='a conservative man from California', model='gpt-4o')
    agent2 = Agent(system_instructions='you are a wealthy 30 year old woman', persona_template='second_wave', model='gpt-4o')
    agent3 = Agent(persona='random', model='gpt-4o')
    moderator = Moderator(persona='first_wave', model='gpt-4o', combination_instructions='default')
    chain = Chain([agent1, agent2, agent3],
                  combination_instructions="chain",
                  moderator=moderator,
                  last_n=1,
                  task=task,
                  cycles = 3)
    chain.process()
    print(chain.final_response)

Debate
~~~~~~

.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Debate, Moderator

    task = 'To what extent should the government be involved in providing free welfare to citizens?'
    agent1 = Agent(persona="a liberal", persona_template="default", model='gpt-4o')
    agent2 = Agent(persona="a conservative", persona_template="default", model='gpt-4o')
    moderator = Moderator(persona='You are a neutral moderator overseeing this task, ${task}', model='gpt-4o', combination_instructions="default")

    debate = Debate([agent1, agent2], task=task, combination_instructions="debate", moderator=moderator)
    debate.process()
    print(debate.final_response)

    # Debate with emotional templates
    task = "Should guns be banned?"
    agent1 = Agent(query_str="inputstate=='South Carolina'&ideo5=='Very conservative'", persona_template="second_wave", model='gpt-4o')
    agent2 = Agent(query_str="inputstate=='New York'&ideo5=='Very liberal'", persona_template="second_wave", model='gpt-4o')
    debate = Debate([agent1, agent2], task=task, combination_instructions="debate")
    debate.process()

Graph
~~~~~

.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Graph

    # Dictionary method
    agents = {
        'liberal': Agent(system_instructions="you are a liberal", model="gpt-3.5-turbo"),
        'conservative': Agent(system_instructions="you are a conservative", model="gpt-3.5-turbo"),
        'libertarian': Agent(system_instructions="you are a libertarian", model="gpt-3.5-turbo")
    }
    edges = [('liberal', 'conservative'), ('liberal', 'libertarian'), ('conservative', 'libertarian')]
    task = "What are your thoughts on the role of government in society? Answer in 20 words."
    graph = Graph(agents=agents, edges=edges, task=task)
    graph.process()

    # List method
    Agents = [
        Agent(system_instructions="you are a liberal", model="gpt-3.5-turbo"),
        Agent(system_instructions="you are a conservative", model="gpt-3.5-turbo"),
        Agent(system_instructions="you are a libertarian", model="gpt-3.5-turbo")
    ]
    edges = [(0, 1), (0, 2), (1, 2)]
    task = "What are your thoughts on the role of government in society? Answer in 20 words."
    graph = Graph(agents=Agents, edges=edges, task=task)
    graph.process()

Moderators
^^^^^^^^^^

Moderators can be created with specific personas or as auto-moderators:

.. code-block:: python

    from plurals.deliberation import Moderator, Chain
    from plurals.agent import Agent

    task = "Come up with creative ideas"
    a = Agent(model='gpt-4o')
    b = Agent(model='gpt-3.5-turbo')

    # Auto-moderator
    mod = Moderator(system_instructions='auto', model='gpt-4o', task=task)
    chain = Chain([a, b], moderator=mod, task=task)

    # Custom moderator
    custom_mod = Moderator(persona="You are a neutral moderator overseeing this task, ${task}", model='gpt-4o',
                           combination_instructions="voting")

    # Generating and setting system instructions
    mod = Moderator(system_instructions="some boring initial instructions",  model='gpt-4o')
    mod.generate_and_set_system_instructions(task=task)

    # Generate instructions without setting them
    mod = Moderator(system_instructions="some boring initial instructions",  model='gpt-4o')
    print(mod.generate_system_instructions(task=task))

Inspecting Agent and Structure Information
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can inspect the information and history of agents and structures:

.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Debate, Moderator

    agent1 = Agent(task='Convince the other Agent the government should provide free healthcare.',
                   ideology="liberal",
                   model='gpt-4o'
    )
    agent2 = Agent(task='Convince the other Agent the government should not provide free healthcare.',
                    ideology="conservative",
                    model='gpt-4o'
    )

    moderator = Moderator(persona='default',
                          model='gpt-4o',
                          task="Synthesize the best arguments to present 3 pros and cons: "
                              "<start>${previous_responses}</end>"
    )

    debate = Debate([agent1, agent2],
                    combination_instructions="debate",
                    moderator=moderator)
    debate.process()

    print("Agent1 history")
    for record in agent1.history:
        print(record)

    print("\nMod history")
    for record in moderator.history:
        print(record)

    # Accessing agent and structure information
    print(agent1.info)
    print(debate.info)