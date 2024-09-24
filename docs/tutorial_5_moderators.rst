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
----------------------------------------------

Combination instructions are set the same way as regular Agents, where you can use a template or input your own
combination instructions that have a ``${previous_responses}`` placeholder.


.. code-block:: python

   from plurals.deliberation import Moderator

   mod = Moderator(system_instructions="You are a neutral moderator overseeing this task, ${task}", model='gpt-4o',
   combination_instructions="Select the response from previous responses that is the least polarizing: <start>${previous_responses}</end>"))