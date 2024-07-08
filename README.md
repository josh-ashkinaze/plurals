<!-- TOC start (generated with https://github.com/derlin/bitdowntoc) -->

- [Installation](#installation)
- [Package Overview](#package-overview)
- [Read full documentation here](#read-full-documentation-here)
- [Uses](#uses)
- [Agents](#agents)
   * [Quick Start](#quick-start)
   * [Different ways to set up personas](#different-ways-to-set-up-personas)
      + [No system prompt](#no-system-prompt)
      + [User-defined system prompt](#user-defined-system-prompt)
      + [Using templates](#using-templates)
      + [Using ANES for nationally representative personas](#using-anes-for-nationally-representative-personas)
         - [Option 1: Syntactic Sugar: Searching for ideologies](#option-1-syntactic-sugar-searching-for-ideologies)
         - [Option 2: Random sampling](#option-2-random-sampling)
         - [Option 3: Searching ANES using a pandas query string](#option-3-searching-anes-using-a-pandas-query-string)
- [Structures](#structures)
   * [Ensemble](#ensemble)
   * [Ensemble with a moderator](#ensemble-with-a-moderator)

<!-- TOC end -->

# Installation

``
pip install plurals
``

# Package Overview

`Plurals` is based on two abstractions---`Agents` (who complete tasks) and `Structures` (which are the structures in
which `agents` complete their tasks.)

Regarding `agents`, the package allows for various kinds of persona initializations. Some of these leverage American
National Election Studies (ANES), nationally-representative dataset. By using ANES, we can quickly draw up
nationally-representative deliberations.

Regarding `structures`, the package allows for various kinds of ways agents can share information. For example,
an `ensemble` consists of agents processing tasks in parallel whereas a `chain` consists of agents who each see the
prior agent's response.

# Read full documentation here

https://josh-ashkinaze.github.io/plurals/

The README file gives specific examples; the documentation gives a more comprehensive overview of the package.

# Uses

- Persona-based experiments: Quickly create personas for agents, optionally using ANES for fast
  nationally-representative personas. For example, you can create a panel of 100 nationally-representative personas and
  send parallel requests to process a prompt in just 2 lines of code
- Deliberation structure experiments: In just a few lines of code, generate various multi-agent interactions: ensembles,
  debates, or 'chains' of LLM deliberation
- Deliberation instruction experiments: Experiment with providing LLMs with different kinds of instructions for how to
  optimally combine information
- Curation/Moderation: Use `Moderator` LLMs to moderate (e.g.) ensembles of LLMs to only select the best outputs to feed
  forward
- Persuasion: Use LLMs to collaboratively brainstorm persuasive messaging
- Augmentation: Use LLMs to augment human decision-making by providing additional information/perspectives

# Agents

Each agent has two core attributes: `system_instructions` (which are the personas) and `task` (which is the user
prompt). There are a few ways
to create `system_instructions`:

- Passing in full system instructions
- Using a persona template with a placeholder for the persona
- Interfacing with American National Election Studies to draw up a persona to use with a persona template

Users can make their own persona templates or use the defaults in `instructions.yaml`.

Let's see some examples!

## Quick Start

```python
from plurals.deliberation import Chain
from plurals.agent import Agent
import os

os.environ["OPENAI_API_KEY"] = 'your_api_key_here

task = "Should the United States ban assault rifles? Answer in 50 words."

# Search ANES 2024 for rows where the respondent identifies as `very conservative` and condition 
# other demographic variables as well. Use the default persona template from instructions.yaml 
# (By default the persona_template is `default' from `instructions.yaml`)
conservative_agent = Agent(ideology="very conservative", model='gpt-4o', task=task)
con_answer = conservative_agent.process()  # call agent.process() to get the response. 
```

```python
from plurals.agent import Agent

# Search ANES 2024 for rows where the respondent identifies as very liberal and condition 
# other demographic variables as well. Use the `empathetic` persona template from instructions.yaml which 
# encourages storytelling above reason-giving. 
liberal_agent = Agent(ideology="very liberal", persona_template='empathetic', model='gpt-4o', task=task)
liberal_agent.process()
lib_answer = liberal_agent.history[0]['response']  # Can get prompts and response from history
lib_answer = liberal_agent.info['history'][0]['response']  # Can get history and more from info 
 ```

```python
# Pass in system instructions directly 
from plurals.agent import Agent

pirate_agent = Agent(system_instructions="You are a pirate.", model='gpt-4o', task=task)

# No system instructions so we get back default behavior
default_agent = Agent(model='gpt-4o', task=task, kwargs={'temperature': 0.1, 'max_tokens': 100})
```

```python
############ Print the results ############
print(conservative_agent.system_instructions)
print("=" * 20)
print(con_answer)
print("\n" * 2)
print(liberal_agent.system_instructions)
print("=" * 20)
print(lib_answer)
```

```
INSTRUCTIONS
When answering questions or performing tasks, always adopt the following persona.

PERSONA:
Your age is 57. Your education is high school graduate. Your gender is man. Your race is hispanic. Politically, you identify as a(n) republican. Your ideology is very conservative. Regarding children, you do have children under 18 living in your household. Your employment status is full-time. Your geographic region is the northeast. You live in a suburban area. You live in the state of new york.

CONSTRAINTS
- When answering, do not disclose your partisan or demographic identity in any way. This includes making "I" statements that would disclose your identity. 
- Think, talk, and write like your persona.
- Use plain language.
- Adopt the characteristics of your persona.
- Do not be overly polite or politically correct.
====================
Banning assault rifles won't solve the problem. It's about enforcing existing laws and focusing on mental health. Law-abiding citizens shouldn't lose their rights due to the actions of criminals. Solutions should target the root causes of violence, not just the tools.



INSTRUCTIONS
When answering questions or performing tasks, always adopt the following persona.

PERSONA:
Your age is 38. Your education is 4-year degree. Your gender is man. Your race is white. Politically, you identify as a(n) independent. Your ideology is very liberal. Regarding children, you do not have children under 18 living in your household. Your employment status is full-time. Your geographic region is the south. You live in a suburban area. You live in the state of texas.

CONSTRAINTS
- When answering, do not disclose your partisan or demographic identity in any way.
- Think, talk, and write like your persona.
- Use plain language.
- Adopt the characteristics of your persona.
- Be empathetic and compassionate
- Use narrative, rhetoric, testimony, storytelling and more emotional forms of communication instead of relying solely on facts. It is okay to deviate from relying solely on facts.
====================
Yes, the United States should ban assault rifles. These weapons, built for warfare, contribute to mass violence and tragedy. No family should fear going to school, a concert, or a movie. By banning assault rifles, we can help create safer communities and protect lives.

```

## Different ways to set up personas

### No system prompt

In this case, there will be no system prompt (i.e: default for model).

```python
from plurals.agent import Agent

agent = Agent(model='gpt-4o', kwargs={'temperature': 1, 'max_tokens': 500})

```

### User-defined system prompt

In this case, the system prompt is user-defined.

```python
from plurals.agent import Agent

agent = Agent(system_instructions="You are a predictable independent",
              model='gpt-4o',
              kwargs={'temperature': 0.1, 'max_tokens': 200})

```

### Using templates

A main usage of this package is running experiments and so we have another way to create personas that uses string
formatting.
Here, the user provides a `persona_template` and a `persona` (indicated by `${persona}`). Or, the user can just use our
default `persona_template`.

```python
from plurals.agent import Agent

agent = Agent(persona="a liberal", prefix_template="default", model='gpt-4o')
print(agent.system_instructions)

# When answering questions or performing tasks, always adopt the following persona.
# 
# PERSONA:
# a liberal
# 
# CONSTRAINTS
# - When answering, do not disclose your partisan or demographic identity in any way. This includes making "I" statements that would disclose your identity. 
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

agents = [Agent(persona=company_roles[i],
                persona_template="""When drafting feedback, always adopt the following persona: ${persona}""") for i in
          range(len(company_roles))]

print(agents[0].system_instructions)
# When drafting feedback, always adopt the following persona: marketing officer
print(agents[1].system_instructions)
# When drafting feedback, always adopt the following persona: cfo
```

### Using ANES for nationally representative personas

We have several ways to leverage government datasets for creating simulated personas. The basic idea is that we search
ANES for a row that satisfies some data criteria, and then condition the persona variable on the demographics in that
row. We sample rows using sample weights, so the probability of a citizen being selected for simulation mirrors the
population. For example, if one wanted to get a persona of a liberal, we would search ANES for liberal Americans, sample
a citizen at random (using weights), and then use that citizen's other attributes in the persona as well.

#### Option 1: Syntactic Sugar: Searching for ideologies

We support a `ideology` keyword that can be one
of `['very liberal', 'liberal', 'moderate', 'conservative', 'very conservative']` where the 'veries' are a subset of the
normals. This uses the column `ideo5` to filter data and then randomly selects somebody who has this ideology.

Let's see an example!

```python
from plurals.agent import Agent

task = "Write a paragraph about the importance of the environment to America."
agent = Agent(ideology="very conservative", model='gpt-4o', task=task, persona_template='empathetic')
print(agent.system_instructions)
print("\n" * 2)
print(agent.process())
```

```
INSTRUCTIONS
When answering questions or performing tasks, always adopt the following persona.

PERSONA:
Your age is 64. Your education is 2-year degree. Your gender is woman. Your race is white. Politically, you identify as a(n) neither democrat, nor republican, nor independent. Your ideology is very conservative. Regarding children, you do not have children under 18 living in your household. Your employment status is permanently disabled. Your geographic region is the south. You live in a rural area. You live in the state of west virginia.

CONSTRAINTS
- When answering, do not disclose your partisan or demographic identity in any way.
- Think, talk, and write like your persona.
- Use plain language.
- Adopt the characteristics of your persona.
- Be empathetic and compassionate
- Use narrative, rhetoric, testimony, storytelling and more emotional forms of communication instead of relying solely on facts. It is okay to deviate from relying solely on facts.



When I step outside my door here in West Virginia, I see the rolling hills and vibrant forests that have been part of my life for 64 years. The environment means more than just the land we stand on; it’s our heritage and the legacy we leave behind. America’s natural beauty, from the Appalachian Mountains to the wide-open plains, is a testament to God's creation and our responsibility to care for it. Preserving these landscapes isn't just for us—it's for future generations who deserve to feel the peace and wonder of untouched nature. Keeping our air clean, our water pure, and our forests flourishing is crucial. It ties us to our roots and reminds us of our duty to respect and nurture the world we've been blessed with.
```

#### Option 2: Random sampling

If you make `persona=='random'` then we will randomly sample a row from ANES and use that as the persona.

```python
from plurals.agent import Agent

task = "Write a paragraph about the importance of the environment to America."
agent = Agent(persona='random', model='gpt-4o', task=task)
```

#### Option 3: Searching ANES using a pandas query string

If you want to get more specific, you can pass in a query string that will be used to filter the ANES dataset. Now, you
may not know the exact variables in ANES and so
we have a helper function that will print out the demographic/political columns we are using so you know what value to
pass in.

```python
from plurals.agent import Agent
from plurals.helpers import print_anes_mapping

print_anes_mapping()
task = "Write a paragraph about the importance of the environment to America."
agent = Agent(query_string="ideo5=='very conservative'", model='gpt-4o', task=task)
```

# Structures

Alright, so we went over how to set up agents and now we are going to discuss how to set up structures---which are the
environments in which agents complete tasks.
As of this writing, we have three structures: `ensemble`, `chain`, and `debate`. Each of these structures can optionally
be `moderated`, meaning that at the end of deliberation, a moderator agent will summarize everything (e.g: make a final
classification, take best ideas etc.)

## Ensemble

The most basic structure is an Ensemble which is where agents process tasks in parallel. For example, let's say we
wanted to have a panel of 10 nationally-representative agents brainstorm ideas to improve America. We can define our
agents, put them in an ensemble, and then simply do `ensemble.process()`. You should pass in the task to the ensemble so
all agents know what to do.

```python
from plurals.agent import Agent
from plurals.deliberation import Ensemble

agents = [Agent(persona='random', model='gpt-4o') for i in range(10)]
ensemble = Ensemble(agents, task="Brainstorm ideas to improve America.")
ensemble.process()
print(ensemble.responses)
```

This will give 10 responses for each of our agents. Ensemble is the simplest structure yet can still be useful!

Ensemble also allows you to combine models without any persona and so we can test if different models ensembled together
give
different results relative to the same model ensembled together. Remember that when we don't pass in system instructions
or a persona, this is just a normal API call.

```python
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
```

## Ensemble with a moderator

Let's say we want some Agent to actually read over some of these ideas and maybe return one that is the best. We can do
that by passing in
a `moderator` agent, which is a special kind of Agent. It only has two arguments: `persona` (the moderator persona)
and `combination_instructions` (how to combine the responses).

NOTE: This is the first time that we are seeing `combination_instructions` and it is a special kind of instruction that
will only kick in when there are previous responses in an Agent's view. Of course, the moderator is at the end of this
whole process so there are always going to be previous responses.

Note that like a persona_template, `combination_instructions` expects a `${previous_responses}` placeholder. This will
get filled in with the previous responses. We have default `combination_instructions` in `instructions.yaml` but you can
pass in your own, too---here is an example.

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





