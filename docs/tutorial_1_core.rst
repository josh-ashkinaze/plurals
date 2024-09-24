:orphan:

.. _tutorial:



Core Concepts
=============

Plurals allows users to create simulated social ensembles with Agents, Structures, and Moderators. **Agents** complete tasks within **Structures**,
which define how information is shared between Agents. **Moderators** can summarize multi-agent communication.


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
Structures govern how information is shared between Agents completing a task. Key features of Structures include:

* **Amount of information shared**:
  Chains, Debates, and Graphs have a parameter called ``last_n`` that controls how many prior responses each Agent can see. For DAGs, the network density can also be considered a measure of information sharing. Ensembles are a basic structure where no information is shared; Agents process tasks in isolation.

* **Directionality of information shared**:
  A "Chain" of Agents is a linear chain of the form ``Agent1->Agent2->...`` where the direction of sharing only goes one way. A debate involves two agents (``Agent1<->Agent2``) sharing information for a given number of ``cycles``. In DAGs, Agents may have both predecessors and successors.

* **Randomness**:
  Chains support a ``shuffle`` parameter that, if set to ``True``, will rewire the order of Agents on each cycle. This introduces a degree of randomness in information-sharing.

* **Repetition**:
  Chains, Debates, and Ensembles support a ``cycle`` parameter which will repeat the process.


Structures we currently support:

- Ensemble: Agents process tasks in parallel without information sharing
- Chain: Agents process tasks sequentially, each building on the previous Agent's output
- Debate: Two Agents engage in a back-and-forth discussion
- Graph: Agents interact in a directed acyclic graph (DAG) structure


.. note::

   If you believe there is another structure that would be widely useful, please open an issue on GitHub using
   the ``feature request`` issue template! We may not be able to implement every structure, but if there is wide demand
   we will try.

Moderators
----------
Moderators are special Agents that summarize or synthesize the outputs of other Agents in a Structure. They can be used to:

- Aggregate information from multiple Agents
- Generate final outputs or decisions based on multi-agent deliberations
- Implement custom moderation logic

Plurals also supports `Auto-Moderators` that can generate their own moderation instructions based on the given task.


Templates
---------
Users can optionally use various templates found in `instructions.yaml <https://github.com/josh-ashkinaze/plurals/blob/main/plurals/instructions.yaml>`_,
and our paper tests a subset of instructions.
