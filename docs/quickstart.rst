Quick Start
===========

Welcome to Plurals, a powerful package for multi-agent, persona-based, pluralistic AI deliberation. This guide will walk you through the main components of Plurals: Agents, Structures, Moderators, and how to inspect output.

Installation
------------

Install Plurals with pip:

.. code-block:: bash

   pip install plurals

Setting Up
----------

First, let's import the necessary modules and set up our API keys:

.. code-block:: python

   from plurals.agent import Agent
   from plurals.deliberation import Chain, Ensemble, Debate, Graph, Moderator
   import os

   # Set your API keys as environment variables
   os.environ["OPENAI_API_KEY"] = 'your_openai_key_here'
   os.environ["ANTHROPIC_API_KEY"] = 'your_anthropic_key_here'

1. Agents
---------

Agents are the core of Plurals. They can be created with various personas and configurations.

Basic Agent
~~~~~~~~~~~

.. code-block:: python

   # Create a basic agent
   basic_agent = Agent(model='gpt-4o', task="Explain the importance of renewable energy.")
   response = basic_agent.process()
   print(response)

   # This will provide a straightforward explanation of renewable energy's importance.

Agent with Custom Persona
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Create an agent with a custom persona
   eco_warrior = Agent(
       persona="You are an passionate environmental activist",
       model='gpt-4o',
       task="Argue for immediate action on climate change."
   )
   eco_response = eco_warrior.process()
   print(eco_response)

   # This will produce a fervent argument for climate action from an activist's perspective.

ANES-based Agent
~~~~~~~~~~~~~~~~

.. code-block:: python

   # Create an agent based on ANES data
   anes_agent = Agent(
       ideology="moderate",
       model='gpt-4o',
       task="What's your view on government spending?"
   )
   anes_response = anes_agent.process()
   print("Persona:", anes_agent.persona)
   print("Response:", anes_response)

   # This will show a moderate's perspective on government spending, based on real demographic data.

2. Structures
-------------

Structures in Plurals allow for complex interactions between multiple agents.

Chain Structure
~~~~~~~~~~~~~~~

.. code-block:: python

   # Create a chain of agents
   agents = [
       Agent(persona='an optimistic futurist', model='gpt-4o'),
       Agent(persona='a cautious ethicist', model='gpt-4o'),
       Agent(persona='a pragmatic engineer', model='gpt-4o')
   ]

   chain = Chain(
       agents,
       task="Discuss the potential impacts of advanced AI on society.",
       combination_instructions="chain"
   )
   chain.process()
   print(chain.final_response)

   # This will produce a nuanced discussion that evolves from optimistic predictions to ethical considerations to practical implementation challenges.

Ensemble Structure
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Create an ensemble of agents
   ensemble_agents = [Agent(persona='random', model='gpt-4o') for _ in range(5)]
   ensemble = Ensemble(
       ensemble_agents,
       task="Propose solutions to urban transportation issues."
   )
   ensemble.process()
   print(ensemble.responses)

   # This will generate multiple diverse solutions to urban transportation from different perspectives.

Debate Structure
~~~~~~~~~~~~~~~~

.. code-block:: python

   # Set up a debate
   pro_agent = Agent(persona="advocate for universal basic income", model='gpt-4o')
   con_agent = Agent(persona="critic of universal basic income", model='gpt-4o')

   debate = Debate(
       [pro_agent, con_agent],
       task="Debate the merits of implementing universal basic income.",
       combination_instructions="debate"
   )
   debate.process()
   print(debate.responses)

   # This will produce a point-counterpoint debate on universal basic income.

Graph Structure
~~~~~~~~~~~~~~~

.. code-block:: python

   # Create a DAG structure
   agents = [
       Agent(persona="AI researcher"),
       Agent(persona="Ethicist"),
       Agent(persona="Policymaker"),
       Agent(persona="Public communicator")
   ]

   edges = [(0, 1), (0, 2), (1, 2), (1, 3), (2, 3)]

   graph = Graph(
       agents=agents,
       edges=edges,
       task="Develop guidelines for responsible AI development and deployment."
   )
   result = graph.process()
   print(result)

   # This will produce guidelines that incorporate technical, ethical, policy, and communication considerations.

3. Moderators
-------------

Moderators can oversee and synthesize the outputs of other agents.

Basic Moderator
~~~~~~~~~~~~~~~

.. code-block:: python

   # Create a basic moderator
   moderator = Moderator(
       persona='You are a neutral facilitator',
       model='gpt-4o',
       combination_instructions="default"
   )

   # Use the moderator in a structure
   moderated_chain = Chain(agents, task="Discuss climate change solutions", moderator=moderator)
   moderated_chain.process()
   print(moderated_chain.final_response)

   # This will produce a balanced summary of the agents' discussion on climate change solutions.

Auto-Moderator
~~~~~~~~~~~~~~

.. code-block:: python

   # Create an auto-moderator
   auto_mod = Moderator(system_instructions='auto', model='gpt-4o')

   # Use the auto-moderator in a structure
   auto_mod_ensemble = Ensemble(ensemble_agents, task="Brainstorm innovative education techniques", moderator=auto_mod)
   auto_mod_ensemble.process()
   print(auto_mod_ensemble.final_response)

   # The auto-moderator will generate its own instructions based on the task and synthesize the ensemble's ideas on education techniques.

4. Inspecting Output
--------------------

Plurals provides various ways to inspect the output and inner workings of agents and structures.

Inspecting Agent Output
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   inspection_agent = Agent(ideology="liberal", model='gpt-4o', task="Comment on income inequality.")
   inspection_agent.process()

   print("Agent Info:")
   print(inspection_agent.info)

   print("\nAgent History:")
   print(inspection_agent.history)

   print("\nAgent Responses:")
   print(inspection_agent.responses)

   # This will display detailed information about the agent's configuration, processing history, and responses.

Inspecting Structure Output
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   inspection_chain = Chain(agents, task="Discuss the future of work")
   inspection_chain.process()

   print("Structure Info:")
   print(inspection_chain.info)

   print("\nStructure Responses:")
   print(inspection_chain.responses)

   print("\nFinal Response:")
   print(inspection_chain.final_response)

   # This will show information about the chain structure, individual agent responses, and the final synthesized response.

These examples demonstrate the power and flexibility of Plurals in creating diverse, multi-agent AI interactions. Experiment with different combinations of agents, structures, and moderators to explore the full potential of pluralistic AI deliberation!