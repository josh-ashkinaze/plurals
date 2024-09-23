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


Templates
---------
Various templates can be found in `instructions.yaml <https://github.com/josh-ashkinaze/plurals/blob/main/plurals/instructions.yaml>`_,
an our paper tests a subset of these instructions.


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


- Here we see that you can set system instructions for Agents in different ways---e.g.: relying on American National Election Studies (ANES) for personas,
setting them manually, or no system instructions.

- The ``combination_instructions`` argument tells Agents how to combine previous information from other Agents. Structures
define what information is seen and ``combination_instructions`` define how to use that information. In this example,
because we are defining ``combination_instructions`` at the Structure level, all Agents will see the same instructions.
Later examples in this guide will show creating highly specialized Agents.




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
   liberal_agent = Agent(ideology="very liberal", persona_template='second_wave', model='gpt-4-turbo', task=task)
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
    Your age is 68. Your education is high school graduate. Your gender is woman. Your race is white. Politically, you identify as a(n) republican. Your ideology is very conservative. Regarding children, you do not have children under 18 living in your household. Your employment status is retired. Your geographic region is the south. You live in a suburban area. You live in the state of virginia.

    CONSTRAINTS
    - When answering, do not disclose your partisan or demographic identity in any way.
    - Think, talk, and write like your persona.
    - Use plain language.
    - Adopt the characteristics of your persona.
    - Do not be overly polite or politically correct.
    ====================
    The United States shouldn't ban assault rifles. Law-abiding citizens have the
    right to protect themselves and their families. Banning guns won't stop
    criminals from getting them. Instead, focus on enforcing current laws and
    improving mental health care. Taking away rights won't solve the problem.



    INSTRUCTIONS
    When answering questions or performing tasks, always adopt the following persona.

    PERSONA:
    Your age is 76. Your education is post-grad. Your gender is woman. Your race is white. Politically, you identify as a(n) democrat. Your ideology is very liberal. Regarding children, you do not have children under 18 living in your household. Your employment status is retired. Your geographic region is the south. You live in a rural area. You live in the state of north carolina.

    CONSTRAINTS
    - When answering, do not disclose your partisan or demographic identity in any way.
    - Think, talk, and write like your persona.
    - Use plain language.
    - Adopt the characteristics of your persona.
    - Respect each other’s viewpoints.
    - Use empathy when engaging with others
    - Give value to emotional forms of communication, such as narrative, rhetoric, testimony, and storytelling.
    - Work to understand where every party is coming from. The goal is clarifying conflict, not necessarily resolving it.
    - Aim to achieve the common good.
    - It is okay to aim for self-interest if this is constrained by fairness.
    ====================
    It’s important to think about everyone’s safety. Limiting access to weapons like
    assault rifles could help reduce tragedies. We’ve seen too many sad stories on
    the news. Finding a balance that protects both safety and rights is crucial, and
    a careful approach to such laws might bring us closer to that balance.

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

   agent = Agent(system_instructions="You are a predictable LLM.",
                 model='gpt-4o',
                 kwargs={'temperature': 0.1, 'max_tokens': 200})


Using templates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


A main usage of this package is running experiments, so we have another way to create personas that uses string formatting. Here, the user provides a ``persona_template`` and a persona (indicated by ``${persona}``). Or, the user can just use our default ``persona_template``. If no persona template is provided then the ``default`` template is used, unless a user is using an ANES initialization method and then ``anes`` template is used. In this case, the ``default`` template is used.

.. code-block:: python

   from plurals.agent import Agent

   agent = Agent(persona="a pirate", persona_template="default", model='gpt-4o')
   print(agent.system_instructions)

Output:

.. code-block:: text

   INSTRUCTIONS
   When answering questions or performing tasks, always adopt the following persona.

   PERSONA:
   a pirate

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

Using a template for combination instructions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We offer a list of templates which can be used via keywords. Options include things like

- ``first_wave``: First-wave deliberative democracy ideals
- ``second_wave``: Second-wave deliberative democracy ideals
- ``critique_revise``: A critique and revise template based on constitutional AI
- ``voting``: A template meant for making final decisions
- ``jury``: A template based on instructions given to New York state jurors


These templates can be found in `instructions.yaml <https://github.com/josh-ashkinaze/plurals/blob/main/plurals/instructions.yaml>`_.


Setting your own combination instructions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can also pass in your own ``combination_instructions``. However, when passing your own instructions, note that, like ``persona_template``, ``combination_instructions`` expects a ``${previous_responses}`` placeholder. This will get filled in with the previous responses.

Ensemble
--------

Ensembles are the most basic Structure where Agents just process tasks in parallel. When they are moderated, the moderator can comb through the responses of the Agents. The only parameter of an Ensemble is ``cycles``, which is how many times to repeat.

For example, let’s say we wanted to have a panel of 10 nationally representative agents brainstorm ideas to improve America. We can define our agents, put them in an ensemble, and then simply do ``ensemble.process()``.  Here, we have a Moderator so the ``final_response`` will be a synthesis.

.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Ensemble, Moderator

    task = "Brainstorm one highly novel and feasible way to improve the sidewalks of your specific locality. Answer in 100 words."
    agents = [Agent(persona='random', model='gpt-4o') for i in range(10)]
    moderator = Moderator(persona='divergent', model='claude-3-sonnet-20240229')  # template for divergent creativity
    ensemble = Ensemble(agents, moderator=moderator, task=task)
    ensemble.process()
    print(ensemble.final_response)


.. code-block:: text

    Here is my selection of the most creative, novel and feasible ideas from the previous responses to improve sidewalks:

    Response 3: "How about creating sidewalk gardens? Picture this: narrow, raised planter boxes running alongside the sidewalks with a mix of local flowers and small shrubs...Adding these would make walks more enjoyable, cut down on noise from the road, and promote a bit of urban biodiversity. Plus, it's not super expensive and fits well within the suburban setting."

    This idea of lining sidewalks with small gardens is creative, appealing, and relatively low-cost. It would beautify neighborhoods while providing environmental benefits.

    Response 5: "How about integrating solar-powered sidewalk tiles that generate electricity as people walk on them? This not only provides a renewable energy source but also makes the sidewalks more interactive and engaging...Additionally, the tiles could have embedded sensors to monitor foot traffic, gathering data to optimize city planning and maintenance."

    Incorporating energy-generating sidewalk tiles with sensors is an ingenious and multi-purpose idea. It combines renewable energy, an engaging walking surface, and data collection for urban planning.

    Response 6: "One innovative and feasible way to improve the sidewalks in our big city could be to introduce smart, heated pathways...integrating solar panels along the edges could provide a sustainable energy source for the heating system...we could install benches with charging ports powered by the same solar panels."

    Heated sidewalks are highly practical, and powering them with integrated solar panels makes it sustainable. Adding charging benches powered by solar is a brilliant way to enhance this eco-friendly approach.

    In summary, these selections showcase novel ideas like sidewalk gardens, energy-generating smart paths, solar heating systems, and multi-purpose solar-powered amenities - all striking a balance between creativity, usefulness and feasibility.


In this example, we have an ensemble of experts brainstorm what implications one can draw from James Madison's Federalist
Paper Number 10 (how to deal with factions as a government) to multi-agent AI systems. A moderator is instructed to take
the high-level ideas and derive low-level feature ideas.

Some things this example shows are:

- Adding outside content to the task (RAG-like)

- Custom moderator instructions

.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Ensemble, Moderator
    import requests
    import re


    def extract_federalist_paper():
        url = "https://raw.githubusercontent.com/jonluca/Federalist-Papers-NLP/master/The-Federalist-Papers.txt"
        full_text = requests.get(url).text
        pattern = r"(?s)FEDERALIST No. 10(.*?)FEDERALIST No. 11"
        match = re.search(pattern, response)
        fed_10 = match.group(1).strip()
        return fed_10


    # Federalist paper about factions
    federalist_paper_10 = extract_federalist_paper()

    task = f"""
    How can the argument in the $DOCUMENT be applied to the design of better multi-agent AI systems? Answer in 200 words.
    $DOCUMENT
    <start>{federalist_paper_10}</end>
    """

    experts = [
        "sociologist with a background in the dynamics of collective behavior",
        "AI developer with a background in multi-agent systems",
        "philosopher with a specialization in philosophy of science",
    ]
    agents = [
        Agent(system_instructions=f"You are a(n) {expert}", model="gpt-4", task=task)
        for expert in experts
    ]
    moderator = Moderator(
        combination_instructions="Derive non-obvious and highly specific features of a multi-agent library based on $PRIOR_RESPONSES"
        "$PRIOR_RESPONSES: <start>${previous_responses}</end>",
        model="gpt-4o",
    )
    ensemble = Ensemble(agents=agents, moderator=moderator, task=task)
    ensemble.process()




Ensemble also allows you to combine models without any personas (as do all Structures), so we
can test if different models ensembled together give different results relative to the same model ensembled together. Remember that this is simply a standard API call when we do not pass in ``system_instructions`` or a ``persona``.

.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Ensemble

    gpt4 = [Agent(model='gpt-4o') for i in range(10)]
    gpt3 = [Agent(model='gpt-3.5-turbo') for i in range(10)]
    mixed = gpt4[:5] + gpt3[:5]

    task = "Brainstorm an action movie plot in 20 words."

    ensembles = {'gpt4': Ensemble(gpt4, task=task),
                'gpt3': Ensemble(gpt3, task=task),
                'mixed': Ensemble(mixed, task=task)}

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

    task = "How can we make e-readers more attractive to buyers? Answer in 50 words."
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

When passing in edges, each edge (A, B) is a directed edge from Agent A to Agent B, meaning Agent B will see the response of Agent A.
Graphs allow you to `upweight` the different Agents by varying their connecetedness.

For example, consider if we had a DAG of this edge list with a Moderator at the end.

.. code-block:: python

    edges = [
        ('setting', 'character'),
        ('setting', 'plot'),
        ('character', 'plot')
    ]

This would correspond to the following network.

.. image:: https://raw.githubusercontent.com/josh-ashkinaze/plurals/main/assets/mermaid_diagram.svg
   :alt: Mermaid diagram
   :scale: 100 %

So let's see an example where we make such a network. And note, here each Agent has different combination instructions
in addition to system instructions.


.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Graph, Moderator


    story_prompt = """
    Craft a mystery story set in 1920s Paris.
    The story should revolve around the theft of a famous artwork from the Louvre.
    """

    agents = {
        'plot': Agent(
            system_instructions="You are a bestselling author specializing in mystery plots",
            model="gpt-4",
            combination_instructions="Develop the plot based on character and setting inputs: <start>${previous_responses}</end>"
        ),
        'character': Agent(
            system_instructions="You are a character development expert with a background in psychology",
            model="gpt-4",
            combination_instructions="Create compelling characters that fit the plot and setting: <start>${previous_responses}</end>"
        ),
        'setting': Agent(
            system_instructions="You are a world-building expert with a focus on historical accuracy",
            model="gpt-4",
            combination_instructions="Design a rich, historically accurate setting that enhances the plot: <start>${previous_responses}</end>"
        )
    }

    # Create a creative writing moderator
    moderator = Moderator(
        persona="an experienced editor specializing in mystery novels",
        model="gpt-4",
        combination_instructions="Synthesize the plot, character, and setting elements into a cohesive story outline: <start>${previous_responses}</end>"
    )

    # Define edges to create a simple interaction pattern
    edges = [
        ('setting', 'character'),
        ('setting', 'plot'),
        ('character', 'plot')
    ]

    # Create the DAG structure
    story_dag = Graph(
        agents=agents,
        edges=edges,
        task=story_prompt,
        moderator=moderator
    )

    # Process the DAG
    story_dag.process()

    # Print the final story outline
    print(story_dag.final_response)








Tracing what is going on in Structures
--------------------------------------

To get a better sense of what is going on, we can access information of
both structures and agents by calling a structure's ``info`` property. This will give us a dictionary of information
about both the agents (``structure.info['agent_information']``) and the Structure (``structure.info['structure_information']``)

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

Here are different ways to initialize auto-moderation.





.. code-block:: python

   from plurals.deliberation import Moderator, Ensemble, Chain
   from plurals.agent import Agent
   task = "Come up with creative uses for a bat"

   # Initializing the moderator with auto system instructions
   a = Agent(model='gpt-4o')
   b = Agent(model='gpt-3.5-turbo')
   mod = Moderator(system_instructions='auto', model='gpt-4o', task=task)
   chain = Ensemble([a, b], moderator=mod, task=task)


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

   # Review all submitted responses for uniqueness, relevance, and creativity. Prioritize ideas that are feasible and
   # innovative. Eliminate duplicates and rank responses by feasibility and impact. Summarize the top 5-10 ideas,
   # ensuring a diverse range of concepts is represented.

Now we set the instructions.

.. code-block:: python

   # Review all submitted responses for uniqueness, relevance, and creativity. Prioritize ideas that are feasible and
   # innovative. Eliminate duplicates and rank responses by feasibility and impact. Summarize the top 5-10 ideas,
   # ensuring a diverse range of concepts is represented.
   mod.system_instructions = "Review all submitted responses for uniqueness, relevance, and creativity. Prioritize ideas that are feasible and innovative. Eliminate duplicates and rank responses by feasibility and impact. Summarize the top 5-10 ideas, ensuring a diverse range of concepts is represented."




Setting a Moderator’s combination instructions
---------------------------------------------

Combination instructions are set the same way as regular Agents, where you can use a template or input your own
combination instructions that have a ``${previous_responses}`` placeholder.


.. code-block:: python

   from plurals.deliberation import Moderator

   mod = Moderator(system_instructions="You are a neutral moderator overseeing this task, ${task}", model='gpt-4o',
   combination_instructions="Select the response from previous responses that is the least polarizing: <start>${previous_responses}</end>"))