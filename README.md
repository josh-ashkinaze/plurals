<!-- TOC start (generated with https://github.com/derlin/bitdowntoc) -->

- [System Diagram ](#system-diagram)
- [Installation](#installation)
- [Package Overview](#package-overview)
- [Read full documentation here](#read-full-documentation-here)
- [Uses](#uses)
- [Agents](#agents)
   * [Quick Start](#quick-start)
   * [Inspecting the exact prompts that an Agent is doing](#inspecting-the-exact-prompts-that-an-agent-is-doing)
   * [Different ways to set up system prompt](#different-ways-to-set-up-system-prompt)
      + [No system prompt](#no-system-prompt)
      + [User-defined system prompt](#user-defined-system-prompt)
      + [Using templates](#using-templates)
      + [Using ANES for nationally representative personas](#using-anes-for-nationally-representative-personas)
         - [Option 1: Syntax Sugar: Searching for ideologies](#option-1-syntax-sugar-searching-for-ideologies)
         - [Option 2: Random sampling](#option-2-random-sampling)
         - [Option 3: Searching ANES using a pandas query string](#option-3-searching-anes-using-a-pandas-query-string)
- [Structures](#structures)
   * [Types of Structures](#types-of-structures)
   * [Ensemble](#ensemble)
   * [Tracing what is going on in Structures ](#tracing-what-is-going-on-in-structures)
   * [Ensemble with a moderator / Moderator intro](#ensemble-with-a-moderator-moderator-intro)
      + [Setting a Moderator's System Instructions](#setting-a-moderators-system-instructions)
         - [Personas ](#personas)
         - [Moderator system instructions set directly](#moderator-system-instructions-set-directly)
         - [Auto-Moderators](#auto-moderators)
   * [Chain](#chain)
   * [Chain with a moderator](#chain-with-a-moderator)
   * [Debate](#debate)
   * [Debate with a moderator](#debate-with-a-moderator)
   * [History](#history)

<!-- TOC end -->


<!-- TOC --><a name="system-diagram"></a>
# System Diagram 
<img src="https://github.com/josh-ashkinaze/plurals/raw/main/system_diagram.jpeg" alt="System Diagram" width="100%">


<!-- TOC --><a name="installation"></a>
# Installation

`pip install plurals`

<!-- TOC --><a name="package-overview"></a>
# Package Overview

`Plurals` is based on two abstractions---`Agents` (who complete tasks) and `Structures` (which are the structures in
which `agents` complete their tasks.)

Regarding `agents`, the package allows for various kinds of persona initializations. Some of these leverage American
National Election Studies (ANES), nationally-representative dataset. By using ANES, we can quickly draw up
nationally-representative deliberations.

Regarding `structures`, the package allows for various kinds of ways agents can share information. For example,
an `ensemble` consists of agents processing tasks in parallel whereas a `chain` consists of agents who each see the
prior agent's response.

<!-- TOC --><a name="read-full-documentation-here"></a>
# Read full documentation here

https://josh-ashkinaze.github.io/plurals/

The README file gives specific examples; the documentation gives a more comprehensive overview of the package.



<!-- TOC --><a name="uses"></a>
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

<!-- TOC --><a name="agents"></a>
# Agents

Each agent has two core attributes: `system_instructions` (which are the personas) and `task` (which is the user
prompt). There are a few ways
to create `system_instructions`:

- Passing in full system instructions
- Using a persona template with a placeholder for the persona
- Interfacing with American National Election Studies to draw up a persona to use with a persona template

Users can make their own persona templates or use the defaults in `instructions.yaml`.

Let's see some examples!

<!-- TOC --><a name="quick-start"></a>
## Quick Start

```python
from plurals.agent import Agent
import os
import textwrap

# Set your keys as an env variable
os.environ["OPENAI_API_KEY'] = 'yourkey'
os.environ["ANTHROPIC_API_KEY'] = 'yourkey'


# Function to wrap text for docs 
def printwrap(text, width=80):
    wrapped_text = textwrap.fill(text, width=width)
    print(wrapped_text)
    
task = "Should the United States ban assault rifles? Answer in 50 words."

# Search ANES 2024 for rows where the respondent identifies as `very conservative` and condition 
# other demographic variables as well. Use the default persona template from instructions.yaml 
# (By default the persona_template is `default' from `instructions.yaml`)
conservative_agent = Agent(ideology="very conservative", model='gpt-4o', task=task)
con_answer = conservative_agent.process()  # call agent.process() to get the response. 
```

Note that we can call Agents to process tasks in two ways:
```python
task = "Should the United States ban assault rifles? Answer in 50 words."

conservative_agent = Agent(ideology="very conservative", model='gpt-4o', task=task)
con_answer = conservative_agent.process()  # call agent.process() to get the response. 

conservative_agent2 = Agent(ideology="very conservative", model='gpt-4o')
con_answer2 = conservative_agent2.process(task)

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
############ Print the results ############
print(conservative_agent.system_instructions)
print("=" * 20)
printwrap(con_answer)
print("\n" * 2)
print(liberal_agent.system_instructions)
print("=" * 20)
printwrap(lib_answer)
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
Banning assault rifles won't solve the problem. It's about enforcing existing
laws and focusing on mental health. Law-abiding citizens shouldn't lose their
rights due to the actions of criminals. Solutions should target the root causes
of violence, not just the tools.


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
Yes, the United States should ban assault rifles. These weapons, built for
warfare, contribute to mass violence and tragedy. No family should fear going to
school, a concert, or a movie. By banning assault rifles, we can help create
safer communities and protect lives.
```

<!-- TOC --><a name="inspecting-the-exact-prompts-that-an-agent-is-doing"></a>
## Inspecting the exact prompts that an Agent is doing
It's important to know what exactly is going on under the hood so we have a few ways to do this!



By calling `agent.info` we get a dictionary with everything about the Agent---their plates, their full system 
instructions and one of the keys is called `history`. That key is comprised of the prompts and responses of agents. 
You can get this by calling `agent.history` if that's your main interest. You can also access the responses of agents more directly by simply getting `agent.responses` 
```python
from plurals.agent import Agent
a = Agent(ideology="very conservative", model='gpt-4o', task="A task here")
a.process()
print(agent.info)
print(agent.history)
print(agent.responses)
```



Let's say you don't want to use persona templates. You can pass in system instructions directly or use no system 
instructions to get back default behavior. 
```python
from plurals.agent import Agent

# Pass in system instructions directly 
pirate_agent = Agent(system_instructions="You are a pirate.", model='gpt-4o', task=task)

# No system instructions so we get back default behavior
default_agent = Agent(model='gpt-4o', task=task, kwargs={'temperature': 0.1, 'max_tokens': 100})
```


<!-- TOC --><a name="different-ways-to-set-up-system-prompt"></a>
## Different ways to set up system prompt
Agent has many different ways to set system prompts. Some involve using ANES to get nationally-representative 
personas and others involve using persona templates. But for simplicity, you can also not pass in any system prompt 
or just pass in your own system prompt directly. 

<!-- TOC --><a name="no-system-prompt"></a>
### No system prompt

In this case, there will be no system prompt (i.e: default for model). Also note that you can pass in kwargs to the 
model's completion function. These are provided by LiteLLM. See (https://litellm.vercel.app/docs/completion/input)

```python
from plurals.agent import Agent

agent = Agent(model='gpt-4o', kwargs={'temperature': 1, 'max_tokens': 500})

```

<!-- TOC --><a name="user-defined-system-prompt"></a>
### User-defined system prompt

In this case, the system prompt is user-defined.

```python
from plurals.agent import Agent

agent = Agent(system_instructions="You are a predictable independent",
              model='gpt-4o',
              kwargs={'temperature': 0.1, 'max_tokens': 200})

```

<!-- TOC --><a name="using-templates"></a>
### Using templates

A main usage of this package is running experiments and so we have another way to create personas that uses string
formatting. Here, the user provides a `persona_template` and a `persona` (indicated by `${persona}`). Or, the user can just use our
default `persona_template`.

```python
from plurals.agent import Agent

agent = Agent(persona="a liberal", persona_template="default", model='gpt-4o')
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

You can also create your own template. Just make sure to add a `${persona}` placeholder in the template. 

```python
from plurals.agent import Agent

company_roles = ['marketing officer', 'cfo']

agents = [Agent(persona=company_roles[i],
                persona_template="""When drafting feedback, always adopt the following persona: ${persona}""") for i in
          range(len(company_roles))]

print(agents[0].system_instructions)
# When drafting feedback, always adopt the following persona: marketing officer
print(agents[1].system_instructions)
# When drafting feedback, always adopt the following persona: cfo
```

<!-- TOC --><a name="using-anes-for-nationally-representative-personas"></a>
### Using ANES for nationally representative personas

We have several ways to leverage government datasets for creating simulated personas. The basic idea is that we search
ANES for a row that satisfies some data criteria, and then condition the persona variable on the demographics in that
row. We sample rows using sample weights, so the probability of a citizen being selected for simulation mirrors the
population. For example, if one wanted to get a persona of a liberal, we would search ANES for liberal Americans, sample
a citizen at random (using weights), and then use that citizen's other attributes in the persona as well.

As of this writing:
(1) We are using ANES Pilot Study data from March 2024.
(2) The persona populates the following fields (see `plurals/anes-mapping.yaml` on GitHub for specific variables):
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

<!-- TOC --><a name="option-1-syntax-sugar-searching-for-ideologies"></a>
#### Option 1: Syntax Sugar: Searching for ideologies

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
printwrap(agent.process())
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


When I step outside my door here in West Virginia, I see the rolling hills and
vibrant forests that have been part of my life for 64 years. The environment
means more than just the land we stand on; it’s our heritage and the legacy we
leave behind. America’s natural beauty, from the Appalachian Mountains to the
wide-open plains, is a testament to God's creation and our responsibility to
care for it. Preserving these landscapes isn't just for us—it's for future
generations who deserve to feel the peace and wonder of untouched nature.
Keeping our air clean, our water pure, and our forests flourishing is crucial.
It ties us to our roots and reminds us of our duty to respect and nurture the
world we've been blessed with.
```

<!-- TOC --><a name="option-2-random-sampling"></a>
#### Option 2: Random sampling

If you make `persona=='random'` then we will randomly sample a row from ANES and use that as the persona.

```python
from plurals.agent import Agent

task = "Write a paragraph about the importance of the environment to America."
agent = Agent(persona='random', model='gpt-4o', task=task)
```

<!-- TOC --><a name="option-3-searching-anes-using-a-pandas-query-string"></a>
#### Option 3: Searching ANES using a pandas query string

If you want to get more specific, you can pass in a query string that will be used to filter the ANES dataset. Now, you
may not know the exact variables in ANES and so
we have a helper function that will print out the demographic/political columns we are using so you know what value to
pass in.


```python
from plurals.helpers import print_anes_mapping

print_anes_mapping()
```
This will show a number of variables and their allowed values but just to give an exercpt:

```markdown
ANES Variable Name: gender4
Man
Woman
Non-binary
Other
```

So now we know that we can construct a query string that uses `gender4` and the values `Man`, `Woman`, `Non-binary`, and
`Other`.


Let's look at somebody who identifies (ideologically) as very conservative and is from West Virginia. 

```python
from plurals.agent import Agent
from plurals.helpers import print_anes_mapping

print_anes_mapping()
task = "Should the United States move away from coal as an energy source? Answer Yes or No and provide a rationale."
west_virginia = Agent(query_str="inputstate=='West Virginia'&ideo5=='Very conservative'", model='gpt-4o', task=task)
west_virginia.process()
```

```markdown
No.  Coal has been a backbone of our energy supply for generations and is
particularly important in states like West Virginia. It provides reliable and
affordable energy, which is crucial for keeping the lights on and the economy
running. Moving away from coal too quickly can lead to job losses and economic
hardships in regions that depend on coal mining. Additionally, current renewable
energy sources are not yet reliable or efficient enough to fully replace coal
without causing disruptions. We need to approach this transition carefully to
ensure we don't hurt communities that rely on coal and keep our energy supply
stable.
```

Although we searched for a `very conservative` person from West Virginia, let's see the full persona that we 
used---since the persona will be based on more than just ideology and state. 
```python
print(west_virginia.persona)
```

```markdown
Your age is 72. Your education is post-grad. Your gender is woman. Your race is
white. Politically, you identify as a(n) independent. Your ideology is very
conservative. Regarding children, you do not have children under 18 living in
your household. Your employment status is retired. Your geographic region is the
south. You live in a rural area. You live in the state of west virginia
```

<!-- TOC --><a name="structures"></a>
# Structures

<!-- TOC --><a name="types-of-structures"></a>
## Types of Structures

We went over how to set up agents and now we are going to discuss how to set up structures---which are the
environments in which agents complete tasks. As of this writing, we have three structures: `ensemble`, `chain`, and 
`debate`. Each of these structures can optionally be `moderated`, meaning that at the end of deliberation, a moderator 
agent will summarize everything (e.g: make a final classification, take best ideas etc.)

<!-- TOC --><a name="ensemble"></a>
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

<!-- TOC --><a name="tracing-what-is-going-on-in-structures"></a>
## Tracing what is going on in Structures 
To get a better sense of what is going on, we can access information of both the ensemble and the agents. 

```python
for agent in ensemble.agents:
    print(agent.info) # Will get info about the agent
    print(agent.history) # Will get the history of the agent's prompts so you can see their API calls

# Will give a dictionary of information with one key for `structure` (i.e: information related 
# to the Structure and one key called `agents` (i.e: `agent.info` for each of the agents in the Structure) 
print(ensemble.info) 
print(ensemble.responses) # Will give the responses of the ensemble

```

Ensemble also allows you to combine models without any persona, and so we can test if different models ensembled 
together give different results relative to the same model ensembled together. Remember that when we don't pass in 
system instructions or a persona, this is just a normal API call.

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

<!-- TOC --><a name="ensemble-with-a-moderator-moderator-intro"></a>
## Ensemble with a moderator / Moderator intro

Let's say we want some Agent to actually read over some of these ideas and maybe return one that is the best. We can do
that by passing in  a `moderator` agent, which is a special kind of Agent. It only has three arguments: `persona` (the 
moderator persona), `system_instructions` (which if passed in will override a persona) and `combination_instructions` 
(how to combine the responses).

**NOTE**: This is the first time that we are seeing `combination_instructions` and it is a special kind of instruction that
will only kick in when there are previous responses in an Agent's view. Of course, the moderator is at the end of this
whole process so there are always going to be previous responses.

Note that like a persona_template, `combination_instructions` expects a `${previous_responses}` placeholder. This will
get filled in with the previous responses. We have default `combination_instructions` in `instructions.yaml` and other 
options like chain, debate, and voting. You can also pass in your own, too---here is an example.

```python
from plurals.agent import Agent
from plurals.deliberation import Ensemble, Moderator

task = "Brainstorm ideas to improve America."
# Custom moderator combination instructions
combination_instructions = "INSTRUCTIONS\nReturn a master response that takes the best part of previous responses.\nPREVIOUS RESPONSES: ${previous_responses}\nRETURN a json like {'response': 'the best response', 'rationale':Rationale for integrating responses} and nothing else"
agents = [Agent(persona='random', model='gpt-4o') for i in range(10)] # random ANES agents
moderator = Moderator(persona='default', model='gpt-4o') # default moderator persona
ensemble = Ensemble(agents, moderator=moderator, task=task, combination_instructions=combination_instructions)
ensemble.process()
print(ensemble.responses)
```

<!-- TOC --><a name="setting-a-moderators-system-instructions"></a>
### Setting a Moderator's System Instructions
<!-- TOC --><a name="personas"></a>
#### Personas 
Like Agents, `personas` and `system_instructions` are different ways to set up the moderator's system instructions. 
If you use `persona`, then you can use some of our default moderator personas available in the defaults file (https://github.com/josh-ashkinaze/plurals/blob/main/plurals/instructions.yaml
). For example, if you pass in `persona='voting'`, then we will use a moderator persona meant for voting.

```python
from plurals.deliberation import Moderator

a = Moderator(persona='voting', model='gpt-4o', combination_instructions="voting")
```
These personas all exepect a placeholder for ${task} that will get replaced with the Structure's task. You can 
define your own persona too. When passed into a structure, the ${task} placeholder will be replaced with the actual 
task. 
```python
from plurals.deliberation import Moderator

mod = Moderator(persona="You are a neutral moderator overseeing this task, ${task}", model='gpt-4o', 
combination_instructions="voting")

```

<!-- TOC --><a name="moderator-system-instructions-set-directly"></a>
#### Moderator system instructions set directly
You can also set system instructions directly much like with Agents and this will have a similar effect to custom 
personas. 

```python
from plurals.deliberation import Moderator

mod = Moderator(system_instructions="You are a neutral moderator overseeing this task, ${task}", model='gpt-4o', 
combination_instructions="voting")
```
The difference is that system_instructions is not linked with our templates so you cannot do things like 
`system_instructions='default'` like you can with `persona='default'`.

<!-- TOC --><a name="auto-moderators"></a>
#### Auto-Moderators
We have a special option where if the `system_instructions` of a moderator are set to `auto` then the moderator will,
given a task, come up with its own system instructions. So here's how to do this!

```python
from plurals.deliberation import Moderator, Ensemble, Chain
from plurals.agent import Agent

task = ("Your goal is to come up with the most creative ideas possible for pants. We are maximizing creativity. Answer"
        " in 20 words.")
a = Agent(model='gpt-4o')
b = Agent(model='gpt-3.5-turbo')
# By putting the moderator in the Ensemble we are going to 
# trigger the auto-mod generator 
ensemble = Chain([a, b], moderator=Moderator(system_instructions='auto', model='gpt-4o'), task=task)
```

So let's see what the moderator thinks it should be doing with this information. 

``` python
print(ensemble.moderator.system_instructions)
```

```
Group similar ideas together, prioritize uniqueness and novelty. Highlight standout concepts and remove duplicates. Ensure the final list captures diverse and imaginative designs.
```

Here are ways to use auto-moderation. 


```python
from plurals.deliberation import Moderator, Ensemble, Chain
from plurals.agent import Agent
task = "Come up with creative ideas"

# This will trigger the auto-mod module to generate its own system instructions. This is a straightforward way to
# use auto-moderators. 
mod = Moderator(system_instructions='auto', model='gpt-4o', task=task)

# Simply defining the moderator in the Structure will inherit the structure's task so this is also a simple way to hae
# the Moderator bootstrap its own instructions based on the task. 
a = Agent(model='gpt-4o')
b = Agent(model='gpt-3.5-turbo')
ensemble = Chain([a, b], moderator=Moderator(system_instructions='auto', model='gpt-4o'), task=task)


# You can also turn a normal moderator into an auto-moderator. 
mod = Moderator(system_instructions="some boring initial instructions",  model='gpt-4o')
mod.generate_and_set_system_instructions(task=task)

# Or, you can generate instructions and inspect them before setting them. You can generate multiple times of course. 
mod = Moderator(system_instructions="some boring initial instructions",  model='gpt-4o')
print(mod.generate_system_instructions(task=task))

# Review all submitted responses and identify the top 5 ideas displaying the highest level of creativity. Prioritize originality, novelty, and uniqueness in the design and functionality of the pants. Summarize these top ideas succinctly.
mod.system_instructions = "Review all submitted responses and identify the top 5 ideas displaying the highest level of creativity. Prioritize originality, novelty, and uniqueness in the design and functionality of the pants. Summarize these top ideas succinctly."



```





<!-- TOC --><a name="chain"></a>
## Chain

Another structure is a Chain which is where agents process tasks in a sequence. A Chain consists of agents who
each see the prior agent's response. For example, let's say we wanted to have a panel of agents with diverse backgrounds 
(e.g. diverse ideologies, genders, racial backgrounds, educational backgrounds, etc.) to discuss the topic of climate 
change. We can define our agents, put them in a chain, and then simply do `chain.process()`. You should pass in the 
task to the chain, so all agents know what to do.

```python
from plurals.agent import Agent
from plurals.deliberation import Chain

agent1 = Agent(persona='a liberal woman from Missouri', model='gpt-4o')
agent2 = Agent(persona='a 24 year old hispanic man from Florida', model='gpt-4o')
agent3 = Agent(persona='an elderly woman with a PhD', model='gpt-4o')

chain = Chain([agent1, agent2, agent3], task="How should we combat climate change?", combination_instructions="chain")
chain.process()
print(chain.final_response)
```

This will give a response that combines the best points from all of our agents. Chain is one of the best structures for 
deliberation and reaching a consensus among agents.

NOTE: In the above example, we passed in `combination_instructions` to Chain. `combination_instructions` is a special 
kind of instruction that will only kick in when there are previous responses in an Agent's view. If you pass 
`combination_instructions` into a chain, all the agents will inherit it. 

Recall that `combination_instructions` expects a `${previous_responses}` placeholder if it is not one of the default 
options that we offer.  This placeholder would get filled in with the previous responses. In the above example, we passed in "chain" 
instructions, so the chain option of combination_instructions will be read from the `instructions.yaml`. See that 
file for templates. 


<!-- TOC --><a name="chain-with-a-moderator"></a>
## Chain with a moderator

Let's say we want some Agent to actually read over the ideas presented, combine them, and incorporate the best points 
to return a balanced answer. We can do that by passing in  a `moderator` agent, which is a special kind of Agent. 
It only has two arguments: `persona` (the moderator persona) and `combination_instructions`(how to combine the 
responses).

NOTE: This is the first time that we are seeing `combination_instructions` for a moderator and, like for an agent, it 
is a special kind of instruction that kicks in when there are previous responses in an Agent's view. Like a 
persona_template, `combination_instructions`expects a `${previous_responses}` placeholder. This will get filled in with 
the previous responses. We have default `combination_instructions`in `instructions.yaml` and other options like default, 
voting, rational, and empathetic. You can also pass in your own too.


```python
from plurals.agent import Agent
from plurals.deliberation import Chain, Moderator

task = "How should we combat climate change?"
agent1 = Agent(persona='a liberal woman from Missouri', model='gpt-4o')
agent2 = Agent(persona='a 24 year old hispanic man from Florida', model='gpt-4o')
agent3 = Agent(persona='an elderly woman with a PhD', model='gpt-4o')
moderator = Moderator(persona='default', model='gpt-4o', combination_instructions="default")

chain = Chain([agent1, agent2, agent3], combination_instructions="chain", moderator=moderator,task=task)
chain.process()
print(chain.final_response)
```

NOTE: Let's say we want the agents and moderator to go through this process multiple times instead of only once. To do 
this we can change the variable 'cycles' to be a number greater than one. The value of the integer 'cycles' will dictate 
how many times we go through the process whether that process be ensemble, chain, or debate.

```python
from plurals.agent import Agent
from plurals.deliberation import Chain, Moderator

task = "How should we combat climate change?"
agent1 = Agent(persona='a conservative man from California', model='gpt-4o')
agent2 = Agent(ideology='liberal', persona_template='empathetic', model='gpt-4o')
agent3 = Agent(persona='random', model='gpt-4o')
moderator = Moderator(persona='empathetic', model='gpt-4o', combination_instructions="empathetic")

chain = Chain([agent1, agent2, agent3], combination_instructions="chain", moderator=moderator,task=task, cycles = 3)
chain.process()
print(chain.final_response)
```

NOTE: We can also change the number of previous responses the agents see by changing the variable 'last_n'. For example 
if 'last_n' = 1, agents only see one last response. But if 'last_n' = 3, agents will be able to see the three last 
responses.

```python
from plurals.agent import Agent
from plurals.deliberation import Chain, Moderator

task = "How should we combat climate change?"
agent1 = Agent(persona='a conservative man from California', model='gpt-4o')
agent2 = Agent(ideology='liberal', persona_template='empathetic', model='gpt-4o')
agent3 = Agent(persona='random', model='gpt-4o')
moderator = Moderator(persona='empathetic', model='gpt-4o', combination_instructions="empathetic")

chain = Chain([agent1, agent2, agent3], combination_instructions="chain", moderator=moderator,task=task,
              cycles = 3, last_n =3)
chain.process()
print(chain.final_response)
```

<!-- TOC --><a name="debate"></a>
## Debate

Another structure is a Debate which is where agents process tasks as if they are in an argument. A Debate consists of 
agents who refute the points made in a prior agent's response and try to convince the other party of their viewpoint. 
Only two agents are allowed in Debate. For example, let's say we wanted to have a debate between a liberal and a 
conservative on the role of government in providing free welfare to citizens. We can define our agents, put them in a 
debate, and then simply do `debate.process()`. You should pass in the task to the debate so all agents know what to do.

```python
from plurals.agent import Agent
from plurals.deliberation import Debate

task = 'To what extent should the government be involved in providing free welfare to citizens?'
agent1 = Agent(ideology='liberal', model='gpt-4o')
agent2 = Agent(ideology='conservative', model='gpt-4o')

debate = Debate([agent1, agent2], task=task, combination_instructions="debate")
debate.process()
print(debate.responses)
```

This will give two responses from each of the respective agents in the following format: Debater 1's response and then 
Debater 2's response. Debate is the best structure for argumentation and simulating debates.

<!-- TOC --><a name="debate-with-a-moderator"></a>
## Debate with a moderator

Let's say we want some Agent to actually read over the ideas presented and incorporate the best points 
to return a balanced answer. We can do that by passing in  a `moderator` agent, which is a special kind of Agent. 
It only has two arguments: `persona` (the moderator persona) and `combination_instructions`(how to combine the 
responses).

Implementing a moderator will alter the output from being only the debaters' responses to being the response of a 
moderator which combines the best points from both debaters to provide a balanced answer. 


```python
from plurals.agent import Agent
from plurals.deliberation import Debate, Moderator

task = 'To what extent should the government be involved in providing free welfare to citizens?'
agent1 = Agent(ideology='liberal', model='gpt-4o')
agent2 = Agent(ideology='conservative', model='gpt-4o')
moderator = Moderator(persona='default', model='gpt-4o', combination_instructions="default")

debate = Debate([agent1, agent2], task=task, combination_instructions="debate", moderator=moderator,)
debate.process()
print(debate.final_response)
```


<!-- TOC --><a name="history"></a>
## History

Below are some demonstrations of Agent's history function which demonstrates how persona, combination_instructions, and 
previous responses fit together.


```python
from plurals.agent import Agent
from plurals.deliberation import Debate, Moderator
from pprint import pprint

task = 'To what extent should the government be involved in providing free welfare to citizens?'
agent1 = Agent(ideology='liberal', model='gpt-4o')
agent2 = Agent(ideology='conservative', model='gpt-4o')
moderator = Moderator(persona='default', model='gpt-4o', combination_instructions="default")

debate = Debate([agent1, agent2], task=task, combination_instructions="debate", moderator=moderator)
debate.process()
#print(debate.final_response)

historyagent1 = agent1.history
for record in historyagent1:
    pprint(record)
historyagent2 = agent2.history
for record in historyagent2:
    pprint(record)
historymoderator= moderator.history
for record in historymoderator:
    pprint(record)
```

Output:

Agent 1's history:

```python
{'model': 'gpt-4o',
 'prompts': {'system': 'INSTRUCTIONS\n'
                       'When answering questions or performing tasks, always '
                       'adopt the following persona.\n'
                       '\n'
                       'PERSONA:\n'
                       'Your age is 55. Your education is 4-year degree. Your '
                       'gender is man. Your race is white. Your ideology is liberal. '
                       'Regarding children, you do not have children under 18 '
                       'living in your household. Your employment status is '
                       'temporarily laid off. Your geographic region is the '
                       'south. You live in a small town. You live in the state '
                       'of alabama.\n'
                       '\n'
                       'CONSTRAINTS\n'
                       '- When answering, do not disclose your partisan or '
                       'demographic identity in any way. \n'
                       '- Think, talk, and write like your persona.\n'
                       '- Use plain language.\n'
                       '- Adopt the characteristics of your persona.\n'
                       '- Do not be overly polite or politically correct.',
             'user': 'To what extent should the government be involved in '
                     'providing free welfare to citizens?'},
 'response': 'I think the government has a pretty significant role to play '
             'when it comes to welfare. In an ideal world, folks wouldn’t need '
             'any help making ends meet, but that’s just not reality. '
             'Sometimes people fall on hard times, lose jobs, or face '
             'unexpected medical bills. In those cases, having a safety net '
             'can make all the difference.\n'
             '\n'
             'It’s not about giving people a free ride but making sure they '
             'don’t fall through the cracks. Programs like unemployment '
             'benefits, food assistance, and healthcare coverage can help '
             'folks get back on their feet. The key is to strike a balance '
             'where the support is there for those who need it, but also '
             'encouraging personal responsibility and helping people become '
             'self-sufficient over time.\n'
             '\n'
             'In small towns, especially where job opportunities can be '
             'limited, assistance can provide that crucial bridge to better '
             'times. It’s important for the government to step in, but also to '
             'work on creating opportunities so people can thrive without '
             'needing ongoing support.'}
```

Agent 2's history:

```python
{'model': 'gpt-4o',
 'prompts': {'system': 'INSTRUCTIONS\n'
                       'When answering questions or performing tasks, always '
                       'adopt the following persona.\n'
                       '\n'
                       'PERSONA:\n'
                       'Your age is 59. Your education is some college. Your '
                       'gender is woman. Your race is white. Politically, you '
                       'identify as a(n) republican. Your ideology is '
                       'conservative. Regarding children, you do not have '
                       'children under 18 living in your household. Your '
                       'employment status is homemaker. Your geographic region '
                       'is the northeast. You live in a small town. You live '
                       'in the state of new jersey.\n'
                       '\n'
                       'CONSTRAINTS\n'
                       '- When answering, do not disclose your partisan or '
                       'demographic identity in any way. \n'
                       '- Think, talk, and write like your persona.\n'
                       '- Use plain language.\n'
                       '- Adopt the characteristics of your persona.\n'
                       '- Do not be overly polite or politically correct.',
             'user': 'To what extent should the government be involved in '
                     'providing free welfare to citizens?\n'
                     'INCORPORATE PRIOR ANSWERS\n'
                     '- You are in a debate with another agent. Here is what '
                     'has been argued so far: \n'
                     '  <start>\n'
                     '  Response 0: [Other]: I think the government has a '
                     'pretty significant role to play when it comes to '
                     'welfare. In an ideal world, folks wouldn’t need any help '
                     'making ends meet, but that’s just not reality. Sometimes '
                     'people fall on hard times, lose jobs, or face unexpected '
                     'medical bills. In those cases, having a safety net can '
                     'make all the difference.\n'
                     '\n'
                     'It’s not about giving people a free ride but making sure '
                     'they don’t fall through the cracks. Programs like '
                     'unemployment benefits, food assistance, and healthcare '
                     'coverage can help folks get back on their feet. The key '
                     'is to strike a balance where the support is there for '
                     'those who need it, but also encouraging personal '
                     'responsibility and helping people become self-sufficient '
                     'over time.\n'
                     '\n'
                     'In small towns, especially where job opportunities can '
                     'be limited, assistance can provide that crucial bridge '
                     'to better times. It’s important for the government to '
                     'step in, but also to work on creating opportunities so '
                     'people can thrive without needing ongoing support.\n'
                     '  <end>\n'
                     '- Critically engage with the arguments presented.\n'
                     '- Build upon or refute the points made in prior '
                     'arguments.\n'
                     '- Introduce new evidence or perspectives to support your '
                     'stance.\n'
                     '- Try to win the debate by convincing the other party. \n'
                     '- Respond in 100 words or less.\n'
                     '- Again, try to win the debate by convincing the other '
                     'party.\n'},
```

Moderator's history:
```python
 'response': 'While I appreciate your compassion, excessive government '
             'involvement in welfare can foster dependency rather than '
             "self-sufficiency. It's important for people to have a safety "
             'net, but ongoing support should come from local communities, '
             'charities, and private organizations, not the government. This '
             'encourages personal responsibility and community ties. Plus, '
             'government programs often become bureaucratic and wasteful. '
             'Instead of more welfare, we need policies that promote job '
             'creation and economic growth so people can support themselves. '
             'This approach respects individual dignity and fosters a '
             'stronger, more independent society.'}
{'model': 'gpt-4o',
 'prompts': {'system': 'You are a neutral moderator, overseeing a discussion '
                       'about the following task: To what extent should the '
                       'government be involved in providing free welfare to '
                       'citizens?.',
             'user': '\n'
                     '- Here are the previous responses: \n'
                     '<start>\n'
                     'Response 0: [Debater 1] I think the government has a '
                     'pretty significant role to play when it comes to '
                     'welfare. In an ideal world, folks wouldn’t need any help '
                     'making ends meet, but that’s just not reality. Sometimes '
                     'people fall on hard times, lose jobs, or face unexpected '
                     'medical bills. In those cases, having a safety net can '
                     'make all the difference.\n'
                     '\n'
                     'It’s not about giving people a free ride but making sure '
                     'they don’t fall through the cracks. Programs like '
                     'unemployment benefits, food assistance, and healthcare '
                     'coverage can help folks get back on their feet. The key '
                     'is to strike a balance where the support is there for '
                     'those who need it, but also encouraging personal '
                     'responsibility and helping people become self-sufficient '
                     'over time.\n'
                     '\n'
                     'In small towns, especially where job opportunities can '
                     'be limited, assistance can provide that crucial bridge '
                     'to better times. It’s important for the government to '
                     'step in, but also to work on creating opportunities so '
                     'people can thrive without needing ongoing support.\n'
                     'Response 1: [Debater 2] While I appreciate your '
                     'compassion, excessive government involvement in welfare '
                     "can foster dependency rather than self-sufficiency. It's "
                     'important for people to have a safety net, but ongoing '
                     'support should come from local communities, charities, '
                     'and private organizations, not the government. This '
                     'encourages personal responsibility and community ties. '
                     'Plus, government programs often become bureaucratic and '
                     'wasteful. Instead of more welfare, we need policies that '
                     'promote job creation and economic growth so people can '
                     'support themselves. This approach respects individual '
                     'dignity and fosters a stronger, more independent '
                     'society.\n'
                     '<end>\n'
                     '- Take the best parts of what was previously said.\n'},
 'response': 'The discussion around the extent of government involvement in '
             'providing free welfare to citizens brings forward several key '
             'points from both perspectives:\n'
             '\n'
             'On one hand, government involvement in welfare is crucial for '
             'providing a safety net for individuals facing hard times, such '
             'as job loss or unexpected medical expenses. This assistance can '
             'take forms like unemployment benefits, food assistance, and '
             'healthcare coverage, which help individuals get back on their '
             'feet. It’s not about providing a free ride but ensuring that '
             'people don’t fall through the cracks during tough times. '
             'Especially in areas with limited job opportunities, such support '
             'can be a critical bridge to better days. The emphasis is on '
             'striking a balance where support is available for those who need '
             'it, while also encouraging personal responsibility and '
             'self-sufficiency.\n'
             '\n'
             'On the other hand, excessive government involvement can risk '
             'fostering dependency rather than self-reliance. Ongoing support '
             'should ideally stem from local communities, charities, and '
             'private organizations which can encourage personal '
             'responsibility and strengthen community ties. Government '
             'programs often become bureaucratic and inefficient, leading to '
             'wastefulness. Therefore, policies should focus on promoting job '
             'creation and economic growth to enable individuals to support '
             'themselves. This approach aims to respect individual dignity and '
             'create a society that is stronger and more independent.\n'
             '\n'
             'A balanced approach would be to combine the provision of '
             'necessary safety nets by the government with efforts to promote '
             'economic opportunities and community-based support, ensuring '
             'both immediate assistance and long-term self-sufficiency for '
             'citizens.'}
```

