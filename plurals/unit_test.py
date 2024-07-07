import unittest
from plurals.agent import Agent
from plurals.deliberation import Chain, Moderator
from plurals.helpers import load_yaml, format_previous_responses, SmartString
DEFAULTS = load_yaml("instructions.yaml")


class TestAgentChain(unittest.TestCase):

    def setUp(self):
        self.task = "How should the US handle gun control? Answer in 100 words."
        self.model = 'gpt-3.5-turbo'
        self.kwargs = {
            "temperature": 0.7,
            "max_tokens": 150,
            "top_p": 0.9
        }

    def test_agent_system_instructions(self):
        agent = Agent(task="test task", system_instructions="Here are some random system instructions.")
        self.assertIsNotNone(agent.system_instructions)
        self.assertIn("Here are some random system instructions.", agent.system_instructions)

    def test_agent_no_system_instructions(self):
        agent = Agent(task="Write a 10 word story.")
        agent.process()
        system_prompt = agent.history[0]['prompts']['system']
        self.assertIsNone(system_prompt)
        self.assertIsNone(agent.system_instructions)



    def test_agent_random_persona(self):
        agent = Agent(task="test task", persona="random")
        self.assertIsNotNone(agent.system_instructions)
        self.assertIn("age is", agent.system_instructions)

    def test_agent_query_string(self):
        agent = Agent(task="test task", query_str="inputstate=='Michigan'")
        self.assertIsNotNone(agent.system_instructions)
        self.assertIn("michigan", agent.system_instructions)

    def test_agent_manual_persona(self):
        a2 = Agent(task=self.task,
                   persona='Very conservative White Man from the deep south who strongly believe in second amendment',
                   model=self.model)
        a3 = Agent(task=self.task, persona="Liberal White women from the east coast who has far left takes",
                   model=self.model)
        a4 = Agent(task=self.task,
                   persona="Young black man from a disadvantaged neighbourhood who has had friends die to gun violence",
                   model=self.model)
        mixed = Chain([a2, a3, a4])


        # Assertions
        self.assertEqual(mixed.agents[0].persona,
                         'Very conservative White Man from the deep south who strongly believe in second amendment')
        self.assertEqual(mixed.agents[1].persona, 'Liberal White women from the east coast who has far left takes')
        self.assertEqual(mixed.agents[2].persona,
                         'Young black man from a disadvantaged neighbourhood who has had friends die to gun violence')

    def test_agent_ideology(self):
        a2 = Agent(task=self.task, ideology='moderate', model=self.model)
        a3 = Agent(task=self.task, ideology='liberal', model=self.model)
        a4 = Agent(task=self.task, ideology='conservative', model=self.model)
        mixed = Chain([a2, a3, a4])


        self.assertIn("moderate", mixed.agents[0].persona)
        self.assertIn("liberal", mixed.agents[1].persona)
        self.assertIn("conservative", mixed.agents[2].persona)

    def test_no_task_in_agent(self):
        a2 = Agent(ideology='moderate', model=self.model)
        a3 = Agent(ideology='liberal', model=self.model)
        a4 = Agent(ideology='conservative', model=self.model)
        mixed = Chain([a2, a3, a4], task_description=self.task)
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(mixed.task_description, self.task)

    def test_no_task_in_chain(self):
        a2 = Agent(task=self.task, ideology='moderate', model=self.model)
        a3 = Agent(task=self.task, ideology='liberal', model=self.model)
        a4 = Agent(task=self.task, ideology='conservative', model=self.model)
        mixed = Chain([a2, a3, a4])
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(mixed.agents[0].task_description, self.task)

    def test_task_in_chain(self):
        a2 = Agent(ideology='moderate', model=self.model)
        a3 = Agent(ideology='liberal', model=self.model)
        a4 = Agent(ideology='conservative', model=self.model)
        mixed = Chain([a2, a3, a4], task_description=self.task)
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(mixed.task_description, self.task)

    def test_moderator_default(self):
        a2 = Agent(ideology='moderate', model=self.model)
        a3 = Agent(ideology='liberal', model=self.model)
        a4 = Agent(ideology='conservative', model=self.model)
        mod = Moderator()
        mixed = Chain([a2, a3, a4], task_description=self.task, moderator=mod)
        mixed.process()
        formatted_responses = mixed.responses[:-1]

        print("Mixed", mixed.moderator.persona)

        expected_persona = SmartString(DEFAULTS['moderator']['persona']['default']).format(task=self.task)
        expected_combination_instructions = SmartString(DEFAULTS['moderator']['combination_instructions']['default']).format(previous_responses=format_previous_responses(formatted_responses))

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(expected_persona, mixed.moderator.persona)
        self.assertEqual(expected_combination_instructions, mixed.moderator.combination_instructions)


    def test_moderator_manual(self):
        a2 = Agent(ideology='moderate', model=self.model)
        a3 = Agent(ideology='liberal', model=self.model)
        a4 = Agent(ideology='conservative', model=self.model)
        mod = Moderator(
            persona="You are a conservative moderator overseeing a discussion about the following task: ${task}.",
            combination_instructions="- Here are the previous responses: ${previous_responses}- Take only the most conservative parts of what was previously said.")
        mixed = Chain([a2, a3, a4], task_description=self.task, moderator=mod)
        mixed.process()
        formatted_responses = mixed.responses[:-1]

        # Assertions

        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(mixed.moderator.persona,
                         SmartString("You are a conservative moderator overseeing a discussion about the following task: ${task}.").format(task=self.task))
        self.assertEqual(mixed.moderator.combination_instructions,
                         SmartString("- Here are the previous responses: ${previous_responses}- Take only the most conservative parts of what was previously said.").format(previous_responses=format_previous_responses(formatted_responses)))

    def test_moderator_voting(self):
        a2 = Agent(ideology='moderate', model=self.model)
        a3 = Agent(ideology='liberal', model=self.model)
        a4 = Agent(ideology='conservative', model=self.model)
        mod = Moderator(persona='voting', combination_instructions='voting')
        mixed = Chain([a2, a3, a4], task_description=self.task, moderator=mod)
        mixed.process()
        formatted_responses = mixed.responses[:-1]

        # Assertions
        self.maxDiff=None
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(SmartString(DEFAULTS['moderator']['persona']['voting']).format(task=self.task), mixed.moderator.persona)
        self.assertEqual(SmartString(DEFAULTS['moderator']['combination_instructions']['voting']).format(previous_responses=format_previous_responses(formatted_responses)),mixed.moderator.combination_instructions)

    def test_chain_chain(self):
        a2 = Agent(ideology='moderate', model=self.model)
        a3 = Agent(ideology='liberal', model=self.model)
        a4 = Agent(ideology='conservative', model=self.model)
        mixed = Chain([a2, a3, a4], task_description=self.task, combination_instructions='chain')
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(mixed.combination_instructions, DEFAULTS['combination_instructions']['chain'])

    def test_chain_debate(self):
        a2 = Agent(ideology='moderate', model=self.model)
        a3 = Agent(ideology='liberal', model=self.model)
        a4 = Agent(ideology='conservative', model=self.model)
        mixed = Chain([a2, a3, a4], task_description=self.task, combination_instructions='debate')
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(mixed.combination_instructions, DEFAULTS['combination_instructions']['debate'])

    def test_chain_voting(self):
        a2 = Agent(ideology='moderate', model=self.model)
        a3 = Agent(ideology='liberal', model=self.model)
        a4 = Agent(ideology='conservative', model=self.model)
        mixed = Chain([a2, a3, a4], task_description=self.task, combination_instructions='voting')
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(mixed.combination_instructions, DEFAULTS['combination_instructions']['voting'])

    def test_kwargs(self):
        a2 = Agent(ideology='moderate', model=self.model,**self.kwargs)
        a3 = Agent(ideology='liberal', model=self.model,**self.kwargs)
        a4 = Agent(ideology='conservative', model=self.model,**self.kwargs)
        agentlist = [a2,a3,a4]
        mixed = Chain(agentlist, task_description=self.task, combination_instructions='voting')
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        for agent in agentlist:
            self.assertIsNotNone(agent.kwargs, "Additional parameters (kwargs) should not be None")
            self.assertEqual(agent.kwargs['temperature'], 0.7)
            self.assertEqual(agent.kwargs['max_tokens'], 150)
            self.assertEqual(agent.kwargs['top_p'], 0.9)


if __name__ == '__main__':
    unittest.main()