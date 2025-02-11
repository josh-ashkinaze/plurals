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

.. note::

    You can also create your own ``persona_template``. Just make sure to add a ``${persona}`` placeholder in the template.

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

ANES Option 3: Searching ANES using a Pandas query string
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


Using different LLMs
---------------------------------------------------

Plurals supports various LLMs by using LiteLLM to make API calls. Agents also support LiteLLM's ``kwargs`` arguments
so you can (e.g) pass in a temperature or max tokens. Here are some examples of using different models:

.. code-block:: python

    from plurals.agent import Agent
    gpt4 = Agent(model='gpt-4o'
    gpt3 = Agent(model='gpt-3.5-turbo', kwargs={'temperature':1})



Local LLMs [Experimental]
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
You can use local LLMs via `Ollama <https://ollama.ai>`_. Please note: Support for local LLMs via Ollama is currently experimental and not officially supported. If you use Ollama with Plurals and find any bugs, please
post a GitHub issue.

1. Install Ollama and start the server:

   .. code-block:: bash

      ollama start

2. Pull your desired model:

   .. code-block:: bash

      ollama pull gemma:2b

3. Configure your Agent with the Ollama endpoint:

.. code-block:: python

   from plurals.agent import Agent

   # point to local Ollama server
   local_agent = Agent(
       model="ollama/gemma:2b",
       kwargs={'api_base': 'http://localhost:11434'}
   )
   print(local_agent.process("Say hello"))

.. note::
   - First run the model locally with ``ollama run gemma:2b``
   - Full model list: https://ollama.ai/library
   - Again: This integration is *experimental* as of now. In contrast to other documented features, API stability is not currently guaranteed.


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