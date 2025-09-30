


# Plurals: A System for Guiding LLMs Via Simulated Social Ensembles
    
**Package Stats 📊**

![PyPI - Downloads](https://img.shields.io/pypi/dm/plurals)
![GitHub last commit](https://img.shields.io/github/last-commit/josh-ashkinaze/plurals)
![GitHub Created At](https://img.shields.io/github/created-at/josh-ashkinaze/plurals)

**Package Build (Tests/Doc Creation/PyPi Releases) 👌**

[![Build](https://github.com/josh-ashkinaze/plurals/actions/workflows/ci.yml/badge.svg)](https://github.com/josh-ashkinaze/plurals/actions/workflows/ci.yml)
[![Push to pypy](https://github.com/josh-ashkinaze/plurals/actions/workflows/python-publish.yml/badge.svg)](https://github.com/josh-ashkinaze/plurals/actions/workflows/python-publish.yml)
![PyPI](https://img.shields.io/pypi/v/plurals)

**Paper 📜** [(Click here!)](https://arxiv.org/abs/2409.17213)

**Documentation 📋** [(Click here!)](https://josh-ashkinaze.github.io/plurals/)


# Cite ℹ️
If you use Plurals in your research, please cite the following [paper](https://arxiv.org/abs/2409.17213) appearing at CHI 25 (Honorable Mention):

_Bibtex:_
```
@inproceedings{ashkinaze2025plurals,
  author = {Ashkinaze, Joshua and Fry, Emily and Edara, Narendra and Gilbert, Eric and Budak, Ceren},
  title = {Plurals: A System for Guiding LLMs Via Simulated Social Ensembles},
  booktitle = {CHI Conference on Human Factors in Computing Systems},
  series = {CHI '25},
  year = {2025},
  month = may,
  location = {Yokohama, Japan},
  publisher = {Association for Computing Machinery},
  address = {New York, NY, USA},
  pages = {1--27},
  numpages = {27},
  doi = {10.1145/3706598.3713675},
  url = {https://doi.org/10.1145/3706598.3713675}
}
```

_APA:_
```
Ashkinaze, J., Fry, E., Edara, N., Gilbert, E., & Budak, C. (2025). Plurals: A system for guiding LLMs via simulated social ensembles. In CHI Conference on Human Factors in Computing Systems (CHI '25, pp. 1-27). Association for Computing Machinery. https://doi.org/10.1145/3706598.3713675
```

# Overview 🌌
<img src="https://raw.githubusercontent.com/josh-ashkinaze/plurals/main/assets/figure1.png" alt="System Diagram" width="100%">

Plurals is an end-to-end generator of simulated social ensembles. (1) **Agents** complete tasks within (2) **Structures**, with communication optionally summarized by (3) **Moderators**. Plurals integrates with government datasets (1a) and templates, some inspired by democratic deliberation theory (1b). 

The building block is Agents, which are large language models (LLMs) that have system instructions and tasks. System instructions can be generated from user input, government datasets (American National Election Studies; ANES), or persona templates. Agents exist within Structures, which define what information is shared. Combination instructions tell Agents how to combine the responses of other Agents when deliberating in the Structure. Users can customize an Agent's combination instructions or use existing templates drawn from deliberation literature and beyond. Moderators aggregate responses from multi-agent deliberation.

Plurals includes support for multiple information-sharing structures (e.g., chains, graphs, debates, ensembles) and [templates](https://github.com/josh-ashkinaze/plurals/blob/main/plurals/instructions.yaml) for customizing LLM deliberation within these.

# Detailed Documentation 📋

https://josh-ashkinaze.github.io/plurals/

# Quick Start ⚡

## Installation

```markddown
pip install plurals
```

## Set environment variables

```python

import os
os.environ["OPENAI_API_KEY"] = 'your_openai_key'
os.environ["ANTHROPIC_API_KEY"] = 'your_anthropic_key'
```

## Create a nationally representative ensemble of Agents portrayed by different LLMs

```python
from plurals.agent import Agent
from plurals.deliberation import Ensemble, Moderator

task = "What, specifically, would make commuting on a bike more appealing to you? Answer from your perspective. Be specific. You are in a focus group."
agents = [Agent(persona='random', model='gpt-4o') for _ in range(20)]
ensemble = Ensemble(agents=agents, task=task)
ensemble.process()
for r in ensemble.responses:
    print(r)

```

## Create a directed acyclic graph of Agents for story development

<div style="text-align: center;">
    <img src="https://raw.githubusercontent.com/josh-ashkinaze/plurals/main/assets/mermaid_diagram.svg" alt="System Diagram" width="80%">
</div>

```python
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

```




# Issues and Features 📝

Plurals is run by a small and energetic team of academics doing the best they can [1]. To report bugs or feature requests, open a GitHub issue. We strongly encourage you to use our Bug or Feature Request issue templates; these make it easy for us to respond effectively to the issue. 

[1] Language adopted from (https://github.com/davidjurgens/potato). 


# Some Potential Uses 🔨🔭🔦✂️


- Persona-based experiments (Ex: Create a panel of nationally representative personas)

- Deliberation structure experiments (What are optimal information-sharing structures?) 

- Deliberation instruction experiments (What are optimal instructions for combining information?) 

- Agent-based models (Ex: understanding contagion in AI networks)

- Curation (Ex: To what extent can Moderator LLMs filter and select the best outputs from other LLMs?)

- Steerable guardrails (Ex: Can LLM deliberation steer abstentions?)

- Persuasive messaging (Use many LLMs to collaboratively brainstorm and refine persuasive messaging for different audiences; Experiment with simulated focus groups)

- Viewpoint augmentation (Provide varied perspectives and information from multiple agents)

- Creative ideation (e.g., get ideas from multiple LLMs with different perspectives/roles for hypothesis generation, creative ideas, or product design)

# Collaborators 🤝

If you are interested in collaborating, please reach out to Joshua Ashkinaze (jashkina@umich.edu). We are 
actively running both human and AI experiments around (1) how and when simulated social ensembles augment humans; (2) using Plurals for moderation.  

# Updates 🆕
- Paper to appear at CHI 2025 with Honorable Mention!
- Changes to debate to decrease sycophancy
- Names of Agents in DAG are visible to other Agents (i.e., instead of "Response 0: Resp0", "Response 1: Resp1", etc., Agents see "PlotAgent: Resp", "CharacterAgent: Resp", etc.)
