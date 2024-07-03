#Plurchain Module
    This module was made to help promote deliberation and mitigate bias in AI responses. This is done by initiating agents with
    different personas and having them debate/respond to a task in a chain like format. The option for a moderator at the end is
    also possible.

For the rest of the documentation below we are going to assume we have already set the variables task and model as seen below:
        task = "How should the US handle gun control? Answer in 100 words."
        model = 'gpt-3.5-turbo'

#Agent Initiation
     There are multiple ways that you can initiate an Agent:
            1.You can manually set the persona:
                a1 = Agent(task_description=task,
                   persona='Very conservative White Man from the Georgia',
                   model=model)
            2.You can set a ideology where a random person with that ideology will be selected out of a dataframe:
                a1 = Agent(task_description=task, ideology='neutral', model=model)
            3.You can use a query_str:
                xxxxxxxx
            Additional Notes: 
                    It is not necessary to set task_description in agent as it can be set later on in Chain.
                    If model is not set gpt 4.0 will be used.
                    If no persona/ideology is passed to agent you will get the default response from AI.
#Moderator Initiation
    There are multiple ways that you can initiate a Moderator:
            1.You can use default moderator:
                mod = Moderator()
            2.You can manually set a persona and combination instructions for the moderator:
                mod = Moderator(persona="You are a conservative moderator overseeing a discussion about the following task: '''{task}'''.",
                                combination_instructions="- Here are the previous responses: '''{previous_responses}'''- Take only the most conservative parts of what was previously said.")
            3.You can use a voting moderator(Arrives at a definite conclusion based on responses):
                mod = Moderator(persona='voting', combination_instructions='voting')
        
#Chain Initiation
    There are multiple ways that you can initiate a Chain:
            1.You can initiate it with or without a task(if no task then agents should have task):
                mixed = Chain([a2, a3, a4], task_description=task)
                mixed = Chain([a2, a3, a4])
            2.You can have a moderator to moderate the final response:
                mixed = Chain([a2, a3, a4], task_description=task, moderator=mod)
            3.You can have set different chain functions:
                    Chain: Agents told to ensure previous perspectives will be included in their answer
                        mixed = Chain([a2, a3, a4], task_description=task, combination_instructions='chain')
                    Debate: Agents try to win debate 
                        mixed = Chain([a2, a3, a4], task_description=task, combination_instructions='debate')
                    Voting: Agents arrive at a definite conclusion
                        mixed = Chain([a2, a3, a4], task_description=task, combination_instructions='voting')
                    
        

