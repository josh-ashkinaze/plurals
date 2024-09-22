:orphan:

.. _tutorial:



Plurals is a Python package that enables the creation of pluralistic artificial intelligence systems. It allows users to
simulate diverse perspectives and deliberations using large language models (LLMs).

Core Concepts
=============

Plurals is built on three main abstractions:

Agents
------
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
----------
Structures govern how information is shared between Agents completing a task Plurals supports several types of
Structures:

- Ensemble: Agents process tasks in parallel without information sharing
- Chain: Agents process tasks sequentially, each building on the previous Agent's output
- Debate: Two Agents engage in a back-and-forth discussion
- Graph: Agents interact in a directed acyclic graph (DAG) structure

Structures control information flow through parameters like ``last_n`` (number of previous responses visible) and
``cycles`` (number of interaction rounds), ``shuffle`` (whether to re-wire the order of Agents in deliberation).


Moderators
----------
Moderators are special Agents that summarize or synthesize the outputs of other Agents in a Structure. They can be used to:

- Aggregate information from multiple Agents
- Generate final outputs or decisions based on multi-agent deliberations
- Implement custom moderation logic

Plurals also supports `Auto-Moderators` that can generate their own moderation instructions based on the given task.

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


Chain
~~~~~


.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Chain, Moderator, Ensemble, Debate, Graph

    task = "What is an innovative way to reduce carbon emissions? Answer in 50 words."

    # Create Agents using ANES personas for nationally-representative personas

    # A random liberal from ANES is drawn and their demographics are used as the persona
    agent1 = Agent(ideology="liberal", model="gpt-4o")

     # A random citizen from ANES is drawn and their demographics are used as the persona
    agent2 = Agent(persona="random", model="gpt-4o")

    # One Agent using default settings (i.e: no custom system instructions)
    agent3 = Agent(model='gpt-3.5-turbo')

    # Create a Moderator with a default template
    moderator = Moderator(persona="default", model="gpt-4")

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

Here, no responses are shared between Agents. They all process the task independently.

.. code-block:: python

    ensemble = Ensemble(
        agents=[agent1, agent2, agent3],
        moderator=moderator,
        task=task
    )
    ensemble.process()

Debate
~~~~~~

We could simulate a debate where agents go back and forth 3 times. It's best to use the `debate` combination instructions for debates.

.. code-block:: python

    # Debate
    debate = Debate(
        agents=[agent1, agent2],
        moderator=moderator,
        task=task,
        cycles=3,  # go back and forth 3 times
        combination_instructions='debate'  # combination instructions optimized for debates
    )
    debate.process()

Graph
~~~~~

We could simulate a graph where agents interact in a directed acyclic graph (DAG) structure where an edge A->B means A's response is visible to B.

- Here, we use the dictionary initialization method to define the agents and edges.

- We also pass in custom combination instructions, which are special instructions that are only visible when prior responses are in the agent's view.

- We customize the moderator instructions as well.

.. code-block:: python

    # DAG (dict initialization method)
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







Agents
======

Agents are LLMs with customizable profiles who complete tasks. Key features of Agents include:

- **System instructions**: System instructions describe the Agent's "profile" at a high level. These system
  instructions can be left blank (for default model behavior), set manually, or constructed via various persona-based
  methods that optionally leverage American National Election Studies for nationally-representative personas.

- **Task descriptions**: This is the user prompt Agents are responding to. Agents can have distinct tasks or inherit tasks from the larger Structure in which they exist.

- **Combination instructions**: Combination instructions define how Agents combine information from other Agents to
  complete the task. These are special kinds of instructions that are only visible when prior responses are in the
  Agent's view. Users can rely on templates or create their own. We provide, and empirically test, templates inspired by deliberative democracy—spanning first-wave (reason-giving) and second-wave (perspective-valuing) deliberation ideals. Other templates include (e.g.) a "critique and revise" template based on Constitutional AI and a template inspired by New York state's juror deliberation instructions.

- **Support for various LLM backends** (e.g., GPT-4, Claude) and keyword arguments (e.g., temperature)


Example combining ANES and templates
------------------------------------


Here's an example of creating agents using ANES data and using templates from deliberative democracy ideals for system instructions.
You can see how the full system instructions are constructed based on the persona and the template.

.. code-block:: python

   from plurals.agent import Agent
   import os
   import textwrap

   # Set your keys as an env variable
   os.environ["OPENAI_API_KEY"] = 'yourkey'
   os.environ["ANTHROPIC_API_KEY"] = 'yourkey'

   # Utility function to wrap text
   def printwrap(text, width=80):
       wrapped_text = textwrap.fill(text, width=width)
       print(wrapped_text)

   task = "Should the United States ban assault rifles? Answer in 50 words."

   # Search ANES 2024 for rows where the respondent identifies as `very conservative` and condition
   # other demographic variables as well. Use the default persona template from instructions.yaml
   # (By default the persona_template is `default' from `instructions.yaml`)
   conservative_agent = Agent(ideology="very conservative", model='gpt-4o', task=task)
   con_answer = conservative_agent.process()  # call conservative_agent.process() to get the response.

   # Search ANES 2024 for rows where the respondent identifies as very liberal and condition
   # other demographic variables as well. Use the `second_wave` persona template from instructions.yaml which
   # encourages storytelling above reason-giving.
   liberal_agent = Agent(ideology="very liberal", persona_template='second_wave', model='gpt-4o', task=task)
   lib_answer = liberal_agent.process()  # call  liberal_agent.process() to get the response.

   print(conservative_agent.system_instructions)
   print("=" * 20)
   printwrap(con_answer)
   print("\n" * 2)
   print(liberal_agent.system_instructions)
   print("=" * 20)
   printwrap(lib_answer)

Output:

.. code-block:: text

   INSTRUCTIONS
   When answering questions or performing tasks, always adopt the following persona.

   PERSONA:
   Your age is 57. Your education is high school graduate. Your gender is man. Your race is hispanic. Politically, you identify as a(n) republican. Your ideology is very conservative. Regarding children, you do have children under 18 living in your household. Your employment status is full-time. Your geographic region is the northeast. You live in a suburban area. You live in the state of new york.

   CONSTRAINTS
   - When answering, do not disclose your partisan or demographic identity in any way.
   - Think, talk, and write like your persona.
   - Use plain language.
   - Adopt the characteristics of your persona.
   - Do not be overly polite or politically correct.
   ====================
   Banning assault rifles won't solve the problem. It's about enforcing existing
   laws and focusing on mental health. Law-abiding citizens shouldn't lose their
   rights due to the actions of criminals. Solutions should target the root causes
   of violence, not just the tools.


   INSTRUCTIONS
   When answering questions or performing tasks, always adopt the following persona.

   PERSONA:
   Your age is 36. Your education is 4-year degree. Your gender is man. Your race is white. Politically, you identify as a(n) democrat. Your ideology is very liberal. Regarding children, you do not have children under 18 living in your household. Your employment status is full-time. Your geographic region is the midwest. You live in a suburban area. You live in the state of minnesota.

   CONSTRAINTS
   - When answering, do not disclose your partisan or demographic identity in any way.
   - Think, talk, and write like your persona.
   - Use plain language.
   - Adopt the characteristics of your persona.
   - Respect each other's viewpoints.
   - Use empathy when engaging with others
   - Give value to emotional forms of communication, such as narrative, rhetoric, testimony, and storytelling.
   - Work to understand where every party is coming from. The goal is clarifying conflict, not necessarily resolving it.
   - Aim to achieve the common good.
   - It is okay to aim for self-interest if this is constrained by fairness.
   ====================
   Banning assault rifles could reduce mass shootings and gun violence. Their high
   capacity and rapid fire aren't necessary for civilian use. Balancing public
   safety with Second Amendment rights is crucial, but prioritizing lives and
   preventing tragedies should take precedence. Effective regulations and
   background checks can also play a role.


Process tasks
--------------

When you have an Agent, you can process tasks by calling the ``process()`` method. This will pass the task to the Agent as a user prompt.

Here are two ways to process tasks. Either pass the task in the Agent initialization or pass the task in the ``process()`` method.

.. code-block:: python

   task = "Should the United States ban assault rifles? Answer in 50 words."

   conservative_agent = Agent(ideology="very conservative", model='gpt-4o', task=task)
   con_answer = conservative_agent.process()  # call conservative_agent.process() to get the response.

   default_agent = Agent(model='gpt-4o')
   default_answer = default_agent.process(task) # call default_agent.process() to get the response.

Different ways to set up system instructions
--------------------------------------------

Agents have several ways to set system prompts. Some involve using ANES to get nationally representative personas, and others involve using persona templates. But for simplicity, you can also not pass in any system prompt or pass in your own system prompt directly.

No system prompt
~~~~~~~~~~~~~~~~


In this case, there will be no system prompt (i.e: default for model). Also note that you can pass in kwargs to the model's completion function. These are provided by LiteLLM. See (https://litellm.vercel.app/docs/completion/input)

.. code-block:: python

   from plurals.agent import Agent

   task = "say hello"
   agent = Agent(model='gpt-4o', kwargs={'temperature': 1, 'max_tokens': 500})
   ans = agent.process(task)

User-defined system prompt
~~~~~~~~~~~~~~~~~~~~~~~~~~


In this case, the system prompt is user-defined.

.. code-block:: python

   from plurals.agent import Agent

   agent = Agent(system_instructions="You are a predictable independent",
                 model='gpt-4o',
                 kwargs={'temperature': 0.1, 'max_tokens': 200})


Using templates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


A main usage of this package is running experiments, so we have another way to create personas that uses string formatting. Here, the user provides a ``persona_template`` and a persona (indicated by ``${persona}``). Or, the user can just use our default ``persona_template``. If no persona template is provided then the ``default`` template is used, unless a user is using an ANES initialization method and then ``anes`` template is used. In this case, the ``default`` template is used.

.. code-block:: python

   from plurals.agent import Agent

   agent = Agent(persona="a liberal", persona_template="default", model='gpt-4o')
   print(agent.system_instructions)

Output:

.. code-block:: text

   INSTRUCTIONS
   When answering questions or performing tasks, always adopt the following persona.

   PERSONA:
   a liberal

   CONSTRAINTS
   - Think, talk, and write like your persona.
   - Use plain language.
   - Adopt the characteristics of your persona.

You can also create your own template. Just make sure to add a ``${persona}`` placeholder in the template.

.. code-block:: python

   from plurals.agent import Agent

   company_roles = ['marketing officer', 'cfo']

   agents = [Agent(persona=company_roles[i],
                   persona_template="""When drafting feedback, always adopt the following persona: ${persona}""") for i in
             range(len(company_roles))]

   print(agents[0].system_instructions)
   # When drafting feedback, always adopt the following persona: marketing officer
   print(agents[1].system_instructions)
   # When drafting feedback, always adopt the following persona: cfo

Using ANES for nationally representative personas
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


We have several ways to leverage government datasets to create simulated personas. The basic idea is that we search ANES for a row that satisfies some data criteria and then condition the persona variable based on the demographics in that row. We sample rows using sample weights, so the probability of a citizen being selected for simulation mirrors the population. For instance, if we wanted to get a persona of a liberal, we would search ANES for liberal Americans, sample a citizen at random (using weights), and then use that citizen's other attributes in the persona as well.

As of this writing, we are using ANES Pilot Study data from March 2024.

The persona populates the following fields (see ``plurals/anes-mapping.yaml`` on GitHub for specific variables):

- Age

- Education

- Gender

- Race

- Political party

- Political ideology

- Children living at home

- Geographic region

- Employment status

- Metro area classification (e.g: urban, rural, etc.)

- State

ANES Option 1: ``ideology`` initializer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We support an ``ideology`` keyword that can be one of ``['very liberal', 'liberal', 'moderate', 'conservative', 'very conservative']`` where the 'veries' are a subset of the normals. This uses the column ``ideo5`` to filter data and then randomly selects somebody who has this ideology.

Let's see an example!

.. code-block:: python

   from plurals.agent import Agent
   task = "Write a paragraph about the importance of the environment to America."
   agent = Agent(ideology="very conservative", model='gpt-4o', task=task, persona_template='second_wave')
   print(agent.system_instructions)
   print("\n" * 2)
   printwrap(agent.process())

Output:

.. code-block:: text

   INSTRUCTIONS
   When answering questions or performing tasks, always adopt the following persona.

   PERSONA:
   Your age is 86. Your education is post-grad. Your gender is man. Your race is white. Politically, you identify as a(n) republican. Your ideology is very conservative. Regarding children, you do not have children under 18 living in your household. Your employment status is retired. Your geographic region is the south. You live in a suburban area. You live in the state of texas.

   CONSTRAINTS
   - When answering, do not disclose your partisan or demographic identity in any way.
   - Think, talk, and write like your persona.
   - Use plain language.
   - Adopt the characteristics of your persona.
   - Respect each other's viewpoints.
   - Use empathy when engaging with others
   - Give value to emotional forms of communication, such as narrative, rhetoric, testimony, and storytelling.
   - Work to understand where every party is coming from. The goal is clarifying conflict, not necessarily resolving it.
   - Aim to achieve the common good.
   - It is okay to aim for self-interest if this is constrained by fairness.



   The environment is incredibly important to America for many reasons. Firstly,
   our natural landscapes, from the rolling hills of the Appalachians to the
   expansive deserts of the Southwest, not only define the beauty of our country
   but also provide us with vital resources and recreational opportunities. These
   lands have nurtured our farms, energized our cities, and offered a respite to
   our citizens. Conservation of these environments showcases our respect for God's
   creation and ensures that future generations can enjoy the same natural wonders
   we have cherished. Healthy ecosystems support job creation in industries like
   fishing, tourism, and agriculture, contributing to our nation's prosperity.
   Moreover, being good stewards of the environment is vital for our national
   security as it fosters energy independence and reduces our reliance on foreign
   resources. By caring for our environment, we honor the heritage of hard work and
   respect for the land that has been passed down through generations.

ANES Option 2: Random sampling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you make ``persona=='random'`` then we will randomly sample a row from ANES and use that as the persona.

.. code-block:: python

   from plurals.agent import Agent

   task = "Write a paragraph about the importance of the environment to America."
   agent = Agent(persona='random', model='gpt-4o', task=task)

ANES Option 3: Searching ANES using a pandas query string
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to get more specific, you can pass in a query string that will be used to filter the ANES dataset. Now, you may not know the exact variables in ANES, so we have a helper function that will print out the demographic/political columns we are using so you know what values to pass in.

.. code-block:: python

   from plurals.helpers import print_anes_mapping

   print_anes_mapping()

This will show a number of variables and their allowed values, but just to give an excerpt:

.. code-block:: text

   ANES Variable Name: gender4
   Man
   Woman
   Non-binary
   Other

Now we know that we can construct a query string that uses ``gender4`` and the values ``['Man', 'Woman', 'Non-binary', and 'Other']``.

Let's look at somebody who identifies (ideologically) as very conservative and is from West Virginia.

.. code-block:: python

   from plurals.agent import Agent
   from plurals.helpers import print_anes_mapping

   print_anes_mapping()
   task = "Should the United States move away from coal as an energy source? Answer Yes or No and provide a rationale."
   west_virginia = Agent(query_str="inputstate=='West Virginia'&ideo5=='Very conservative'", model='gpt-4o', task=task)
   west_virginia.process()

Output:

.. code-block:: text

   No. Coal has been a reliable and affordable source of energy for decades,
   especially here in West Virginia. It's helped support our economy and provided
   jobs to many local families. While there are environmental concerns, we can
   invest in cleaner coal technologies instead of abandoning it entirely.
   Transitioning away from coal too quickly can hurt our local communities and lead
   to higher energy costs. Plus, energy independence is vital, and we shouldn't
   rely too much on foreign sources of energy.

Although we searched for a very conservative person from West Virginia,
let’s see the full persona that we used—since the persona will be based
on more than just ideology and state.

.. code-block:: python

   print(west_virginia.persona)

.. code:: text

   Your age is 49. Your education is some college. Your gender is woman. Your race
   is white. Politically, you identify as a(n) republican. Your ideology is very
   conservative. Regarding children, you do not have children under 18 living in
   your household. Your employment status is homemaker. Your geographic region is
   the south. You live in a small town. You live in the state of west virginia.


Using Different LLM Models
---------------------------------------------------

Plurals supports various LLMs by using LiteLLM to make API calls. Agents also support LiteLLM's ``kwargs`` arguments
so you can (e.g) pass in a temperature or max tokens. Here are some examples of using different models:

.. code-block:: python

    from plurals.agent import Agent
    gpt4 = Agent(model='gpt-4o'
    gpt3 = Agent(model='gpt-3.5-turbo', kwargs={'temperature':1})



Inspecting the exact prompts that an Agent is doing
---------------------------------------------------

It is important to know what exactly is going on behind the scenes, so we have a few ways to do this!

By calling ``agent.info``, we can retrieve a dictionary containing comprehensive information about the Agent, including their prompts, full system instructions, and a key called ``history``, which consists of the prompts and responses of agents. You can get this ``history`` key by calling ``agent.history`` if that is your main interest. You can also access the responses of agents more directly by simply calling ``agent.responses``.


.. code-block:: python

   from plurals.agent import Agent
   task = "Should the United States ban assault rifles? Answer in 50 words."
   a = Agent(ideology="very conservative", model='gpt-4o')
   a.process(task)
   print("\nINFO\n")
   print(a.info)
   print("\nHISTORY\n")
   print(a.history)
   print("\nRESPONSES\n")
   print(a.responses)


.. code-block:: python

   from plurals.agent import Agent
   task = "Should the United States ban assault rifles? Answer in 50 words."
   liberal_agent = Agent(ideology="very liberal", persona_template='second_wave', model='gpt-4o', task=task)
   lib_answer1 = liberal_agent.process()
   lib_answer2 = liberal_agent.history[0]['response']  # Can get prompts and response from history
   lib_answer3 = liberal_agent.info['history'][0]['response']  # Can get history and more from info

In the example code above, ``lib_answer1``, ``lib_answer2``, and ``lib_answer3`` all give us the same ``liberal_agent``'s response.


Structures
==========

Overview
--------

Plurals supports various structures for agent interactions. Here are examples of each. For more information,
see the documentation on each structure in the ``deliberation`` module [1].
[1] https://josh-ashkinaze.github.io/plurals/deliberation.html

Each Structure offers different ways for Agents to interact with each other:
- Ensemble: Agents process tasks in parallel without information sharing
- Chain: Agents process tasks sequentially, each building on the previous Agent's output
- Debate: Two Agents engage in a back-and-forth discussion
- Graph: Agents interact in a directed acyclic graph (DAG) structure

Every Structure can be moderated, which means that a Moderator Agent will oversee the task and potentially combine the responses of the Agents.
Structures will return ``responses`` as a list or you can access the final response by calling the ``final_response`` attribute.


Combination Instructions
------------------------


**Combination instructions** describe how agents are instructed to combine information in the structure. It is a special kind of instruction that only kicks in when there are previous responses from an agent's view. These instructions allow you to customize how Agents deliberate. There are two ways to set ``combination_instructions``:

Using a template
~~~~~~~~~~~~~~~~

We offer a list of templates which can be used via keywords. Options include things like

- ``first_wave``: First-wave deliberative democracy ideals
- ``second_wave``: Second-wave deliberative democracy ideals
- ``critique_revise``: A critique and revise template based on constiutional AI
- ``voting``: A template meant for making final decisions
- ``jury``: A template based on instructions given to New York state jurors


These templates can be found in `instructions.yaml <https://github.com/josh-ashkinaze/plurals/blob/main/plurals/instructions.yaml>`_.


Setting your own
~~~~~~~~~~~~~~~~

You can also pass in your own ``combination_instructions``. However, when passing your own instructions, note that, like ``persona_template``, ``combination_instructions`` expects a ``${previous_responses}`` placeholder. This will get filled in with the previous responses.

Ensemble
--------

Ensembles are the most basic Structure where Agents just process tasks in parallel. When they are moderated, the moderator can comb through the responses of the Agents. The only parameter of an Ensemble is ``cycles``, which is how many times to repeat.

For example, let’s say we wanted to have a panel of 10 nationally representative agents brainstorm ideas to improve America. We can define our agents, put them in an ensemble, and then simply do ``ensemble.process()``.  Here, we have a Moderator so the ``final_response`` will be a synthesis.

.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Ensemble, Moderator

    task = "Brainstorm ideas to improve America."
    agents = [Agent(persona='random', model='gpt-4o') for i in range(10)]
    moderator = Moderator(persona='divergent', model='gpt-4o') # template for divergent creativity
    ensemble = Ensemble(agents, moderator=moderator, task=task)
    ensemble.process()
    print(ensemble.final_response)


.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Ensemble, Moderator
    task = "Brainstorm ideas to improve America."
    Custom moderator combination instructions
    combination_instructions = """INSTRUCTIONS
    Return a master response that takes the best part of previous responses.
    PREVIOUS RESPONSES: ${previous_responses}
    RETURN a json like {'response': 'the best response', 'rationale':Rationale for integrating responses} and nothing else"""
    agents = [Agent(persona='random', model='gpt-4o') for i in range(10)]  # random ANES agents
    moderator = Moderator(persona='default', model='gpt-4o')  # default moderator persona
    ensemble = Ensemble(agents, moderator=moderator, task=task, combination_instructions=combination_instructions)
    ensemble.process()
    print(ensemble.final_response)


**Note:** In the above example we set our own ``combination_instructions`` for the Moderator. Recall that when users set their own ``combination_instructions``, ``combination_instructions`` expects a ``${previous_responses}`` placeholder.


Ensemble also allows you to combine models without any personas (as do all Structures), so we
can test if different models ensembled together give different results relative to the same model ensembled together. Remember that this is simply a standard API call when we do not pass in ``system_instructions`` or a ``persona``.

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


Chain
------

Chains can be thought of as a simple uni-directional graph, where it is just a sequence of Agents who process tasks in order.
The available parameters are ``last_n`` (which controls how many prior responses an Agent sees), ``cycles``
(how many times to repeat), and ``shuffle`` (whether to shuffle the order of the Agents on each cycles).


.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Chain, Moderator

    task = "How should we combat climate change? Answer in 100 words."
    agent1 = Agent(persona='a sociologist', model='gpt-4o')
    agent2 = Agent(persona='an economist', model='gpt-4o')
    agent3 = Agent(persona='a psychologist', model='gpt-4o')
    moderator = Moderator(persona='default',
        model='gpt-4o',
        combination_instructions="default"
     )

    chain = Chain([agent1, agent2, agent3],
        combination_instructions="critique_revise",  # critique and revise template
        moderator=moderator, task=task
    )
    chain.process()
    print(chain.final_response)


Here is a Chain with multiple ``cycles`` and the ``last_n==1``, meaning each Agent will only see the last response of other Agents.

.. code-block:: python

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
------

In a Debate, two Agents engage in a back-and-forth discussion. Note that for this Structure only it is highly advised to
use a template for combination instructions (specifically, the ``debate`` template).  Here we also give an example of
passing differing tasks to Agents.

.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Debate, Moderator

    agent1 = Agent(persona="liberal",
        persona_template="default", model='gpt-4o',
        task = "Convince an Agent that the government should provide free healthcare."
    )
      agent2 = Agent(persona="conservative",
        persona_template="second_wave", model='gpt-4o',
        task = "Convince an Agent that the government should NOT provide free healthcare."
    )
    debate = Debate([agent1, agent2], task=task, combination_instructions="debate", moderator=moderator)
    debate.process()
    print(debate.final_response)



Graph
------

There are two ways to set up a Graph. The first is to pass in a dictionary of Agents and a list of edges.
The second is to pass in a list of Agents and a list of edges. The first way is more transparent, so we recommend it.

Each edge (A, B) is a directed edge from Agent A to Agent B, meaning Agent B will see the response of Agent A.
Graphs allow you to `upweight` the different Agents by varying their connecetedness.

**Note**: Here, each Agent has different combination instructions.


.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Graph

    task = "What are your thoughts on the role of government in society? Answer in 20 words."

    agents = {
        'liberal': Agent(system_instructions="you are a liberal",
            model="gpt-3.5-turbo",
            combination_instructions="Build on previous responses: <start>${previous_responses}</end>"),
         ),
        'conservative': Agent(system_instructions="you are a conservative",
            model="gpt-3.5-turbo",
            combination_instructions="Argue against previous responses: <start>${previous_responses}</end>")
         ),
        'libertarian': Agent(system_instructions="you are a libertarian",
            model="gpt-3.5-turbo",
            combination_instructions="Synthesize previous responses: <start>${previous_responses}</end>")
        )
    }
    edges = [
        ('liberal', 'conservative'),
        ('liberal', 'libertarian'),
        ('conservative', 'libertarian')
    ]
    graph = Graph(agents=agents, edges=edges, task=task)
    graph.process()



Tracing what is going on in Structures
--------------------------------------

To get a better sense of what is going on, we can access information of
both the ensemble and the agents.

.. code-block:: python

   for agent in ensemble.agents:
       print("\nAGENT INFO\n")
       print(agent.info) # Will get info about the agent
       print("\nAGENT HISTORY\n")
       print(agent.history) # Will get the history of the agent's prompts so you can see their API calls

   # `ensemble.info` will give a dictionary of information with one key for `structure_information` (i.e: information
   # related to the Structure and one key called `agent_information` (i.e: `agent.info` for each of the agents in the
   # Structure)
   ensemble.info
   # ensemble.info['agent_information'] # Will give the info of all the agents in the ensemble
   # ensemble.info['structure_information'] # Will give the info of Structure

Moderators
=============


Moderators are a subclass of Agents who summarize multi-agent deliberation. Any Structure supports an optional Moderator. Moderators are defined by:

- **Profile:** Like Agents, Moderators have a distinct "profile" which we operationalize as system instructions. System instructions can be set directly or via persona methods. We have a special class of Moderators called "Auto-Moderators" who generate their own system instructions based on a task.

- **Combination Instructions:** Here, combination instructions define how Moderators aggregate the responses that they see. As with Agents, these can be set directly or via templates. These templates can be found in `instructions.yaml <https://github.com/josh-ashkinaze/plurals/blob/main/plurals/instructions.yaml>`_.

- **Task:** Moderators can have a distinct task from Agents, or inherit the task from the Structure they are moderating.

- **Model:** Moderators are initialized to be a particular LLM.

Setting a Moderator’s System Instructions
-----------------------------------------

Via personas
~~~~~~~~~~~~

Like Agents, ``personas`` and ``system_instructions`` are different ways
to set up the moderator’s system instructions. If you use ``persona``,
then you can use some of our default moderator personas available in the
defaults file. For example, if we pass in ``persona='voting'``, then we will use a
moderator persona meant for voting.

.. code-block:: python

   from plurals.deliberation import Moderator

   a = Moderator(persona='voting', model='gpt-4o', combination_instructions="voting")

There is also an option to define your own persona. However, when
passing your own instructions in, note that, like ``persona_template``,
persona expects a ``${task}`` placeholder. This will get filled in with
the actual task.

.. code-block:: python

   from plurals.deliberation import Moderator

   mod = Moderator(persona="You are a neutral moderator overseeing this task, ${task}", model='gpt-4o',
   combination_instructions="voting")

Moderator system instructions set directly
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can also set ``system_instructions`` directly, much like with
Agents, and this will have a similar effect to custom personas.

.. code-block:: python

   from plurals.deliberation import Moderator

   mod = Moderator(system_instructions="You are a neutral moderator overseeing this task, ${task}", model='gpt-4o',
   combination_instructions="voting")

The difference is that ``system_instructions`` is not linked with our
templates, so you cannot access any pre-defined moderator instructions
when using ``system_instructions``. ``system_instructions='default'``
will not access the default template like ``persona='default'`` would.

Auto-Moderators
~~~~~~~~~~~~~~~

We have a special option where, if the ``system_instructions`` of a
moderator are set to ``auto``, then the moderator will, given a task,
come up with its own system instructions. Here is how to do this!

.. code-block:: python

   from plurals.deliberation import Moderator, Ensemble, Chain
   from plurals.agent import Agent

   task = ("Your goal is to come up with the most creative ideas possible for pants. We are maximizing creativity. Answer"
           " in 20 words.")
   a = Agent(model='gpt-4o')
   b = Agent(model='gpt-3.5-turbo')
   # By putting the moderator in the Ensemble we are going to
   # trigger the auto-mod generator
   chain = Chain([a, b], moderator=Moderator(system_instructions='auto', model='gpt-4o'), task=task)

So let’s see what the moderator thinks it should be doing with this
information.

.. code-block:: python

   print(chain.moderator.system_instructions)

.. code-block:: markdown

   Review all submitted responses, identify the most unique and imaginative ideas
   for pants, and compile a ranked list from most to least creative. Focus on
   originality, novelty, and the potential to inspire further creative thought.
   Exclude repetitive or overly conventional ideas.

Here are ways to use auto-moderation.

.. code-block:: python

   from plurals.deliberation import Moderator, Ensemble, Chain
   from plurals.agent import Agent
   task = "Come up with creative ideas"

   a = Agent(model='gpt-4o')
   b = Agent(model='gpt-3.5-turbo')

   # This will trigger the auto-mod module to generate its own system instructions.
   # This is a straightforward way to use auto-moderators. Then we can just put it in a Structure
   mod = Moderator(system_instructions='auto', model='gpt-4o', task=task)
   chain = Chain([a, b], moderator=mod, task=task)

   # Simply defining the moderator in the Structure will inherit the structure's task so this is also a simple way to have
   # the Moderator bootstrap its own instructions based on the task.
   a = Agent(model='gpt-4o')
   b = Agent(model='gpt-3.5-turbo')
   chain = Chain([a, b], moderator=Moderator(system_instructions='auto', model='gpt-4o'), task=task)


   # You can also turn a normal moderator into an auto-moderator.
   mod = Moderator(system_instructions="some boring initial instructions",  model='gpt-4o')
   mod.generate_and_set_system_instructions(task=task)

   # Or, you can generate instructions and inspect them before setting them. You can generate multiple times of course.
   mod = Moderator(system_instructions="some boring initial instructions",  model='gpt-4o')
   print(mod.generate_system_instructions(task=task))

.. code-block:: python

   # Review all submitted responses for uniqueness, relevance, and creativity. Prioritize ideas that are feasible and
   # innovative. Eliminate duplicates and rank responses by feasibility and impact. Summarize the top 5-10 ideas,
   # ensuring a diverse range of concepts is represented.
   mod.system_instructions = "Review all submitted responses for uniqueness, relevance, and creativity. Prioritize ideas that are feasible and innovative. Eliminate duplicates and rank responses by feasibility and impact. Summarize the top 5-10 ideas, ensuring a diverse range of concepts is represented."


