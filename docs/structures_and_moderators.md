
# Structures

## Types of Structures

We went over how to set up agents and now we are going to discuss how to set up structures---which are the
environments in which agents complete tasks. As of this writing, we have three structures: `ensemble`, `chain`, and 
`debate`. Each of these structures can optionally be `moderated`, meaning that at the end of deliberation, a moderator 
agent will summarize everything (e.g: make a final classification, take best ideas etc.)

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

## Ensemble with a moderator

Let's say we want some Agent to actually read over some of these ideas and maybe return one that is the best. We can do
that by passing in  a `moderator` agent, which is a special kind of Agent. It only has two arguments: `persona` (the 
moderator persona) and `combination_instructions` (how to combine the responses).

NOTE: This is the first time that we are seeing `combination_instructions` and it is a special kind of instruction that
will only kick in when there are previous responses in an Agent's view. Of course, the moderator is at the end of this
whole process so there are always going to be previous responses.

Note that like a persona_template, `combination_instructions` expects a `${previous_responses}` placeholder. This will
get filled in with the previous responses. We have default `combination_instructions` in `instructions.yaml` and other 
options like chain, debate, and voting. You can also pass in your own, too---here is an example.

```python
from plurals.agent import Agent
from plurals.deliberation import Ensemble, Moderator

task = "Brainstorm ideas to improve America."
combination_instructions = "INSTRUCTIONS\nReturn a master response that takes the best part of previous responses.\nPREVIOUS RESPONSES: ${previous_responses}\nRETURN a json like {'response': 'the best response', 'rationale':Rationale for integrating responses} and nothing else"
agents = [Agent(persona='random', model='gpt-4o') for i in range(10)]
moderator = Moderator(persona='default', model='gpt-4o')
ensemble = Ensemble(agents, moderator=moderator, task=task)
ensemble.process()
print(ensemble.responses)
```

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
kind of instruction that will only kick in when there are previous responses in an Agent's view. 

Note that like a persona_template, `combination_instructions` expects a `${previous_responses}` placeholder. This will
get filled in with the previous responses. We have default `combination_instructions` in `instructions.yaml` and other 
options like chain, debate, and voting. You can also pass in your own too. In the above example, we passed in "chain" 
instructions, so the chain option of combination_instructions will be read from the `instructions.yaml` 


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
#print(debate.final_response) # If you wanted to, you can print the final response for every structure
```


All agents have a `history` attribute which is a list of dictionaries. Each dictionary contains the exact prompts 
and responses so you can trace the deliberations. 

```python

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

```markdown
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
```

Moderator's history:
```markdown

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