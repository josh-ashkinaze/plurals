Plurals: A Comprehensive Tutorial
=================================

1. Introduction
---------------

1.1 What is Plurals?
^^^^^^^^^^^^^^^^^^^^

Plurals is a powerful Python library designed for creating multi-agent, persona-based, pluralistic AI deliberations. It provides a flexible framework for simulating diverse viewpoints and complex decision-making processes using large language models (LLMs).

At its core, Plurals allows you to create AI agents with distinct personas, organize them into various deliberation structures, and facilitate interactions between these agents to tackle complex problems or generate diverse perspectives on a given topic.

1.2 Key features and concepts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Agents**: The fundamental building blocks of Plurals, representing different personas or viewpoints.
- **Structures**: Define how agents interact and share information (e.g., Ensemble, Chain, Debate, Graph).
- **Moderators**: Special agents that oversee and summarize deliberations.
- **ANES Integration**: Ability to create representative personas based on American National Election Studies data.
- **Customizable Instructions**: Fine-grained control over agent behavior and interaction.

1.3 Use cases and applications
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Plurals can be applied to a wide range of scenarios where diverse perspectives and complex deliberations are valuable:

- Policy analysis and development
- Market research and consumer insights
- Ethical decision-making in technology
- Educational curriculum development
- Scenario planning and risk assessment
- Collaborative problem-solving
- Simulating public opinion on contentious issues

2. Getting Started
------------------

2.1 Installation
^^^^^^^^^^^^^^^^

To install Plurals, use pip:

.. code-block:: bash

   pip install plurals

2.2 Basic setup and configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before using Plurals, you need to set up your API keys for the language models. It's recommended to use environment variables:

.. code-block:: python

   import os

   os.environ["OPENAI_API_KEY"] = 'your_openai_key'
   os.environ["ANTHROPIC_API_KEY"] = 'your_anthropic_key'

2.3 Quick start example
^^^^^^^^^^^^^^^^^^^^^^^

Here's a simple example to get you started with Plurals:

.. code-block:: python

   from plurals.agent import Agent
   from plurals.deliberation import Chain

   # Define a task
   task = "What are the potential economic impacts of implementing a four-day work week?"

   # Create agents with different perspectives
   economist = Agent(persona="You are a macroeconomist specializing in labor markets", model='gpt-4o')
   business_owner = Agent(persona="You are a small business owner with 50 employees", model='gpt-4o')
   union_rep = Agent(persona="You are a labor union representative", model='gpt-4o')

   # Create a chain of agents
   chain = Chain(
       [economist, business_owner, union_rep],
       task=task,
       combination_instructions="Consider the previous response and build upon it, adding your unique perspective."
   )

   # Process the task
   chain.process()

   # Print the final response
   print(chain.final_response)

This example creates three agents with different perspectives, arranges them in a Chain structure, and has them collaboratively analyze the potential economic impacts of a four-day work week.

3. Core Components
------------------

3.1 Agents
^^^^^^^^^^

Agents are the fundamental building blocks in Plurals. Each agent represents a unique perspective or persona in the deliberation process.

3.1.1 Creating agents
~~~~~~~~~~~~~~~~~~~~~

There are several ways to create agents in Plurals:

.. code-block:: python

   from plurals.agent import Agent

   # Basic agent with a simple persona
   basic_agent = Agent(
       persona="You are a financial analyst",
       model='gpt-4o'
   )

   # Agent with specific system instructions
   detailed_agent = Agent(
       system_instructions="You are a cybersecurity expert with 15 years of experience. Provide insights based on current trends and best practices.",
       model='gpt-4o'
   )

   # Agent using ANES data for a representative persona
   anes_agent = Agent(
       ideology="moderate",
       model='gpt-4o'
   )

3.1.2 System instructions and persona templates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When using a persona, the final system instructions are a combination of the persona and the persona template. The persona template provides a structure for how the persona should be enacted. Here's how it works:

.. code-block:: python

   # Using a predefined template
   template_agent = Agent(
       persona="a veteran police officer",
       persona_template="default",
       model='gpt-4o'
   )
   print("Template Agent Instructions:")
   print(template_agent.system_instructions)

   # Custom template
   custom_template = "As ${persona}, focus on practical, real-world implications in your responses."
   custom_agent = Agent(
       persona="a small business owner",
       persona_template=custom_template,
       model='gpt-4o'
   )
   print("\nCustom Agent Instructions:")
   print(custom_agent.system_instructions)

This approach allows for flexible and nuanced agent creation, combining specific personas with general behavioral guidelines.

3.1.3 ANES integration for representative personas
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Plurals offers integration with the American National Election Studies (ANES) dataset to create more representative personas. This feature allows you to generate agents based on real demographic and ideological data:

.. code-block:: python

   from plurals.agent import Agent
   from plurals.helpers import print_anes_mapping

   # View available ANES variables
   print_anes_mapping()

   # Create an agent based on ANES data
   anes_agent = Agent(
       query_str="inputstate=='California' & ideo5=='Liberal' & age > 30 & age < 50",
       model='gpt-4o'
   )

   print("ANES Agent Persona:")
   print(anes_agent.persona)

This feature is particularly useful for creating diverse, representative panels of agents for deliberations on social or political issues.

3.1.4 Processing tasks
~~~~~~~~~~~~~~~~~~~~~~

Agents can process tasks in two ways:

.. code-block:: python

   task = "What are the potential economic impacts of raising the minimum wage?"

   # Method 1: Task provided during initialization
   agent1 = Agent(ideology="conservative", model='gpt-4o', task=task)
   response1 = agent1.process()

   # Method 2: Task provided during processing
   agent2 = Agent(ideology="liberal", model='gpt-4o')
   response2 = agent2.process(task)

3.1.5 Inspecting agent prompts and responses
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To examine an agent's prompts, responses, and other information:

.. code-block:: python

   import json

   agent = Agent(ideology="moderate", model='gpt-4o')
   agent.process("What are the pros and cons of implementing a flat tax rate?")

   print("Agent Info:")
   print(json.dumps(agent.info, indent=2))

   print("\nAgent History:")
   print(json.dumps(agent.history, indent=2))

   print("\nAgent Responses:")
   print(json.dumps(agent.responses, indent=2))

This capability is crucial for understanding how agents are interpreting and responding to tasks, which can be particularly useful for debugging and refining your multi-agent systems.

3.2 Structures
^^^^^^^^^^^^^^

Structures in Plurals define how agents interact and share information during deliberations. Each structure type offers a unique way of organizing agent interactions to simulate different types of group dynamics.

3.2.1 Ensemble
~~~~~~~~~~~~~~

Ensemble is the simplest structure where agents process tasks in parallel:

.. code-block:: python

   from plurals.agent import Agent
   from plurals.deliberation import Ensemble

   task = "What are the most pressing issues facing the education system today?"

   agents = [
       Agent(persona='a high school teacher', model='gpt-4o'),
       Agent(persona='an education policy researcher', model='gpt-4o'),
       Agent(persona='a parent of school-aged children', model='gpt-4o')
   ]

   ensemble = Ensemble(agents, task=task)
   ensemble.process()

   for i, response in enumerate(ensemble.responses, 1):
       print(f"Agent {i} Response:")
       print(response)
       print()

3.2.2 Chain
~~~~~~~~~~~

Chain allows agents to build upon each other's responses:

.. code-block:: python

   from plurals.agent import Agent
   from plurals.deliberation import Chain

   task = "Analyze the impact of artificial intelligence on job markets over the next decade."

   agents = [
       Agent(persona='an AI researcher', model='gpt-4o'),
       Agent(persona='a labor economist', model='gpt-4o'),
       Agent(persona='a career counselor', model='gpt-4o')
   ]

   chain = Chain(
       agents,
       task=task,
       combination_instructions="Consider the previous agent's ideas and build upon them, adding your unique perspective.",
       last_n=1  # Each agent sees only the immediately preceding response
   )
   chain.process()

   print("Final Chain Response:")
   print(chain.final_response)

3.2.3 Debate
~~~~~~~~~~~~

Debate facilitates back-and-forth discussion between two agents:

.. code-block:: python

   from plurals.agent import Agent
   from plurals.deliberation import Debate

   task = 'Debate the pros and cons of implementing a carbon tax to combat climate change.'

   agent1 = Agent(persona="You are an environmental economist.", model='gpt-4o')
   agent2 = Agent(persona="You are an industry lobbyist for the energy sector.", model='gpt-4o')

   debate = Debate(
       [agent1, agent2],
       task=task,
       combination_instructions="Address the points made by the other participant and present your perspective, focusing on factual arguments.",
       cycles=2  # The debate will go back and forth twice
   )
   debate.process()

   print("Debate Responses:")
   for i, response in enumerate(debate.responses, 1):
       print(f"Round {(i+1)//2}, {'Proponent' if i%2 else 'Opponent'}:")
       print(response)
       print()

3.2.4 Graph
~~~~~~~~~~~

Graph allows for more complex interaction patterns between agents:

.. code-block:: python

   from plurals.agent import Agent
   from plurals.deliberation import Graph

   task = "Analyze the impact of social media on modern politics and suggest ways to mitigate negative effects."

   agents = {
       'political_analyst': Agent(system_instructions="You are a political analyst specializing in media influence.", model="gpt-4o"),
       'social_media_expert': Agent(system_instructions="You are a social media platform architect with insider knowledge.", model="gpt-4o"),
       'psychologist': Agent(system_instructions="You are a social psychologist studying online behavior.", model="gpt-4o"),
       'policy_maker': Agent(system_instructions="You are a seasoned policy maker focused on technology regulation.", model="gpt-4o")
   }

   edges = [
       ('political_analyst', 'social_media_expert'),
       ('political_analyst', 'psychologist'),
       ('social_media_expert', 'policy_maker'),
       ('psychologist', 'policy_maker')
   ]

   graph = Graph(agents=agents, edges=edges, task=task)
   graph.process()

   print("Final Graph Response (Policy Maker's perspective):")
   print(graph.final_response)

Combination Instructions
^^^^^^^^^^^^^^^^^^^^^^^^

Each structure type supports combination instructions, which guide how agents should incorporate previous responses. These can be set using predefined templates or custom instructions with a ``${previous_responses}`` placeholder:

.. code-block:: python

   # Using a predefined template
   chain = Chain(
       agents,
       task=task,
       combination_instructions="chain"  # Uses the default chain template
   )

   # Using custom instructions
   custom_instructions = """
   INSTRUCTIONS
   Analyze the previous responses: ${previous_responses}
   1. Identify key themes and innovative ideas.
   2. Critically evaluate each point for feasibility.
   3. Synthesize the most promising elements.
   4. Introduce at least one novel perspective.
   Your response should build upon and refine the existing ideas.
   """

   chain = Chain(
       agents,
       task=task,
       combination_instructions=custom_instructions
   )

This flexibility allows you to fine-tune how agents interact and build upon each other's ideas within the chosen structure.