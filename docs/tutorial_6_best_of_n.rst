.. _best-of-n:

Best-of-N Response Selection
=============================

Overview
--------

Agents support generating multiple responses and selecting the best one according to a user-defined function. This enables techniques like self-consistency sampling and reward optimizing.

Two required parameters:

* ``num_responses``: Number of responses to generate (must be ≥ 1)
* ``response_selector``: Function that takes a list of strings and returns one string

All generated responses are stored in ``agent.history[-1]['all_responses']`` for inspection.

Quick Start
-----------

The examples below progress from simple to advanced:

1. **Return first response**: Learn the basic mechanics
2. **Return longest response**: Simple heuristic-based selection
3. **Wikipedia NPOV**: Verifiable rewards (edit distance, semantic similarity, mixed rewards)
4. **LLM-as-judge**: Complex behavioral criteria for single agents
5. **LLM-as-judge in debates**: Maximize adherence across multi-turn interactions

Example 1: Return First Response (Learn the Mechanics)
-------------------------------------------------------

Start by understanding the basic pattern---generate multiple responses but just return the first one.

.. code-block:: python

    from plurals.agent import Agent

    def return_first(responses):
        """Always return the first response"""
        return responses[0]

    agent = Agent(
        task="Explain photosynthesis in simple terms",
        model="gpt-4o",
        num_responses=5,
        response_selector=return_first
    )

    response = agent.process()
    print(response)

**Inspect what was generated:**

.. code-block:: python

    all_responses = agent.history[-1]['all_responses']

    print(f"\nGenerated {len(all_responses)} responses:")
    for i, r in enumerate(all_responses):
        selected = "← SELECTED" if r == response else ""
        print(f"{i+1}. {r[:80]}... {selected}")

**Output:**

.. code-block:: text

    Generated 5 responses:
    1. Photosynthesis is the process by which green plants, algae, and some bacteria co... ← SELECTED
    2. Photosynthesis is the process by which green plants, algae, and some bacteria co...
    3. Photosynthesis is a process that plants, algae, and some bacteria use to make th...
    4. Photosynthesis is the process by which green plants, algae, and some bacteria ma...
    5. Photosynthesis is the process by which green plants, algae, and some bacteria co...

So, the agent generated 5 different responses, but ``return_first`` selected the first one. Now you can write more sophisticated selectors.

Example 2: Return Longest Response
-----------------------------------

Pick the most detailed response using a simple heuristic.

.. code-block:: python

    from plurals.agent import Agent

    def pick_longest(responses):
        """Return the response with the most characters"""
        return max(responses, key=len)

    agent = Agent(
        task="Explain photosynthesis",
        model="gpt-4o",
        num_responses=5,
        response_selector=pick_longest
    )

    response = agent.process()

**Inspect with lengths:**

.. code-block:: python

    all_responses = agent.history[-1]['all_responses']

    for i, r in enumerate(all_responses):
        selected = "← SELECTED" if r == response else ""
        print(f"{i+1}. ({len(r):3d} chars) {r[:80]}... {selected}")

**Output:**

.. code-block:: text

    1. (131 chars) Photosynthesis converts light energy into chemical energy, using sunlight, carbo...
    2. (136 chars) Photosynthesis converts sunlight into chemical energy, using carbon dioxide and ... ← SELECTED
    3. (133 chars) Photosynthesis converts sunlight, carbon dioxide, and water into glucose and oxy...
    4. (133 chars) Photosynthesis converts sunlight, water, and carbon dioxide into glucose and oxy...
    5. (127 chars) Photosynthesis is the process where plants convert sunlight, carbon dioxide, and...

**Also useful**: Pick the *shortest* response for concise answers:

.. code-block:: python

    agent = Agent(
        task="Say hello creatively",
        model="gpt-4o",
        num_responses=5,
        response_selector=lambda responses: min(responses, key=len)
    )

Example 3: [A real-world problem] Wikipedia NPOV with verifiable metrics
--------------------------------------------------

**Problem**:
When asked to neutralize biased text (e.g., for Wikipedia's Neutral Point of View policy), LLMs often deviate from the way expert editors make changes [1]. We found that LLMs rewrite entire sentences when human editors would make minimal edits like removing one or two charged words.


**Solution**:
Generate multiple neutralizations and select based on verifiable metrics: edit distance, semantic similarity, or a mixture of both.

[1] Ashkinaze, J., Guan, R., Kurek, L., Adar, E., Budak, C., & Gilbert, E. (2024). Seeing like an ai: How llms apply (and misapply) wikipedia neutrality norms. arXiv preprint arXiv:2407.04183.


Installation
~~~~~~~~~~~~

.. code-block:: bash

    pip install editdistance sentence-transformers

Strategy A: Minimize Edit Distance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**When to use**: Preserving the original wording and structure is critical (e.g., Wikipedia edits, legal documents).

.. code-block:: python

    from plurals.agent import Agent
    import editdistance

    original_text = "He was a very, very good photographer. He also had to go to school, where he flourished achieving praise from his teachers."

    def small_edit_dist(responses, original):
        """Return response with minimal edit distance to original"""
        distances = [editdistance.eval(r, original) for r in responses]
        min_distance_idx = distances.index(min(distances))
        return responses[min_distance_idx]

    neutralizer = Agent(
        task=f"Neutralize this statement: {original_text}",
        model="gpt-4o-mini",
        num_responses=5,
        response_selector=lambda r: small_edit_dist(r, original_text)
    )

    response = neutralizer.process()
    print(f"Original:    {original_text}")
    print(f"Neutralized: {response}")
    print(f"Edit distance: {editdistance.eval(original_text, response)}")

**Output:**

.. code-block:: text

    Original:    He was a very, very good photographer. He also had to go to school, where he flourished achieving praise from his teachers.
    Neutralized: He was a competent photographer and attended school, where he received feedback from his teachers.
    Edit distance: 52

**Inspect all alternatives:**

.. code-block:: python

    all_responses = neutralizer.history[-1]['all_responses']

    print("\nAll neutralizations ranked by edit distance:")
    scored_responses = []
    for r in all_responses:
        dist = editdistance.eval(original_text, r)
        scored_responses.append((dist, r))

    scored_responses.sort(key=lambda x: x[0])

    for i, (dist, r) in enumerate(scored_responses):
        selected = "← SELECTED" if r == response else ""
        print(f"{i+1}. (dist={dist:2d}) {r} {selected}")

**Output:**

.. code-block:: text

    All neutralizations ranked by edit distance:
    1. (dist=52) He was a competent photographer and attended school, where he received feedback from his teachers. ← SELECTED
    2. (dist=53) He was a competent photographer who attended school, where he received some recognition from his teachers.
    3. (dist=58) He was a competent photographer who attended school, where he received some positive feedback from his teachers.
    4. (dist=58) He was a competent photographer who attended school, where he received some positive feedback from his teachers.
    5. (dist=72) He was a photographer who demonstrated competence in his craft. He attended school, where he received feedback from his teachers.

    So in some cases you can imagine an LLM making a bunch of edits like Example 5.

Strategy B: Maximize Semantic Similarity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

But let's say we really just want to preserve meaning and don't care as much about exact wording (e.g., paraphrasing with neutralization).
Here we can use SBERT or some kind of embedding model. The point of this example is really that you can use models optimized for
specific tasks (in this case semantic similarity) to guide best-of-n selection for different Agents.

.. code-block:: python

    from sentence_transformers import SentenceTransformer
    from scipy.spatial.distance import cosine

    # Load embedding model (do this once, reuse across agents)
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

    def max_semantic_similarity(responses, original, model):
        """Return response most semantically similar to original"""
        original_embedding = model.encode([original])[0]
        similarities = []

        for r in responses:
            r_embedding = model.encode([r])[0]
            similarity = 1 - cosine(original_embedding, r_embedding)
            similarities.append(similarity)

        max_sim_idx = similarities.index(max(similarities))
        return responses[max_sim_idx]

    neutralizer = Agent(
        task=f"Neutralize the statement: {original_text}",
        model="gpt-4o-mini",
        kwargs = {'temperature': 0.9},  # Higher temp for diversity
        num_responses=5,
        response_selector=lambda r: max_semantic_similarity(r, original_text, embedding_model)
    )

    response = neutralizer.process()

Strategy C: Mixture of Rewards
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**When to use**: Best of both worlds for Wikipedia NPOV---both minimal changes AND preserved meaning.

.. code-block:: python

    def mixed_score_selector(responses, original, model, alpha=0.5):
        """
        Select response optimizing both edit distance and semantic similarity.

        Args:
            responses: List of candidate responses
            original: Original text
            model: Sentence embedding model
            alpha: Weight for edit distance (1-alpha for semantic similarity)
                   alpha=1.0 means only edit distance
                   alpha=0.0 means only semantic similarity
                   alpha=0.5 means equal weighting
        """
        original_embedding = model.encode([original])[0]

        # Normalize edit distances to [0, 1] range
        edit_distances = [editdistance.eval(r, original) for r in responses]
        max_dist = max(edit_distances) if max(edit_distances) > 0 else 1
        normalized_dists = [d / max_dist for d in edit_distances]

        # Calculate semantic similarities (already in [0, 1])
        similarities = []
        for r in responses:
            r_embedding = model.encode([r])[0]
            similarity = 1 - cosine(original_embedding, r_embedding)
            similarities.append(similarity)

        # Combined score (lower edit distance is better, higher similarity is better)
        scores = []
        for norm_dist, sim in zip(normalized_dists, similarities):
            combined_score = (1 - alpha) * sim - alpha * norm_dist
            scores.append(combined_score)

        max_score_idx = scores.index(max(scores))
        return responses[max_score_idx]

    # Equal weighting (alpha=0.5)
    neutralizer = Agent(
        task=f"Neutralize the sentiment: {original_text}",
        model="gpt-4o-mini",
        kwargs = {'temperature': 0.9},  # Higher temp for diversity
        num_responses=5,
        response_selector=lambda r: mixed_score_selector(
            r, original_text, embedding_model, alpha=0.5
        )
    )

    response = neutralizer.process()

**Compare all metrics:**

.. code-block:: python

    all_responses = neutralizer.history[-1]['all_responses']
    original_embedding = embedding_model.encode([original_text])[0]

    edit_distances = [editdistance.eval(r, original_text) for r in all_responses]
    max_dist = max(edit_distances)

    print("\nAll neutralizations with mixed scoring (alpha=0.5):")
    print(f"{'Rank':<6}{'Edit Dist':<12}{'Similarity':<12}{'Combined':<12}Response")
    print("-" * 80)

    scored_responses = []
    for r in all_responses:
        edit_dist = editdistance.eval(r, original_text)
        norm_dist = edit_dist / max_dist

        r_embedding = embedding_model.encode([r])[0]
        similarity = 1 - cosine(original_embedding, r_embedding)

        combined = 0.5 * similarity - 0.5 * norm_dist

        scored_responses.append((combined, edit_dist, similarity, r))

    scored_responses.sort(key=lambda x: x[0], reverse=True)

    for i, (combined, dist, sim, r) in enumerate(scored_responses):
        selected = "← SELECTED" if r == response else ""
        print(f"{i+1:<6}{dist:<12}{sim:<12.3f}{combined:<12.3f}{r} {selected}")

**Output:**

.. code-block:: text

    All neutralizations with mixed scoring (alpha=0.5):
    Rank  Edit Dist   Similarity  Combined    Response
    --------------------------------------------------------------------------------
    1     50          0.896       0.105       He was a capable photographer. He attended school, where he received feedback from his teachers. ← SELECTED
    2     53          0.895       0.085       He was a competent photographer and attended school, where he received some recognition from his teachers.
    3     52          0.855       0.071       He was a photographer. He attended school, where he received feedback from his teachers.
    4     70          0.908       -0.025      He was a competent photographer. He attended school, where he performed adequately and received some recognition from his teachers.
    5     73          0.846       -0.077      He was a photographer who met the expectations of his training. He attended school, where he received feedback from his teachers.

Example 4: LLM-as-Judge for Single Agents
------------------------------------------


**Setup evaluator:**

.. code-block:: python

    from plurals.agent import Agent

    formality_evaluator = Agent(
        system_instructions="""Rate how formal and professional this text is:
        - Uses appropriate business language
        - Avoids slang and casual phrasing
        - Maintains professional tone
        - Uses complete sentences

        Return ONLY a number from 0-10.""",
        model="gpt-4o-mini"  # Use cheap model for evaluation
    )

**Create selection function:**


.. code-block:: python

    def pick_most_formal(responses):
        """Use LLM to pick most formal response"""
        scores = []
        for r in responses:
            score_str = formality_evaluator.process(task=f"Rate this text:\n\n{r}")
            try:
                score = float(score_str.strip())
            except ValueError:
                score = 0.0  # Fallback if parsing fails
            scores.append(score)

        return responses[scores.index(max(scores))]

Here it's scoring each response but we can just as easily have the LLM directly return the top one. But there is a chance,
the LLM could return an invalid response in that case and hallucinate---though one can ensure the response does
exist in the input list.

**Use with agent:**

.. code-block:: python

    agent = Agent(
        task="Explain why the project deadline was missed",
        model="gpt-4o",
        num_responses=5,
        response_selector=pick_most_formal,
        kwargs={"temperature": 0.9}  # Higher temperature for diversity
    )

    response = agent.process()
    print(response)


Example 5: LLM-as-Judge in Debates
-----------------------------------

**Use case**: Maximize adherence to instructions across multi-turn debates (good faith vs. bad faith) with Agents who
are supposed to follow different goals.

**Setup evaluators:**

.. code-block:: python

    from plurals.agent import Agent
    from plurals.deliberation import Debate

    good_faith_evaluator = Agent(
        system_instructions="""Rate how well this response demonstrates good-faith debate:
        - Directly addresses opponent's actual arguments
        - Acknowledges valid points
        - Uses honest reasoning
        - Seeks truth over winning

        Return ONLY a number from 0-10.""",
        model="gpt-4o-mini"
    )

    bad_faith_evaluator = Agent(
        system_instructions="""Rate how well this response demonstrates bad-faith debate:
        - Misrepresents opponent's arguments
        - Uses deflection and whataboutism
        - Makes ad hominem attacks
        - Focuses on winning over truth

        Return ONLY a number from 0-10.""",
        model="gpt-4o-mini"
    )

**Create selection functions:**

.. code-block:: python

    def pick_most_good_faith(responses):
        """Use LLM to pick most good-faith response"""
        scores = []
        for r in responses:
            score_str = good_faith_evaluator.process(
                task=f"Rate this debate response:\n\n{r}"
            )
            try:
                score = float(score_str.strip())
            except ValueError:
                score = 0.0
            scores.append(score)

        return responses[scores.index(max(scores))]

    def pick_most_bad_faith(responses):
        """Use LLM to pick most bad-faith response"""
        scores = []
        for r in responses:
            score_str = bad_faith_evaluator.process(
                task=f"Rate this debate response:\n\n{r}"
            )
            try:
                score = float(score_str.strip())
            except ValueError:
                score = 0.0
            scores.append(score)

        return responses[scores.index(max(scores))]

**Full debate with greedy best-of-n:**

.. code-block:: python

    good_faith_agent = Agent(
        system_instructions="""You debate in good faith. Address arguments directly,
        acknowledge valid points, seek truth over winning.""",
        model="gpt-4o",
        num_responses=5,
        response_selector=pick_most_good_faith,
        kwargs={"temperature": 0.9}
    )

    bad_faith_agent = Agent(
        system_instructions="""You debate in bad faith. Misrepresent arguments,
        use strawman tactics, deflect, focus on winning.""",
        model="gpt-4o",
        num_responses=5,
        response_selector=pick_most_bad_faith,
        kwargs={"temperature": 0.9}
    )

    debate = Debate(
        agents=[good_faith_agent, bad_faith_agent],
        task="Should social media be regulated by government? Answer in 200 words on each turn.",
        combination_instructions="debate",
        cycles=3
    )

    debate.process()

    # Print debate transcript
    for i, response in enumerate(debate.responses):
        agent_label = "Good Faith" if i % 2 == 0 else "Bad Faith"
        turn = i // 2 + 1
        print(f"\n{'='*80}")
        print(f"[{agent_label} - Turn {turn}]")
        print(f"{'='*80}")
        print(response)

Common Pitfalls
---------------

**Missing response_selector:**

.. code-block:: python

    # ERROR - Will raise exception
    agent = Agent(num_responses=5)

    # CORRECT
    agent = Agent(num_responses=5, response_selector=lambda r: r[0])

**Selector returns None:**

.. code-block:: python

    # BAD - Can return None
    def broken(responses):
        for r in responses:
            if "keyword" in r:
                return r
        # Returns None if keyword not found!

    # GOOD - Always returns something
    def safe(responses):
        for r in responses:
            if "keyword" in r:
                return r
        return responses[0]

**Not using temperature (low diversity):**

.. code-block:: python

    # GOOD - For best-of-n, I think it is a good idea to increase temperature to get some diversity.
    agent = Agent(
        num_responses=5,
        response_selector=pick_longest,
        kwargs={"temperature": 0.6}
    )

