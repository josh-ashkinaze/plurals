

- [Installation](#installation)
- [Package Overview](#package-overview)
- [Docs](#docs)
- [Agents](#agents)
  * [Quick Start](#quick-start)
  * [Different ways to set up personas](#different-ways-to-set-up-personas)
    + [No system prompt](#no-system-prompt)
    + [User-defined system prompt.](#user-defined-system-prompt)
    + [Using templates](#using-templates)
    + [Using ANES for nationally representative personas](#using-anes-for-nationally-representative-personas)
      - [Option 1: Syntactic Sugar: Searching for ideologies](#option-1--syntactic-sugar--searching-for-ideologies)
      - [Option 2: Random sampling](#option-2--random-sampling)
      - [Option 3: Searching ANES using a pandas query string](#option-3--searching-anes-using-a-pandas-query-string)
- [Structures](#structures)
  * [Ensemble](#ensemble)
  * [Ensemble with a moderator](#ensemble-with-a-moderator)

<small><i><a href='http://ecotrust-canada.github.io/markdown-toc/'>Table of contents generated with markdown-toc</a></i></small>


# Installation

``
pip install plurals
``


# Package Overview
`Plurals` is based on two abstractions---`Agents` (who complete tasks) and `Structures` (which are the structures in which `agents` complete their tasks.)

Regarding `agents`, the package allows for various kinds of persona initializations. Some of these leverage American National Electoral Studies (ANES), nationally-representative dataset. By using ANES, we can quickly draw up personas that represent the population. 

Regarding `structures`, the package allows for various kinds of ways agents can share information. For example, an `ensemble` consists of agents processing tasks in parallel whereas a `chain` consists of agents who each see the prior agent's response. 

# Docs 
https://josh-ashkinaze.github.io/plurals/

# Agents
Each agent has two core attributes: `system_instructions` (which are the personas) and `task` (which is the user prompt). There are a few ways
to create `system_instructions`:
- Passing in full system instructions
- Combining a persona and a persona template
- Interfacing with American National Election Studies to draw up a persona to use with a persona template 

Users can make their own persona templates or use the defaults in `instructions.yaml`. So let's see some examples!


## Quick Start

```python
from plurals.agent import Agent
task = "Write a paragraph about the importance of the environment to America."

# Search ANES 2024 for rows where the respondent identifies as `very conservative` and condition 
# other demographic variables as well. Use the default persona template from instructions.yaml 
# by default the persona_template is `default' from `instructions.yaml` 
conservative_agent = Agent(ideology="very conservative", model='gpt-4o', task=task)

# Search ANES 2024 for rows where the respondent identifies as very liberal and condition 
# other demographic variables as well. Use the `empathetic` persona template from instructions.yaml 
liberal_agent = Agent(ideology="very liberal", persona_template='empathic', model='gpt-4o', task=task)

# Pass in system instructions directly 
pirate_agent = Agent(system_instructions="You are a pirate.", model='gpt-4o', task=task)

# No system instructions so we get back default behavior
default_agent = Agent(model='gpt-4o', task=task, kwargs={'temperature':0.1, 'max_tokens':100})


print(conservative_agent.system_instructions)
print(liberal_agent.system_instructions)
```

## Different ways to set up personas


### No system prompt

In this case, there will be no system prompt (i.e: default for model). 

```python
from plurals.agent import Agent
agent = Agent(system_instructions="You are a predictable independent", 
              model='gpt-4o',
              kwargs={'temperature':0.1, 'max_tokens':500})

```

### User-defined system prompt. 

In this case, the system prompt is user-defined. 

```python
from plurals.agent import Agent
agent = Agent(system_instructions="You are a predictable independent", 
              model='gpt-4o',
              kwargs={'temperature':0.1, 'max_tokens':500})

```

### Using templates
A main usage of this package is running experiments and so we have another way to create personas that uses string formatting. 
Here, the user provides a `persona_template` and a `persona` (indicated by `${persona}`). Or, the user can just use our default `persona_template`. 


```python
from plurals.agent import Agent
agent = Agent(persona="a liberal", prefix_template="default", model='gpt-4o')
print(agent.system_instructions)

# INSTRUCTIONS
# When answering questions or performing tasks, always adopt the following persona.
# 
# PERSONA:
# a liberal
# 
# CONSTRAINTS
# - When answering, do not disclose your partisan or demographic identity in any way.
# - Think, talk, and write like your persona.
# - Use plain language.
# - Adopt the characteristics of your persona.
# - Do not be overly polite or politically correct.
```

You can also create your own template of course, just make sure to add a `${persona}` placeholder in the template. 

```python
from plurals.agent import Agent


persona_template = """When drafting feedback, always adopt the following persona ${persona}"""
company_roles = ['marketing officer', 'cfo']

agents = [Agent(persona=company_roles[i], persona_template="""When drafting feedback, always adopt the following persona: ${persona}""") for i in range(len(company_roles))]

print(agents[0].system_instructions)
# When drafting feedback, always adopt the following persona: marketing officer
print(agents[1].system_instructions)
# When drafting feedback, always adopt the following persona: cfo
```

### Using ANES for nationally representative personas 
We have several ways to leverage government datasets for creating simulated personas. The basic idea is that we search ANES for a row that satisifes some data criteria, and then condition the persona variable on the demographics in that row. So, if one wanted to get a persona of a liberal, we would search ANES for liberal Americans, sample a citizen at random, and then use their other attributes in the persona as well. 

#### Option 1: Syntactic Sugar: Searching for ideologies 
We support a `ideology` keyword that can be one of `['very liberal', 'liberal', 'moderate', 'conservative', 'very conservative']` where the 'veries' are a subset of the normals. This uses the column `ideo5` to filter data and then randomly selects somebody who has this ideology. 

Let's see an example!

```python
from plurals.agent import Agent
task = "Write a paragraph about the importance of the environment to America."
agent = Agent(ideology="very conservative", model='gpt-4o', task=task)
```

#### Option 2: Random sampling 
If you make `persona=='random'` then we will randomly sample a row from ANES and use that as the persona. 

```python
from plurals.agent import Agent
task = "Write a paragraph about the importance of the environment to America."
agent = Agent(persona='random', model='gpt-4o', task=task)
```
#### Option 3: Searching ANES using a pandas query string
If you want to get more specific, you can pass in a query string that will be used to filter the ANES dataset. Now, you may not know the exact variables in ANES and so 
we have a helper function that will print out the demographic/political columns we are using so you know what value to pass in. 

```python
from plurals.agent import Agent
from plurals.helpers import print_anes_mapping
print_anes_mapping()
task = "Write a paragraph about the importance of the environment to America."
agent = Agent(query_string="ideo5=='very conservative'", model='gpt-4o', task=task)
```


# Structures
Alright, so we went over how to set up agents and now we are going to discuss how to set up structures---which are the environments in which agents complete tasks.
As of this writing, we have three structures: `ensemble`, `chain`, and `debate`. Each of these structures can optionally be `moderated`, meaning that at the end of deliberation, a moderator agent will summarize everything (e.g: make a final classification, take best ideas etc.)

## Ensemble
The most basic structure is an Ensemble which is where agents process tasks in parallel. For example, let's say we wanted to have a panel of 10 nationally-representative agents brainstorm ideas to improve America. We can define our agents, put them in an ensemble, and then simply do `ensemble.process()`. You should pass in the task to the ensemble so all agents know what to do. 

    
```python
from plurals.agent import Agent
from plurals.deliberation import Ensemble
agents = [Agent(persona='random', model='gpt-4o') for i in range(10)]
ensemble = Ensemble(agents, task = "Brainstorm ideas to improve America.")
ensemble.process()
print(ensemble.responses)
```
So we see that this gave 10 responses for each of our agents. Ensemble is the simplest structure yet can still be useful! 

## Ensemble with a moderator
Let's say we want some Agent to actually read over some of these ideas and maybe return one that is the best. We can do that by passing in 
a `moderator` agent, which is a special kind of Agent. It only has two arguments: `persona` (the moderator persona) and `combination_instructions` (how to combine the responses). 

Note that like a persona_template, `combination_instructions` expects a `${previous_responses}` placeholder. This will get filled in with the previous responses. We have default `combination_instructions` in `instructions.yaml` but you can pass in your own, too---here is an example.

 ```python
 from plurals.agent import Agent
 from plurals.deliberation import Ensemble
 task = "Brainstorm ideas to improve America."
 combination_instructions = "INSTRUCTIONS\nReturn a master response that takes the best part of previous responses.\nPREVIOUS RESPONSES: ${previous_responses}\nRETURN a json like {'response': 'the best response', 'rationale':Rationale for integrating responses} and nothing else"
 agents = [Agent(persona='random', model='gpt-4o', task=task) for i in range(10)]
 moderator = Agent(persona='random', model='gpt-4o', task=task)
 ensemble = Ensemble(agents, moderator=moderator)
 ensemble.process()
 print(ensemble.responses)
 print(ensemble.moderator_response)
   ```



