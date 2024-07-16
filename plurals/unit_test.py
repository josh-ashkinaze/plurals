import unittest
from plurals.agent import Agent
from plurals.deliberation import Chain, Moderator, Ensemble, Debate
from plurals.helpers import load_yaml, format_previous_responses, SmartString
from unittest.mock import MagicMock, patch

DEFAULTS = load_yaml("instructions.yaml")


class TestAgent(unittest.TestCase):

    def setUp(self):
        self.task = "How should the US handle gun control? Answer in 100 words."
        self.model = 'gpt-3.5-turbo'
        self.kwargs = {"temperature": 0.7, "max_tokens": 50, "top_p": 0.9}

    def test_agent_system_instructions(self):
        """Test whether agents can be properly initialized with system instructions"""
        agent = Agent(task="test task", system_instructions="Here are some random system instructions.",
                      kwargs=self.kwargs)
        self.assertIsNotNone(agent.system_instructions)
        self.assertIn("Here are some random system instructions.", agent.system_instructions)

    def test_agent_no_system_instructions(self):
        """Test whether agents are initialized with no system instructions"""
        agent = Agent(task="Write a 10 word story.", kwargs=self.kwargs)
        agent.process()
        system_prompt = agent.history[0]['prompts']['system']
        self.assertIsNone(system_prompt)
        self.assertIsNone(agent.system_instructions)

    def test_agent_set_task(self):
        """Test whether set_task only changes the task and not other attributes"""
        task1 = "Test Task1"
        task2 = "Test Task2"

        a = Agent(ideology='liberal', task=task1, model=self.model, kwargs=self.kwargs)

        persona1 = a.persona
        system_instructions1 = a.system_instructions
        task_original_1 = a.original_task_description
        task_current_1 = a.current_task_description

        a.set_task(task2)

        persona2 = a.persona
        system_instructions2 = a.system_instructions
        task_original_2 = a.original_task_description
        task_current_2 = a.current_task_description

        self.assertEqual(task1, task_original_1)
        self.assertEqual(task2, task_original_2)
        self.assertEqual(task1, task_current_1)
        self.assertEqual(task2, task_current_2)
        self.assertEqual(task_current_1, task1)
        self.assertEqual(task_current_2, task2)
        self.assertEqual(persona1, persona2)
        self.assertEqual(system_instructions1, system_instructions2)

    def test_agent_combo_inst_in_user_prompt(self):
        """Test if when combination instructions are set they are appropriately used in user prompt"""
        a = Agent(ideology='moderate', task="write a haiku", model=self.model,
                  combination_instructions='eccentric instructions', kwargs=self.kwargs)
        previous_responses = format_previous_responses(['response1', 'response2'])
        a.process(previous_responses=previous_responses)
        user_prompt = a.info['history'][0]['prompts']['user']
        self.assertIn("eccentric instructions", user_prompt)

    def test_agent_combo_inst_overwrite(self):
        """Test whether combination instructions are properly set for agents. If they are provided to agents and
        structures the desired behavior is that structures will overwrite agents combination instructions"""
        a2 = Agent(ideology='moderate', model=self.model, combination_instructions='initial instructions',
                   kwargs=self.kwargs)
        a3 = Agent(ideology='liberal', model=self.model, kwargs=self.kwargs)
        a4 = Agent(ideology='conservative', model=self.model, combination_instructions='initial instructions',
                   kwargs=self.kwargs)
        mixed = Chain([a2, a3, a4], task=self.task, combination_instructions='voting')

        mixed._set_combination_instructions()

        expected_instructions = SmartString(DEFAULTS['combination_instructions']['voting']).format(task=self.task)

        # Assertions
        self.assertEqual(expected_instructions, a2.combination_instructions)
        self.assertEqual(expected_instructions, a3.combination_instructions)
        self.assertEqual(expected_instructions, a4.combination_instructions)

    def test_agent_combo_instr_overwrite_warning(self):
        """Test whether a warning is raised when combination instructions are overwritten"""
        a2 = Agent(ideology='moderate', model=self.model, combination_instructions='initial instructions',
                   kwargs=self.kwargs)
        a3 = Agent(ideology='liberal', model=self.model, kwargs=self.kwargs)
        a4 = Agent(ideology='conservative', model=self.model, combination_instructions='initial instructions',
                   kwargs=self.kwargs)
        mixed = Chain([a2, a3, a4], task=self.task, combination_instructions='voting')

        with self.assertWarns(UserWarning):
            mixed._set_combination_instructions()

        expected_instructions = SmartString(DEFAULTS['combination_instructions']['voting']).format(task=self.task)

        # Assertions
        self.assertEqual(expected_instructions, a2.combination_instructions)
        self.assertEqual(expected_instructions, a3.combination_instructions)
        self.assertEqual(expected_instructions, a4.combination_instructions)

    def test_agent_process_task_with_task_arg(self):
        """
        Test whether the task parameter is passed to the process method appropriately. The desired behavior is
        that the system_instructions and persona are the same and the original_task and current_task description
        differ
        """
        task1 = "Test Task1"
        task2 = "Test Task2"

        a = Agent(ideology='conservative', task=task1)
        a.process()

        persona1 = a.persona
        system_instructions1 = a.system_instructions
        task_original_1 = a.original_task_description
        task_current_1 = a.current_task_description

        a.process(task=task2)

        persona2 = a.persona
        system_instructions2 = a.system_instructions
        task_original_2 = a.original_task_description
        task_current_2 = a.current_task_description

        self.assertEqual(task1, task_original_1)
        self.assertEqual(task2, task_original_2)
        self.assertEqual(task1, task_current_1)
        self.assertEqual(task2, task_current_2)
        self.assertEqual(persona1, persona2)
        self.assertEqual(system_instructions1, system_instructions2)
        self.assertNotEqual(task_original_1, task_original_2)
        self.assertNotEqual(task_current_1, task_current_2)

    def test_agent_random_persona(self):
        """Test if the agent is initialized with a random persona. We should always have age in persona."""
        agent = Agent(task="test task", persona="random")
        self.assertIsNotNone(agent.system_instructions)
        self.assertIn("age is", agent.system_instructions)

    def test_agent_query_string(self):
        """Searching ANES via query string and using persona"""
        agent = Agent(task="test task", query_str="inputstate=='Michigan'")
        self.assertIsNotNone(agent.system_instructions)
        self.assertIn("michigan", agent.system_instructions)

    def test_agent_age_query(self):
        """Test age parameter works correctly. This is a column we manually add to ANES from birthyr"""
        for age in [42, 52, 55]:
            agent = Agent(task="test task", query_str="age=={}".format(age))
            self.assertIsNotNone(agent.system_instructions)
            self.assertIn(str(age), agent.persona)

    def test_agent_with_nonexistent_ideology(self):
        """Test whether the agent raises an error or handles gracefully when no matching ideology is found"""
        with self.assertRaises(AssertionError):
            Agent(task=self.task, ideology='nonexistent', model=self.model, kwargs=self.kwargs)

    def test_agent_with_invalid_query_str(self):
        """Test whether the agent raises an error or handles gracefully when query_str results in no data"""
        with self.assertRaises(AssertionError):
            Agent(task=self.task, query_str="inputstate=='Atlantis'", model=self.model, kwargs=self.kwargs)

    def test_agent_manual_persona(self):
        """Test manual persona setting"""
        a2 = Agent(task=self.task,
                   persona='Very conservative White Man from the deep south who strongly believe in second amendment',
                   model=self.model)
        a3 = Agent(task=self.task, persona="Liberal White women from the east coast who has far left takes",
                   model=self.model)
        a4 = Agent(task=self.task, persona="Young man from a neighbourhood who has had friends die to gun violence",
                   model=self.model)
        mixed = Chain([a2, a3, a4])

        # Assertions
        self.assertEqual('Very conservative White Man from the deep south who strongly believe in second amendment',
                         mixed.agents[0].persona)
        self.assertEqual('Liberal White women from the east coast who has far left takes', mixed.agents[1].persona)
        self.assertEqual('Young man from a neighbourhood who has had friends die to gun violence',
                         mixed.agents[2].persona)

    def test_agent_ideology(self):
        """Test ANES persona ideology method"""
        a2 = Agent(task=self.task, ideology='moderate', model=self.model)
        a3 = Agent(task=self.task, ideology='liberal', model=self.model)
        a4 = Agent(task=self.task, ideology='conservative', model=self.model)
        mixed = Chain([a2, a3, a4])

        self.assertIn("moderate", mixed.agents[0].persona)
        self.assertIn("liberal", mixed.agents[1].persona)
        self.assertIn("conservative", mixed.agents[2].persona)

    def test_no_task_in_agent(self):
        """Test whether Structures work with no task in the agent"""
        a2 = Agent(ideology='moderate', model=self.model)
        a3 = Agent(ideology='liberal', model=self.model)
        a4 = Agent(ideology='conservative', model=self.model)
        mixed = Chain([a2, a3, a4], task=self.task)
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(self.task, mixed.task)

    def test_no_task_in_chain(self):
        """Test whether Structures work with no task in the chain"""
        a2 = Agent(task=self.task, ideology='moderate', model=self.model)
        a3 = Agent(task=self.task, ideology='liberal', model=self.model)
        a4 = Agent(task=self.task, ideology='conservative', model=self.model)
        mixed = Chain([a2, a3, a4])
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(self.task, mixed.agents[0].task_description)

    def test_task_in_chain(self):
        """Test whether Structures work with a task in the chain"""
        a2 = Agent(ideology='moderate', model=self.model)
        a3 = Agent(ideology='liberal', model=self.model)
        a4 = Agent(ideology='conservative', model=self.model)
        mixed = Chain([a2, a3, a4], task=self.task)
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(self.task, mixed.task)


class TestModerator(unittest.TestCase):

    def setUp(self):
        self.task = "How should the US handle gun control? Answer in 10 words."
        self.model = 'gpt-3.5-turbo'
        self.kwargs = {"temperature": 0.7, "max_tokens": 50, "top_p": 0.9}

    def test_init_with_persona_and_system_instructions(self):
        with self.assertRaises(ValueError):
            Moderator(persona="some_persona", system_instructions="some_instructions")

    def test_init_with_persona_only(self):
        persona = "some_persona"
        mod = Moderator(persona=persona)
        expected_persona = DEFAULTS["moderator"]['persona'].get(persona, persona)
        self.assertEqual(expected_persona, mod.persona)
        self.assertEqual("${persona}", mod.persona_template)

    def test_init_with_system_instructions_only(self):
        sys_inst = "These should be moderator's system instructions"
        mod = Moderator(system_instructions=sys_inst)
        self.assertEqual(sys_inst, mod.system_instructions)
        self.assertIsNone(mod.persona)
        self.assertIsNone(mod.persona_template)

    def test_init_with_default(self):
        default_persona = DEFAULTS["moderator"]['persona'].get('default', 'default_moderator_persona')
        mod = Moderator(model=self.model)
        self.assertEqual(default_persona, mod.persona)
        self.assertEqual("${persona}", mod.persona_template)

    @patch.object(Agent, 'process', return_value="System Instructions: Moderate the responses carefully.")
    def test_generate_system_instructions(self, mock_process):
        """Test system instructions generation when set to auto"""
        mod = Moderator(model=self.model, kwargs=self.kwargs)
        system_instructions = mod.generate_system_instructions(self.task)
        self.assertEqual("Moderate the responses carefully.", system_instructions)
        mock_process.assert_called_once()

    @patch.object(Agent, 'process', side_effect=["Invalid response"] * 10)
    def test_generate_system_instructions_max_tries_exceeded(self, mock_process):
        """Test system instructions generation raises ValueError after max tries exceeded"""
        mod = Moderator(model=self.model, kwargs=self.kwargs)

        task = "Test task exceeding max tries"

        with self.assertRaises(ValueError):
            mod.generate_system_instructions(task)
        self.assertEqual(mock_process.call_count, 10)

    @patch.object(Agent, 'process', return_value="System Instructions: Synthesize the responses effectively.")
    def test_generate_and_set_system_instructions(self, mock_process):
        """Test generate_and_set_system_instructions method"""
        mod = Moderator(model=self.model, kwargs=self.kwargs)
        mod.generate_and_set_system_instructions(self.task)
        self.assertEqual("Synthesize the responses effectively.", mod.system_instructions)
        mock_process.assert_called_once()

    @patch.object(Agent, 'process', return_value="System Instructions: Combine responses coherently.")
    def test_moderator_generate_system_instructions_in_structure(self, mock_process):
        """
        Test that the system instructions are generated properly in a structure when AutoModerated.

        The desired behavior is that the task from the Structure is passed to moderator.generate_system_instructions.
        """
        agent1 = Agent(ideology='moderate', model=self.model)
        agent2 = Agent(ideology='liberal', model=self.model)

        moderator = Moderator(system_instructions='auto', model=self.model, kwargs=self.kwargs)

        chain = Chain(agents=[agent1, agent2], task=self.task, moderator=moderator)

        self.assertEqual("Combine responses coherently.", chain.moderator.system_instructions)
        self.assertIsNone(chain.moderator.persona)
        self.assertIsNone(chain.moderator.persona_template)

    def test_moderator_kwargs(self):
        """Test setting kwargs for moderators results in valid response and are accurately passed to moderators"""
        kwargs = {"temperature": 0.7, "max_tokens": 50, "top_p": 0.9}
        mod = Moderator(persona='default', model='gpt-3.5-turbo', kwargs=self.kwargs)
        self.assertEqual(kwargs, mod.kwargs)

    def test_moderator_default(self):
        """Test whether the moderator is properly initialized with default instructions"""
        a2 = Agent(ideology='moderate', model=self.model)
        a3 = Agent(ideology='liberal', model=self.model)
        a4 = Agent(ideology='conservative', model=self.model)
        mod = Moderator()
        mixed = Chain([a2, a3, a4], task=self.task, moderator=mod)
        mixed.process()
        formatted_responses = mixed.responses[:-1]

        expected_persona = SmartString(DEFAULTS['moderator']['persona']['default']).format(task=self.task)
        expected_combination_instructions = SmartString(
            DEFAULTS['moderator']['combination_instructions']['default']).format(
            previous_responses=format_previous_responses(formatted_responses))

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(expected_persona, mixed.moderator.persona)
        self.assertEqual(expected_combination_instructions, mixed.moderator.combination_instructions)

    def test_moderator_manual(self):
        """Test manual moderator persona and combination instructions"""
        a2 = Agent(ideology='moderate', model=self.model)
        a3 = Agent(ideology='liberal', model=self.model)
        a4 = Agent(ideology='conservative', model=self.model)
        mod = Moderator(
            persona="You are a conservative moderator overseeing a discussion about the following task: ${task}.",
            combination_instructions="- Here are the previous responses: ${previous_responses}- Take only the most "
                                     "conservative parts of what was previously said.")
        mixed = Chain([a2, a3, a4], task=self.task, moderator=mod)
        mixed.process()
        formatted_responses = mixed.responses[:-1]

        expected_persona = SmartString(
            "You are a conservative moderator overseeing a discussion about the following task: ${task}.").format(
            task=self.task)
        expected_combination_instructions = SmartString(
            "- Here are the previous responses: ${previous_responses}- Take only the most "
            "conservative parts of what was previously said.").format(
            previous_responses=format_previous_responses(formatted_responses))

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(expected_persona, mixed.moderator.persona)
        self.assertEqual(expected_combination_instructions, mixed.moderator.combination_instructions)

    def test_moderator_kwargs(self):
        """Test setting kwargs for moderators results in valid response and are accurately passed to moderators"""
        mod = Moderator(persona='default', model=self.model, kwargs=self.kwargs)
        self.assertEqual(self.kwargs, mod.kwargs)

    def test_moderator_voting(self):
        """Test moderator persona and combination instructions for voting"""
        a2 = Agent(ideology='moderate', model=self.model)
        a3 = Agent(ideology='liberal', model=self.model)
        a4 = Agent(ideology='conservative', model=self.model)
        mod = Moderator(persona='voting', combination_instructions='voting')
        mixed = Ensemble([a2, a3, a4], task=self.task, moderator=mod)
        mixed.process()
        formatted_responses = mixed.responses[:-1]

        expected_persona = SmartString(DEFAULTS['moderator']['persona']['voting']).format(task=self.task)
        expected_combination_instructions = SmartString(
            DEFAULTS['moderator']['combination_instructions']['voting']).format(
            previous_responses=format_previous_responses(formatted_responses))

        # Assertions
        self.maxDiff = None
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(expected_persona, mixed.moderator.persona)
        self.assertEqual(expected_combination_instructions, mixed.moderator.combination_instructions)


class TestSmartString(unittest.TestCase):

    def test_correctly_replaces_placeholders_no_brackets(self):
        """Test that placeholders are correctly replaced when only thing in brackets is desired replacement."""
        initial_s = "Complete the following task: ${task}."
        formatted_string = SmartString(initial_s).format(task="Do the thing")
        self.assertEqual("Complete the following task: Do the thing.", formatted_string)

    def test_correctly_replaces_placeholders_with_brackets(self):
        """Test that placeholders are correctly replaced when something else uses curly brackets not meant to be
        replaced"""
        initial_s = "Complete the following task: ${task} in json format like {'answer':answer}"
        formatted_string = SmartString(initial_s).format(task="Do the thing")
        self.assertEqual("Complete the following task: Do the thing in json format like {'answer':answer}",
                         formatted_string)

    def test_avoid_double_period(self):
        """Test that double periods are correctly removed."""
        initial_s = "Complete the following task: ${task}."
        formatted_string = SmartString(initial_s).format(task="Do the thing.", avoid_double_period=True)
        self.assertEqual("Complete the following task: Do the thing.", formatted_string)

    def test_no_change_needed(self):
        """Test that the string is not distorted if no change is needed."""
        initial_s = "Complete the following task: ${task}."
        formatted_string = SmartString(initial_s).format(task="Do the thing", avoid_double_period=True)
        self.assertEqual("Complete the following task: Do the thing.", formatted_string)

    def test_only_remove_double_period(self):
        """Only remove redundant periods induced by the placeholder and not extra ones from user"""
        initial_s = "Think about this task, ${task}."
        task = "respond slowly..."
        formatted_string = SmartString(initial_s).format(task=task, avoid_double_period=True)
        self.assertEqual("Think about this task, respond slowly...", formatted_string, )


class TestChain(unittest.TestCase):

    def setUp(self):
        self.task = "How should the US handle gun control? Answer in 100 words."
        self.model = 'gpt-3.5-turbo'
        self.kwargs = {"temperature": 0.7, "max_tokens": 50, "top_p": 0.9}

    def test_chain_combination_instructions(self):
        """Test chain combination instructions"""
        a2 = Agent(ideology='moderate', model=self.model)
        a3 = Agent(ideology='liberal', model=self.model)
        a4 = Agent(ideology='conservative', model=self.model)
        mixed = Chain([a2, a3, a4], task=self.task, combination_instructions='chain')
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(DEFAULTS['combination_instructions']['chain'], mixed.combination_instructions)

    def test_chain_debate_instructions(self):
        a2 = Agent(ideology='moderate', model=self.model)
        a3 = Agent(ideology='liberal', model=self.model)
        a4 = Agent(ideology='conservative', model=self.model)
        mixed = Chain([a2, a3, a4], task=self.task, combination_instructions='debate')
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(DEFAULTS['combination_instructions']['debate'], mixed.combination_instructions)

    def test_chain_voting_instructions(self):
        """Test chain voting instructions"""
        a2 = Agent(ideology='moderate', model=self.model)
        a3 = Agent(ideology='liberal', model=self.model)
        a4 = Agent(ideology='conservative', model=self.model)
        mixed = Chain([a2, a3, a4], task=self.task, combination_instructions='voting')
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(DEFAULTS['combination_instructions']['voting'], mixed.combination_instructions)


class TestEnsemble(unittest.TestCase):

    def setUp(self):
        self.task = "How should the US handle gun control? Answer in 100 words."
        self.model = 'gpt-3.5-turbo'
        self.kwargs = {"temperature": 0.7, "max_tokens": 50, "top_p": 0.9}

    def test_moderator_voting(self):
        """Test moderator persona and combination instructions for voting"""
        a2 = Agent(ideology='moderate', model=self.model)
        a3 = Agent(ideology='liberal', model=self.model)
        a4 = Agent(ideology='conservative', model=self.model)
        mod = Moderator(persona='voting', combination_instructions='voting')
        mixed = Ensemble([a2, a3, a4], task=self.task, moderator=mod)
        mixed.process()
        formatted_responses = mixed.responses[:-1]

        # Assertions
        self.maxDiff = None
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(SmartString(DEFAULTS['moderator']['persona']['voting']).format(task=self.task),
                         mixed.moderator.persona)
        self.assertEqual(SmartString(DEFAULTS['moderator']['combination_instructions']['voting']).format(
            previous_responses=format_previous_responses(formatted_responses)),
            mixed.moderator.combination_instructions)


class TestDebate(unittest.TestCase):

    def setUp(self):
        self.task = "How should the US handle gun control? Answer in 100 words."
        self.model = 'gpt-3.5-turbo'
        self.kwargs = {"temperature": 0.7, "max_tokens": 50, "top_p": 0.9}

    def test_debate_formatting(self):
        agents = [Agent(persona="You are a mac fanatic trying to convince a user to switch to Mac.", model=self.model,
                        kwargs=self.kwargs), Agent(persona="A PC fanatic", model=self.model, kwargs=self.kwargs)]

        debate_structure = Debate(agents=agents, task="Which computer is better? Mac or PC? Answer in 10 words.",
                                  moderator=Moderator(), cycles=3)

        debate_structure.process()

        # Make sure final responses are formatted correctly
        self.assertTrue(debate_structure.responses[0].startswith("[Debater 1]"))
        self.assertTrue(debate_structure.responses[1].startswith("[Debater 2]"))
        self.assertTrue(debate_structure.responses[2].startswith("[Debater 1]"))

        # Check that for Debater 2 on the first turn it is the case that Debater 1's answer is in the user prompt
        # and prefixed by "[Other]:"
        user_prompt = agents[1].info['history'][0]['prompts']['user']
        self.assertIn("[Other]:", user_prompt)
        prev_response = user_prompt.split("[Other]:")[1].split("<end>")[0].strip()
        debater_1_initial_response = agents[0].info['history'][0]['response'].strip()
        self.assertEqual(debater_1_initial_response, prev_response)

        # Check that for Debater 1 on the second term it is the case that...
        # Check 1: There is only a [You] and [Other] placeholder
        user_prompt = agents[0].info['history'][1]['prompts']['user']
        you_counts = user_prompt.count("[You]:")
        other_counts = user_prompt.count("[Other]:")
        self.assertEqual(1, you_counts)
        self.assertEqual(1, other_counts)

        # Check 2: Debater 1's previous response is in the user prompt and
        # prefixed by [You]
        debater_1_initial_response = agents[0].info['history'][0]['response'].strip()
        debater_2_initial_response = agents[1].info['history'][0]['response'].strip()
        self.assertIn("[You]: " + debater_1_initial_response, user_prompt)
        self.assertIn("[Other]: " + debater_2_initial_response, user_prompt)

        correct_strings = [
            "Response 0: [Debater 1]",
            "Response 1: [Debater 2]",
            "Response 2: [Debater 1]",
            "Response 3: [Debater 2]",
        ]

        # Incorrectly formatted response strings that should not appear in the moderator's task description
        incorrect_strings = [
            "Response 0: [Debater 2]",
            "Response 1: [Debater 1]",
            "Response 2: [Debater 2]",
            "Response 3: Debater [1]"
        ]

        # Check for correct strings in the current task description
        for correct_string in correct_strings:
            self.assertIn(correct_string, debate_structure.moderator.info['current_task_description'],
                          f"{correct_string} should be in the moderator's current task description.")

        # Check for incorrect strings not in the current task description
        for incorrect_string in incorrect_strings:
            self.assertNotIn(incorrect_string, debate_structure.moderator.info['current_task_description'],
                             f"{incorrect_string} should not be in the moderator's current task description.")


class TestAgentStructures(unittest.TestCase):

    def setUp(self):
        self.task = "How should the US handle gun control? Answer in 100 words."
        self.model = 'gpt-3.5-turbo'
        self.kwargs = {"temperature": 0.7, "max_tokens": 50, "top_p": 0.9}

    def test_info_method(self):
        agents = [Agent(task="First task", model=self.model, kwargs=self.kwargs),
                  Agent(task="Second task", model=self.model, kwargs=self.kwargs)]

        moderator = Moderator(persona="default", model=self.model)

        structure = Chain(agents=agents, task="General task for agents", moderator=moderator)

        # using mocking with this method
        structure.process = MagicMock(return_value=None)
        structure.final_response = "Aggregated final response from mock"
        structure.responses = ["Response from First task", "Response from Second task"]

        info = structure.info

        # validate the dictionary structure and types
        self.assertIsInstance(info, dict)
        self.assertIn('structure_information', info)
        self.assertIn('agent_information', info)

        # validate structure_information
        self.assertEqual("General task for agents", info['structure_information']['task'])
        self.assertIn('final_response', info['structure_information'])
        self.assertTrue(isinstance(info['structure_information']['responses'], list))
        self.assertEqual("Aggregated final response from mock", info['structure_information']['final_response'])
        self.assertIn("Response from First task", info['structure_information']['responses'])
        self.assertIn("Response from Second task", info['structure_information']['responses'])

        # validate agent_information
        self.assertTrue(isinstance(info['agent_information'], list))
        self.assertEqual(2, len(info['agent_information']))
        for agent_info in info['agent_information']:
            self.assertIn('current_task_description', agent_info)
            self.assertIn(agent_info['current_task_description'], ["First task", "Second task"])


if __name__ == '__main__':
    unittest.main()
