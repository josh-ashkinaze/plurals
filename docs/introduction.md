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


# Plurals System

Plurals consists of three core abstractions (Figure 1):

1. **Agents:**
    - Users can initialize system instructions as null to get back model behavior.
    - Users can pass in direct system instructions.
    - Users can combine personas with persona templates, giving more instructions to the model on how to enact the persona.
    - We have various pre-populated templates.
    - We support creating personas from American National Election Studies (ANES, 2024):
        - Our system finds a real individual satisfying some criteria (e.g: A Michigan resident) and then creates a persona based on the totality of this individual's attributes.
        - The marginal distribution of Plurals-generated personas matches that of the general population.
        - Sampling is probability-weighted, so the probability of a citizen being simulated matches their national sample probability weight.
        - We also support a `random` argument where users can quickly draw up random personas.

2. **Structures:** Structures are the environments in which agents work together. Broadly, structures are defined by:
    - **Information-sharing:**
        - Direction of information sharing (i.e: is it directed or undirected).
        - Amount of information-sharing.
        - Example: In an `Ensemble`, no information is shared and Agents process requests in parallel whereas in a `Chain`, agents each build upon each other's answers.
        - Users can create in-between structures. Our system supports a `$last_n$` parameter that dictates how much information an agent sees from the current deliberation stack. Setting `$last_n$` to 1 would result in a Markov-esque chain.
        - Users can also control `$cycles$` of a structure, which is how many times the sequence is run and whether to `$shuffle$` the ordering of agents on each cycle.
    - **Combination instructions:** 
        - How agents are instructed to combine information in the structure.
        - Interactions can be adversarial or amicable.
        - We offer a list of templates which can be used via keywords.
        - Templates are inspired by research on derivative democracy, spanning first-wave deliberation (valuing reason-giving) and second-wave deliberation (valuing perspectives).

3. **Moderators:** We support Moderators, who are special classes of Agents that oversee deliberation. Moderators are defined by their personas and combination instructions (how to combine information). As with combination instructions and persona templates, we support various pre-defined moderator instructions such as `information aggregators` or `synthesizers`.


# Quick start 

## Using ANES to create a conservative persona-based agent

Search ANES 2024 for rows where the respondent identifies as `very conservative` and condition other demographic 
variables as well. Use the default persona template from instructions.yaml.  


```python
from plurals.agent import Agent
import os
os.environ["OPENAI_API_KEY'] = 'yourkey'
os.environ["ANTHROPIC_API_KEY'] = 'yourkey'
task = "Should the United States ban assault rifles? Answer in 50 words."
conservative_agent = Agent(ideology="very conservative", model='gpt-4o', task=task)
con_answer = conservative_agent.process()  # call agent.process() to get the response. 
```

```python
print(conservative_agent.persona)
print(conservative_agent.system_instructions)
```

Here is the persona. 
```markdown
Your age is 57. Your education is high school graduate. Your gender is man. Your race is hispanic. Politically, you identify as a(n) republican. Your ideology is very conservative. Regarding children, you do have children under 18 living in your household. Your employment status is full-time. Your geographic region is the northeast. You live in a suburban area. You live in the state of new york.
```

Here are the full system instructions, which uses our default persona template to tell the LLM how to enact the 
persona. 

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
```

And the final answer:
```markdown
Banning assault rifles won't solve the problem. It's about enforcing existing
laws and focusing on mental health. Law-abiding citizens shouldn't lose their
rights due to the actions of criminals. Solutions should target the root causes
of violence, not just the tools.

```

We can get all the info for an agent by simply printing `print(conservative_agent.info)`. 



## Using different persona templates 
Persona templates instruct the model how to enact a persona. Let's say we wanted to use the `empathetic` persona. 

```python
from plurals.agent import Agent

# Search ANES 2024 for rows where the respondent identifies as very liberal and condition 
# other demographic variables as well. Use the `empathetic` persona template from instructions.yaml which 
# encourages storytelling above reason-giving. 
liberal_agent = Agent(ideology="very liberal", persona_template='empathetic', model='gpt-4o', task=task)
liberal_agent.process() # will print response
lib_answer = liberal_agent.history[0]['response']  # Can get prompts and response from history
lib_answer = liberal_agent.info['history'][0]['response']  # Can get history and more from info 
```

```python
print(liberal_agent.system_instructions)
```

```markdown
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
```


## An ensemble of nationally-representative personas brainstorming ways to reduce affective polarization

As discussed in the `Agent` section, we can create random personas by sampling from ANES 2024 using appropriate 
probability weights. As discussed in the `Structures` section, an `Ensemble` will process requests in parallel and 
then a `Moderator` will oversee the deliberation response. 

```python
from plurals.deliberation import Ensemble, Moderator
from plurals.agent import Agent
import random

task = "Based on your experiences, what are some under-explored ways to reduce affective polarization?"
agents = [
    Agent(persona='random', model=random.choice(['gpt-4o']))
    for _ in range(10)
]
mod = Moderator(persona='default', combination_instructions="Pick the best of the proposals: ${previous_responses}")

ensemble = Ensemble(agents=agents, moderator=mod,task=task
)
ensemble.process()

print(ensemble.final_response) # final response
print(ensemble.responses) # all responses
print(ensemble.info) # all info about the ensemble and the agents
```

## A highly specific chain of LLMs deliberating on AGI
Have Claude, ChatGPT, and GPT-4 build on each other’s output for 10 iterations, using custom combination instructions with each Agent seeing the last 3 responses from deliberation so far, with the sequence of agent deliberation changing each cycle.  

```python
from plurals.deliberation import Chain
from plurals.agent import Agent

chain = Chain(
    agents=[
        Agent(model="claude-2.1"),
        Agent(model="gpt-4-turbo"),
        Agent(model="gpt-3.5-turbo")
    ],
    cycles=10,
    last_n=3,
    shuffle=True,
    combination_instructions="Build on ${previous_responses} for a more nuanced position.",
    task="Even if artificial general intelligence was possible, would it positively benefit humans?",
)
chain.process()

```

