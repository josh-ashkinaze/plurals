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
############ Print the results ############
print(conservative_agent.system_instructions)
print("=" * 20)
printwrap(con_answer)
print("\n" * 2)
print(liberal_agent.system_instructions)
print("=" * 20)
printwrap(lib_answer)
```

```markdown
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

Let's say you don't want to use persona templates. You can pass in system instructions directly or use no system 
instructions to get back default behavior. 
```python
from plurals.agent import Agent

# Pass in system instructions directly 
pirate_agent = Agent(system_instructions="You are a pirate.", model='gpt-4o', task=task)

# No system instructions so we get back default behavior
default_agent = Agent(model='gpt-4o', task=task, kwargs={'temperature': 0.1, 'max_tokens': 100})
```


## Different ways to set up personas

### No system prompt

In this case, there will be no system prompt (i.e: default for model). Also note that you can pass in kwargs to the 
model's completion function. These are provided by LiteLLM. See (https://litellm.vercel.app/docs/completion/input)

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
formatting. Here, the user provides a `persona_template` and a `persona` (indicated by `${persona}`). Or, the user can just use our
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
print(agent.process())
```

```markdown
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

Let's look at somebody who identifies (ideologically) as very conservative and is from West Virginia. 

```python
from plurals.agent import Agent
from plurals.helpers import print_anes_mapping

print_anes_mapping()
task = "Should the United States move away from coal as an energy source? Answer Yes or No and provide a rationale."
west_virginia = Agent(query_str="inputstate=='West Virginia'&ideo5=='Very conservative'", model='gpt-4o', task=task)
west_virginia.process()
```
```
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