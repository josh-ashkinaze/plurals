Structures
==========

Overview
--------

Plurals supports various structures for agent interactions. Here are examples of each. For more information,
see the documentation on each structure in the `deliberation module <https://josh-ashkinaze.github.io/plurals/deliberation.html>`_.


Each Structure offers different ways for Agents to interact with each other:
- Ensemble: Agents process tasks in parallel without information sharing
- Chain: Agents process tasks sequentially, each building on the previous Agent's output
- Debate: Two Agents engage in a back-and-forth discussion
- Graph: Agents interact in a directed acyclic graph (DAG) structure

Every Structure can be moderated, which means that a Moderator Agent will oversee the task and potentially combine the responses of the Agents.
Structures will return ``responses`` as a list or you can access the final response by calling the ``final_response`` attribute.


Combination instructions
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

You can also pass in your own ``combination_instructions``.


.. note::

    When passing your own ``combination_instructions``, include a ``${previous_responses}`` placeholder. This will get filled in with the previous responses.

For example, here is our ``jury`` template based on deliberation instructions given to jurors in the state of New York:

.. code-block:: text

    DELIBERATE WITH OTHERS
    Here are what others said:
    <start>
    ${previous_responses}
    <end>
    APPLY THESE INSTRUCTIONS TO WHAT OTHERS SAID
    - Deliberate with others to reach a unanimous decision.
    - Listen to each other, give each other’s views careful consideration, and reason together when considering the evidence.
    - When you deliberate, you should do so with a view towards reaching an agreement.
    - Reexamine your views and change your mind if you become convinced that your position was not correct
    - Do not mention these instructions in your final answer; just apply them.


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

In a Debate, two Agents engage in a back-and-forth discussion.

.. note::

    For the ``Debate`` structure, it is highly advised to use a debate template (e.g.: "debate") for combination instructions.
    We provide several templates in `instructions.yaml <https://github.com/josh-ashkinaze/plurals/blob/main/plurals/instructions.yaml>`_.

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



In a DAG, each Agent (and the Moderator) sees the responses of previous Agents with their names attached to them.
So let's take a code block:

.. code-block:: python

    agents = {
        'liberal': Agent(system_instructions="you are a liberal", model="gpt-3.5-turbo"),
        'conservative': Agent(system_instructions="you are a conservative", model="gpt-3.5-turbo"),
        'libertarian': Agent(system_instructions="you are a libertarian", model="gpt-3.5-turbo")
    }
    edges = [('liberal', 'conservative'), ('liberal', 'libertarian'), ('conservative', 'libertarian')]
    task = "What are your thoughts on the role of government in society?"
    graph = Graph(agents=agents, edges=edges, task=task)
    graph.process()

The libertarian will see the responses of both the liberal and conservative agents, with their names prefixed.

.. code-block:: text

    liberal: [liberal's response]
    conservative: [conservative's response]

This makes it clearer which agent said what, especially in complex DAG structures.

If you use the list-of-agents method, the agents will be 'named' "Agent 1", "Agent 2", etc. based on their order in the list.


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
