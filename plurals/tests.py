import unittest
from unittest.mock import MagicMock, patch, Mock

from plurals.agent import Agent
from plurals.deliberation import (
    Chain,
    Moderator,
    Ensemble,
    Debate,
    Graph,
    AbstractStructure,
)
from plurals.helpers import (
    load_yaml,
    format_previous_responses,
    SmartString,
    strip_nested_dict,
)
import json

DEFAULTS = load_yaml("instructions.yaml")
DEFAULTS = strip_nested_dict(DEFAULTS)


#############################################
# CORE BEHAVIOR
#############################################
class TestStructure(AbstractStructure):
    def process(self):
        pass  # Implement the abstract method


class TestAgent(unittest.TestCase):
    anes_template = DEFAULTS["persona_template"].get("anes").strip()
    default_template = DEFAULTS["persona_template"].get("default").strip()

    def setUp(self):
        self.task = "How should the US handle gun control? Answer in 100 words."
        self.model = "gpt-3.5-turbo"
        self.kwargs = {"temperature": 0.7, "max_tokens": 50, "top_p": 0.9}

    def test_agent_system_instructions(self):
        """Test whether agents can be properly initialized with system instructions"""
        agent = Agent(
            task="test task",
            system_instructions="Here are some random system instructions.",
            kwargs=self.kwargs,
        )
        self.assertIsNotNone(agent.system_instructions)
        self.assertIn(
            "Here are some random system instructions.", agent.system_instructions
        )

    def test_agent_no_system_instructions(self):
        """Test whether agents are initialized with no system instructions"""
        agent = Agent(task="Write a 10 word story.", kwargs=self.kwargs)
        agent.process()
        system_prompt = agent.history[0]["prompts"]["system"]
        self.assertIsNone(system_prompt)
        self.assertIsNone(agent.system_instructions)

    def test_agent_set_task(self):
        """Test whether set_task only changes the task and not other attributes"""
        task1 = "Test Task1"
        task2 = "Test Task2"

        a = Agent(ideology="liberal", task=task1, model=self.model, kwargs=self.kwargs)

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
        a = Agent(
            ideology="moderate",
            task="write a haiku",
            model=self.model,
            combination_instructions="eccentric instructions",
            kwargs=self.kwargs,
        )
        previous_responses = format_previous_responses(["response1", "response2"])
        a.process(previous_responses=previous_responses)
        user_prompt = a.info["history"][0]["prompts"]["user"]
        self.assertIn("eccentric instructions", user_prompt)

    def test_agent_combo_inst_overwrite(self):
        """Test whether combination instructions are properly set for agents. If they are provided to agents and
        structures the desired behavior is that agents will overwrite structure combination instructions
        """
        a2 = Agent(
            ideology="moderate",
            model=self.model,
            combination_instructions="agent 2 instructions",
            kwargs=self.kwargs,
        )
        a3 = Agent(
            ideology="liberal",
            model=self.model,
            kwargs=self.kwargs,
            combination_instructions="agent 3 instructions",
        )
        a4 = Agent(
            ideology="conservative",
            model=self.model,
            combination_instructions="agent 4 instructions",
            kwargs=self.kwargs,
        )
        mixed = Chain([a2, a3, a4], task=self.task, combination_instructions="voting")

        mixed._set_combination_instructions()

        # Assertions
        self.assertEqual("agent 2 instructions", a2.combination_instructions)
        self.assertEqual("agent 3 instructions", a3.combination_instructions)
        self.assertEqual("agent 4 instructions", a4.combination_instructions)

    def test_agent_process_task_with_task_arg(self):
        """
        Test whether the task parameter is passed to the process method appropriately. The desired behavior is
        that the system_instructions and persona are the same and the original_task and current_task description
        differ
        """
        task1 = "Test Task1"
        task2 = "Test Task2"

        a = Agent(ideology="conservative", task=task1)
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
        persona_template = agent.persona_template
        self.assertEqual(self.anes_template, persona_template)
        self.assertIsNotNone(agent.system_instructions)
        self.assertIn("age is", agent.system_instructions)

    def test_agent_query_string(self):
        """Searching ANES via query string and using persona"""
        agent = Agent(task="test task", query_str="inputstate=='Michigan'")
        persona_template = agent.persona_template
        self.assertEqual(self.anes_template, persona_template)
        self.assertIsNotNone(agent.system_instructions)
        self.assertIn("michigan", agent.system_instructions)

    def test_agent_age_query(self):
        """Test age parameter works correctly. This is a column we manually add to ANES from birthyr"""
        for age in [42, 52, 55]:
            agent = Agent(task="test task", query_str="age=={}".format(age))
            persona_template = agent.persona_template
            self.assertEqual(self.anes_template, persona_template)
            self.assertIsNotNone(agent.system_instructions)
            self.assertIn(str(age), agent.persona)

    def test_agent_with_nonexistent_ideology(self):
        """Test whether the agent raises an error or handles gracefully when no matching ideology is found"""
        with self.assertRaises(AssertionError):
            Agent(
                task=self.task,
                ideology="nonexistent",
                model=self.model,
                kwargs=self.kwargs,
            )

    def test_agent_with_invalid_query_str(self):
        """Test whether the agent raises an error or handles gracefully when query_str results in no data"""
        with self.assertRaises(AssertionError):
            Agent(
                task=self.task,
                query_str="inputstate=='Atlantis'",
                model=self.model,
                kwargs=self.kwargs,
            )

    def test_agent_manual_persona(self):
        """Test manual persona setting"""
        a2 = Agent(
            task=self.task,
            persona="Very conservative White Man from the deep south who strongly believe in second amendment",
            model=self.model,
        )
        a3 = Agent(
            task=self.task,
            persona="Liberal White women from the east coast who has far left takes",
            model=self.model,
        )
        a4 = Agent(
            task=self.task,
            persona="Young man from a neighbourhood who has had friends die to gun violence",
            model=self.model,
        )
        mixed = Chain([a2, a3, a4])

        # Assertions for personas
        self.assertEqual(
            "Very conservative White Man from the deep south who strongly believe in second amendment",
            mixed.agents[0].persona,
        )
        self.assertEqual(
            "Liberal White women from the east coast who has far left takes",
            mixed.agents[1].persona,
        )
        self.assertEqual(
            "Young man from a neighbourhood who has had friends die to gun violence",
            mixed.agents[2].persona,
        )

        # Assertions for persona templates
        self.assertEqual(self.default_template, mixed.agents[0].persona_template)
        self.assertEqual(self.default_template, mixed.agents[1].persona_template)
        self.assertEqual(self.default_template, mixed.agents[2].persona_template)

    def test_agent_ideology(self):
        """Test ANES persona ideology method"""
        a2 = Agent(task=self.task, ideology="moderate", model=self.model)
        a3 = Agent(task=self.task, ideology="liberal", model=self.model)
        a4 = Agent(task=self.task, ideology="conservative", model=self.model)
        mixed = Chain([a2, a3, a4])

        # Persona assertions
        self.assertIn("moderate", mixed.agents[0].persona)
        self.assertIn("liberal", mixed.agents[1].persona)
        self.assertIn("conservative", mixed.agents[2].persona)

        # Persona template assertions
        self.assertEqual(self.anes_template, mixed.agents[0].persona_template)
        self.assertEqual(self.anes_template, mixed.agents[1].persona_template)
        self.assertEqual(self.anes_template, mixed.agents[2].persona_template)

    def test_no_task_in_agent(self):
        """Test whether Structures work with no task in the agent"""
        a2 = Agent(ideology="moderate", model=self.model)
        a3 = Agent(ideology="liberal", model=self.model)
        a4 = Agent(ideology="conservative", model=self.model)
        mixed = Chain([a2, a3, a4], task=self.task)
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(self.task, mixed.task)

    def test_no_task_in_chain(self):
        """Test whether Structures work with no task in the chain"""
        a2 = Agent(task=self.task, ideology="moderate", model=self.model)
        a3 = Agent(task=self.task, ideology="liberal", model=self.model)
        a4 = Agent(task=self.task, ideology="conservative", model=self.model)
        mixed = Chain([a2, a3, a4])
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(self.task, mixed.agents[0].task_description)

    def test_task_in_chain(self):
        """Test whether Structures work with a task in the chain"""
        a2 = Agent(ideology="moderate", model=self.model)
        a3 = Agent(ideology="liberal", model=self.model)
        a4 = Agent(ideology="conservative", model=self.model)
        mixed = Chain([a2, a3, a4], task=self.task)
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(self.task, mixed.task)


class TestModerator(unittest.TestCase):

    def setUp(self):
        self.task = "How should the US handle gun control? Answer in 10 words."
        self.model = "gpt-3.5-turbo"
        self.kwargs = {"temperature": 0.7, "max_tokens": 50, "top_p": 0.9}

    def test_init_with_persona_and_system_instructions(self):
        with self.assertRaises(ValueError):
            Moderator(persona="some_persona", system_instructions="some_instructions")

    def test_init_with_persona_only(self):
        persona = "some_persona"
        mod = Moderator(persona=persona)
        expected_persona = DEFAULTS["moderator"]["persona"].get(persona, persona)
        self.assertEqual(expected_persona, mod.persona)
        self.assertEqual("${persona}", mod.persona_template)

    def test_init_with_system_instructions_only(self):
        sys_inst = "These should be moderator's system instructions"
        mod = Moderator(system_instructions=sys_inst)
        self.assertEqual(sys_inst, mod.system_instructions)
        self.assertIsNone(mod.info["persona"])
        self.assertIsNone(mod.info["persona_template"])

    def test_init_with_default(self):
        default_persona = DEFAULTS["moderator"]["persona"].get(
            "default", "default_moderator_persona"
        )
        mod = Moderator(model=self.model, persona="default")
        self.assertEqual(default_persona, mod.persona)
        self.assertEqual("${persona}", mod.persona_template)

    @patch.object(
        Agent,
        "process",
        return_value="System Instructions: Moderate the responses carefully.",
    )
    def test_generate_system_instructions(self, mock_process):
        """Test system instructions generation when set to auto"""
        mod = Moderator(model=self.model, kwargs=self.kwargs)
        system_instructions = mod.generate_system_instructions(self.task)
        self.assertEqual("Moderate the responses carefully.", system_instructions)
        mock_process.assert_called_once()

    @patch.object(Agent, "process", side_effect=["Invalid response"] * 10)
    def test_generate_system_instructions_max_tries_exceeded(self, mock_process):
        """Test system instructions generation raises ValueError after max tries exceeded"""
        mod = Moderator(model=self.model, kwargs=self.kwargs)

        task = "Test task exceeding max tries"

        with self.assertRaises(ValueError):
            mod.generate_system_instructions(task)
        self.assertEqual(mock_process.call_count, 10)

    @patch.object(
        Agent,
        "process",
        return_value="System Instructions: Synthesize the responses effectively.",
    )
    def test_generate_and_set_system_instructions(self, mock_process):
        """Test generate_and_set_system_instructions method"""
        mod = Moderator(model=self.model, kwargs=self.kwargs)
        mod.generate_and_set_system_instructions(self.task)
        self.assertEqual(
            "Synthesize the responses effectively.", mod.system_instructions
        )
        mock_process.assert_called_once()

    @patch.object(
        Agent,
        "process",
        return_value="System Instructions: Combine responses coherently.",
    )
    def test_moderator_generate_system_instructions_in_structure(self, mock_process):
        """
        Test that the system instructions are generated properly in a structure when AutoModerated.

        The desired behavior is that the task from the Structure is passed to moderator.generate_system_instructions.
        """
        agent1 = Agent(ideology="moderate", model=self.model)
        agent2 = Agent(ideology="liberal", model=self.model)

        moderator = Moderator(
            system_instructions="auto", model=self.model, kwargs=self.kwargs
        )

        chain = Chain(agents=[agent1, agent2], task=self.task, moderator=moderator)

        self.assertEqual(
            "Combine responses coherently.", chain.moderator.system_instructions
        )
        self.assertIsNone(chain.moderator.info["persona"])
        self.assertIsNone(chain.moderator.info["persona_template"])

    def test_moderator_kwargs(self):
        """Test setting kwargs for moderators results in valid response and are accurately passed to moderators"""
        kwargs = {"temperature": 0.7, "max_tokens": 50, "top_p": 0.9}
        mod = Moderator(persona="default", model="gpt-3.5-turbo", kwargs=self.kwargs)
        self.assertEqual(kwargs, mod.kwargs)

    def test_moderator_default(self):
        """Test whether the moderator is properly initialized with default instructions"""
        a2 = Agent(ideology="moderate", model=self.model)
        a3 = Agent(ideology="liberal", model=self.model)
        a4 = Agent(ideology="conservative", model=self.model)
        mod = Moderator(persona="default")
        mixed = Chain([a2, a3, a4], task=self.task, moderator=mod)
        mixed.process()
        formatted_responses = mixed.responses[:-1]

        expected_persona = SmartString(
            DEFAULTS["moderator"]["persona"]["default"]
        ).format(task=self.task)
        expected_combination_instructions = SmartString(
            DEFAULTS["moderator"]["combination_instructions"]["default"]
        ).format(previous_responses=format_previous_responses(formatted_responses))

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(expected_persona, mixed.moderator.persona)
        self.assertEqual(
            expected_combination_instructions, mixed.moderator.combination_instructions
        )

    def test_moderator_no_instructions(self):
        """Test whether the moderator is properly initialized with default instructions"""
        a2 = Agent(ideology="moderate", model=self.model)
        a3 = Agent(ideology="liberal", model=self.model)
        a4 = Agent(ideology="conservative", model=self.model)
        mod = Moderator()
        mixed = Chain([a2, a3, a4], task=self.task, moderator=mod)
        mixed.process()
        formatted_responses = mixed.responses[:-1]

        expected_combination_instructions = SmartString(
            DEFAULTS["moderator"]["combination_instructions"]["default"]
        ).format(previous_responses=format_previous_responses(formatted_responses))

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(None, mixed.moderator.persona)
        self.assertEqual(
            expected_combination_instructions, mixed.moderator.combination_instructions
        )
        self.assertEqual(None, mixed.moderator.system_instructions)

    def test_moderator_manual(self):
        """Test manual moderator persona and combination instructions"""
        a2 = Agent(ideology="moderate", model=self.model)
        a3 = Agent(ideology="liberal", model=self.model)
        a4 = Agent(ideology="conservative", model=self.model)
        mod = Moderator(
            persona="You are a conservative moderator overseeing a discussion about the following task: ${task}.",
            combination_instructions="- Here are the previous responses: ${previous_responses}- Take only the most "
                                     "conservative parts of what was previously said.",
        )
        mixed = Chain([a2, a3, a4], task=self.task, moderator=mod)
        mixed.process()
        formatted_responses = mixed.responses[:-1]

        expected_persona = SmartString(
            "You are a conservative moderator overseeing a discussion about the following task: ${task}."
        ).format(task=self.task)
        expected_combination_instructions = SmartString(
            "- Here are the previous responses: ${previous_responses}- Take only the most "
            "conservative parts of what was previously said."
        ).format(previous_responses=format_previous_responses(formatted_responses))

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(expected_persona, mixed.moderator.persona)
        self.assertEqual(
            expected_combination_instructions, mixed.moderator.combination_instructions
        )

    def test_moderator_kwargs(self):
        """Test setting kwargs for moderators results in valid response and are accurately passed to moderators"""
        mod = Moderator(persona="default", model=self.model, kwargs=self.kwargs)
        self.assertEqual(self.kwargs, mod.kwargs)

    def test_moderator_voting(self):
        """Test moderator persona and combination instructions for voting"""
        a2 = Agent(ideology="moderate", model=self.model)
        a3 = Agent(ideology="liberal", model=self.model)
        a4 = Agent(ideology="conservative", model=self.model)
        mod = Moderator(persona="voting", combination_instructions="voting")
        mixed = Ensemble([a2, a3, a4], task=self.task, moderator=mod)
        mixed.process()
        formatted_responses = mixed.responses[:-1]

        expected_persona = SmartString(
            DEFAULTS["moderator"]["persona"]["voting"]
        ).format(task=self.task)
        expected_combination_instructions = SmartString(
            DEFAULTS["moderator"]["combination_instructions"]["voting"]
        ).format(previous_responses=format_previous_responses(formatted_responses))

        # Assertions
        self.maxDiff = None
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(expected_persona, mixed.moderator.persona)
        self.assertEqual(
            expected_combination_instructions, mixed.moderator.combination_instructions
        )


class TestChain(unittest.TestCase):

    def setUp(self):
        self.task = "How should the US handle gun control? Answer in 100 words."
        self.model = "gpt-3.5-turbo"
        self.kwargs = {"temperature": 0.7, "max_tokens": 50, "top_p": 0.9}

    def test_chain_multiple_cycles(self):
        task = "Discuss the pros and cons of remote work."
        agent1 = Agent(ideology="liberal", model="gpt-3.5-turbo")
        agent2 = Agent(ideology="conservative", model="gpt-3.5-turbo")

        chain = Chain([agent1, agent2], task=task, cycles=3)

        with patch.object(
                Agent,
                "_get_response",
                side_effect=[
                    "Pros: flexibility, no commute. Cons: isolation.",
                    "Pros: reduced office costs. Cons: difficulty in team building.",
                    "Agree on flexibility, add increased productivity as pro.",
                    "Agree on team building issues, add potential for overwork.",
                    "Emphasize need for balance and hybrid models.",
                    "Suggest importance of clear communication and expectations.",
                ],
        ):
            chain.process()

        self.assertEqual(len(chain.responses), 6)
        self.assertEqual(
            chain.final_response,
            "Suggest importance of clear communication and expectations.",
        )

    def test_chain_combination_instructions(self):
        """Test chain combination instructions"""
        a2 = Agent(ideology="moderate", model=self.model)
        a3 = Agent(ideology="liberal", model=self.model)
        a4 = Agent(ideology="conservative", model=self.model)
        mixed = Chain([a2, a3, a4], task=self.task, combination_instructions="chain")
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(
            DEFAULTS["combination_instructions"]["chain"],
            mixed.combination_instructions,
        )

    def test_chain_with_different_combination_instructions(self):
        task = "Say hello"
        agent1 = Agent(
            task=task,
            combination_instructions="Hello to previous ${previous_responses}",
            model="gpt-3.5-turbo",
        )
        agent2 = Agent(
            task=task,
            combination_instructions="Prev2 to previous ${previous_responses}",
            model="gpt-4",
        )
        agent3 = Agent(
            task=task,
            combination_instructions="Greetings to previous ${previous_responses}",
            model="gpt-3.5-turbo",
        )

        chain = Chain([agent1, agent2, agent3], task=task)
        chain.process()

        self.assertEqual(
            agent1.combination_instructions, "Hello to previous ${previous_responses}"
        )
        self.assertEqual(
            agent2.combination_instructions, "Prev2 to previous ${previous_responses}"
        )
        self.assertEqual(
            agent3.combination_instructions,
            "Greetings to previous ${previous_responses}",
        )

        self.assertEqual(len(chain.responses), 3)

        self.assertIn("Prev2 to previous", agent2.prompts[0]["user"])
        self.assertIn("Greetings to previous", agent3.prompts[0]["user"])

    def test_set_all_individual_agent_combination_instructions(self):
        """Set custom combo insts for all agents"""

        task = "Generate argument for or against social media in 10 words."
        agent1 = Agent(
            task=task,
            combination_instructions="Build on previous ideas: ${previous_responses}",
            model="gpt-3.5-turbo",
            kwargs={"max_tokens": 30},
        )
        agent2 = Agent(
            task=task,
            combination_instructions="Critique previous points: ${previous_responses}",
            model="gpt-3.5-turbo",
            kwargs={"max_tokens": 30},
        )
        agent3 = Agent(
            task=task,
            combination_instructions="Synthesize all points: ${previous_responses}",
            model="gpt-3.5-turbo",
            kwargs={"max_tokens": 30},
        )

        chain = Chain([agent1, agent2, agent3], task=task)
        chain.process()

        self.assertEqual(
            "Build on previous ideas: ${previous_responses}",
            agent1.combination_instructions,
        )
        self.assertEqual(
            "Critique previous points: ${previous_responses}",
            agent2.combination_instructions,
        )
        self.assertEqual(
            "Synthesize all points: ${previous_responses}",
            agent3.combination_instructions,
        )

        self.assertEqual(3, len(chain.responses))

        self.assertIn("Critique previous points:", agent2.prompts[0]["user"])
        self.assertIn("Synthesize all points:", agent3.prompts[0]["user"])

    def test_set_some_individual_agent_combination_instructions(self):
        """When combo insts set for some Agents, we use the set instructions for the relevant Agents and structure combo instructions for other Agents"""
        task = "Generate argument for or against social media in 10 words."
        agent1 = Agent(
            task=task,
            combination_instructions="Expand on previous responses: ${previous_responses}",
            model="gpt-3.5-turbo",
            kwargs={"max_tokens": 30},
        )
        agent2 = Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})
        agent3 = Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})

        chain = Chain(
            [agent1, agent2, agent3], task=task, combination_instructions="jury"
        )
        chain.process()

        self.assertEqual(
            "Expand on previous responses: ${previous_responses}",
            agent1.combination_instructions,
        )
        self.assertEqual(
            DEFAULTS["combination_instructions"]["jury"],
            agent2.combination_instructions,
        )
        self.assertEqual(
            DEFAULTS["combination_instructions"]["jury"],
            agent3.combination_instructions,
        )

        self.assertEqual(3, len(chain.responses))

        self.assertIn("Reexamine your views", agent2.prompts[0]["user"])
        self.assertIn("Reexamine your views", agent3.prompts[0]["user"])

    def test_no_individual_agent_combination_instructions(self):
        """Make sure when no combo inst set, but set in structure, Agents get what is set in structure"""
        task = "Generate argument for or against social media in 10 words."
        agent1 = Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})
        agent2 = Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})
        agent3 = Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})

        chain = Chain(
            [agent1, agent2, agent3], task=task, combination_instructions="first_wave"
        )
        chain.process()

        self.assertEqual(
            DEFAULTS["combination_instructions"]["first_wave"],
            agent1.combination_instructions,
        )
        self.assertEqual(
            DEFAULTS["combination_instructions"]["first_wave"],
            agent2.combination_instructions,
        )
        self.assertEqual(
            DEFAULTS["combination_instructions"]["first_wave"],
            agent3.combination_instructions,
        )

        self.assertIn("Respect each other’s viewpoints", agent2.prompts[0]["user"])
        self.assertIn("Respect each other’s viewpoints", agent3.prompts[0]["user"])

    def test_chain_debate_instructions(self):
        a2 = Agent(ideology="moderate", model=self.model)
        a3 = Agent(ideology="liberal", model=self.model)
        a4 = Agent(ideology="conservative", model=self.model)
        mixed = Chain([a2, a3, a4], task=self.task, combination_instructions="debate")
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(
            DEFAULTS["combination_instructions"]["debate"],
            mixed.combination_instructions,
        )

    def test_chain_voting_instructions(self):
        """Test chain voting instructions"""
        a2 = Agent(ideology="moderate", model=self.model)
        a3 = Agent(ideology="liberal", model=self.model)
        a4 = Agent(ideology="conservative", model=self.model)
        mixed = Chain([a2, a3, a4], task=self.task, combination_instructions="voting")
        mixed.process()

        # Assertions
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(
            DEFAULTS["combination_instructions"]["voting"],
            mixed.combination_instructions,
        )

    def test_chain_current_task_description(self):
        """Test that the current task description is correct for each agent in a two-agent chain."""
        task = "Describe the impact of social media on society in 50 words."
        agent1 = Agent(
            ideology="moderate", task=task, model=self.model, kwargs=self.kwargs
        )
        agent2 = Agent(
            ideology="conservative", task=task, model=self.model, kwargs=self.kwargs
        )
        chain = Chain([agent1, agent2], task=task)

        # Mock ONLY _get_response from `process()`.
        with patch.object(
                Agent,
                "_get_response",
                return_value="Social media has both positive and negative impacts on society.",
        ):
            chain.process()

        # Expected formatted previous responses
        previous_responses = [
            "Social media has both positive and negative impacts on society."
        ]
        formatted_previous_responses = format_previous_responses(previous_responses)

        # Expected current task descriptions
        expected_agent1_task_description = task
        expected_agent2_task_description = """Describe the impact of social media on society in 50 words.\nUSE PREVIOUS RESPONSES TO COMPLETE THE TASK
Here are the previous responses: 
 <start>
 Response 0: Social media has both positive and negative impacts on society.
 <end>"""

        # Assertions
        self.assertEqual(
            expected_agent1_task_description, agent1.current_task_description
        )
        self.assertEqual(
            expected_agent2_task_description, agent2.current_task_description
        )

    def test_chain_with_different_agent_tasks(self):
        """Test Chain processes Agents with different tasks correctly."""
        task1 = "Discuss the pros of remote work."
        task2 = "Discuss the cons of remote work."
        task3 = "Summarize the discussion on remote work."

        agent1 = Agent(ideology="liberal", model=self.model, task=task1)
        agent2 = Agent(ideology="conservative", model=self.model, task=task2)
        agent3 = Agent(ideology="moderate", model=self.model, task=task3)

        chain = Chain([agent1, agent2, agent3])

        with patch.object(
                Agent,
                "_get_response",
                side_effect=[
                    "Pros: flexibility, no commute.",
                    "Cons: isolation, difficulty in team building.",
                    "Summary: Remote work offers flexibility but poses challenges in collaboration.",
                ],
        ):
            chain.process()

        self.assertEqual(task1, chain.agents[0].original_task_description)
        self.assertEqual(task2, chain.agents[1].original_task_description)
        self.assertEqual(task3, chain.agents[2].original_task_description)
        self.assertEqual(3, len(chain.responses))
        self.assertIn("flexibility", chain.responses[0])
        self.assertIn("isolation", chain.responses[1])
        self.assertIn("Summary", chain.responses[2])


class TestEnsemble(unittest.TestCase):

    def setUp(self):
        self.task = "How should the US handle gun control? Answer in 100 words."
        self.model = "gpt-3.5-turbo"
        self.kwargs = {"temperature": 0.7, "max_tokens": 50, "top_p": 0.9}

    def test_moderator_voting(self):
        """Test moderator persona and combination instructions for voting"""
        a2 = Agent(ideology="moderate", model=self.model)
        a3 = Agent(ideology="liberal", model=self.model)
        a4 = Agent(ideology="conservative", model=self.model)
        mod = Moderator(persona="voting", combination_instructions="voting")
        mixed = Ensemble([a2, a3, a4], task=self.task, moderator=mod)
        mixed.process()
        formatted_responses = mixed.responses[:-1]

        # Assertions
        self.maxDiff = None
        self.assertIsNotNone(mixed.final_response)
        self.assertEqual(
            SmartString(DEFAULTS["moderator"]["persona"]["voting"]).format(
                task=self.task
            ),
            mixed.moderator.persona,
        )
        self.assertEqual(
            SmartString(
                DEFAULTS["moderator"]["combination_instructions"]["voting"]
            ).format(previous_responses=format_previous_responses(formatted_responses)),
            mixed.moderator.combination_instructions,
        )

    def test_ensemble_with_different_agent_tasks(self):
        """Test Ensemble processes Agents with different tasks correctly."""
        task1 = "Discuss economic impacts of climate change."
        task2 = "Discuss social impacts of climate change."
        task3 = "Discuss environmental impacts of climate change."

        a1 = Agent(ideology="liberal", model=self.model, task=task1)
        a2 = Agent(ideology="conservative", model=self.model, task=task2)
        a3 = Agent(ideology="moderate", model=self.model, task=task3)

        ensemble = Ensemble([a1, a2, a3])

        expected_responses = [
            "Economic impacts include increased costs for adaptation.",
            "Social impacts include displacement of communities.",
            "Environmental impacts include loss of biodiversity.",
        ]

        with patch.object(Agent, "_get_response", side_effect=expected_responses):
            ensemble.process()

        self.assertEqual(task1, ensemble.agents[0].original_task_description)
        self.assertEqual(task2, ensemble.agents[1].original_task_description)
        self.assertEqual(task3, ensemble.agents[2].original_task_description)
        self.assertEqual(3, len(ensemble.responses))

        for response in expected_responses:
            self.assertIn(response, ensemble.responses)


class TestDebate(unittest.TestCase):

    def setUp(self):
        self.task = "How should the US handle gun control? Answer in 100 words."
        self.model = "gpt-3.5-turbo"
        self.kwargs = {"temperature": 0.7, "max_tokens": 50, "top_p": 0.9}

    def test_debate_formatting(self):
        agents = [
            Agent(
                persona="You are a mac fanatic trying to convince a user to switch to Mac.",
                model=self.model,
                kwargs=self.kwargs,
            ),
            Agent(persona="A PC fanatic", model=self.model, kwargs=self.kwargs),
        ]

        debate_structure = Debate(
            agents=agents,
            task="Which computer is better? Mac or PC? Answer in 10 words.",
            moderator=Moderator(),
            cycles=3,
        )

        debate_structure.process()

        # Make sure final responses are formatted correctly
        self.assertTrue(debate_structure.responses[0].startswith("[Debater 1]"))
        self.assertTrue(debate_structure.responses[1].startswith("[Debater 2]"))
        self.assertTrue(debate_structure.responses[2].startswith("[Debater 1]"))

        # Check that for Debater 2 on the first turn it is the case that Debater 1's answer is in the user prompt
        # and prefixed by "[WHAT OTHER PARTICIPANT SAID]:"
        user_prompt = agents[1].info["history"][0]["prompts"]["user"]
        self.assertIn("[WHAT OTHER PARTICIPANT SAID]:", user_prompt)
        prev_response = (
            user_prompt.split("[WHAT OTHER PARTICIPANT SAID]:")[1]
            .split("<end>")[0]
            .strip()
        )
        debater_1_initial_response = agents[0].info["history"][0]["response"].strip()
        self.assertEqual(debater_1_initial_response, prev_response)

        # Check that for Debater 1 on the second term it is the case that...
        # Check 1: There is only a single [WHAT YOU SAID] and [WHAT OTHER PARTICIPANT SAID] placeholder
        user_prompt = agents[0].info["history"][1]["prompts"]["user"]
        you_counts = user_prompt.count("[WHAT YOU SAID]:")
        other_counts = user_prompt.count("[WHAT OTHER PARTICIPANT SAID]:")
        self.assertEqual(1, you_counts)
        self.assertEqual(1, other_counts)

        # Check 2: Debater 1's previous response is in the user prompt and
        # prefixed by [WHAT YOU SAID]
        debater_1_initial_response = agents[0].info["history"][0]["response"].strip()
        debater_2_initial_response = agents[1].info["history"][0]["response"].strip()
        self.assertIn("[WHAT YOU SAID]: " + debater_1_initial_response, user_prompt)
        self.assertIn(
            "[WHAT OTHER PARTICIPANT SAID]: " + debater_2_initial_response, user_prompt
        )

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
            "Response 3: Debater [1]",
        ]

        # Check for correct strings in the current task description
        for correct_string in correct_strings:
            self.assertIn(
                correct_string,
                debate_structure.moderator._info["current_task_description"],
                f"{correct_string} should be in the moderator's current task description.",
            )

        # Check for incorrect strings not in the current task description
        for incorrect_string in incorrect_strings:
            self.assertNotIn(
                incorrect_string,
                debate_structure.moderator.info["current_task_description"],
                f"{incorrect_string} should not be in the moderator's current task description.",
            )

    def test_debate_with_different_agent_tasks(self):
        """Test Debate processes Agents with different tasks correctly."""
        task1 = "Argue for stricter gun control laws."
        task2 = "Argue against stricter gun control laws."

        agent1 = Agent(
            persona="You are a gun control advocate.", model=self.model, task=task1
        )
        agent2 = Agent(
            persona="You are a gun rights advocate.", model=self.model, task=task2
        )

        debate = Debate([agent1, agent2], cycles=2)

        with patch.object(
                Agent,
                "_get_response",
                side_effect=[
                    "Stricter laws will reduce gun violence.",
                    "Stricter laws infringe on Second Amendment rights.",
                    "Gun control laws have been effective in other countries.",
                    "Law-abiding citizens need guns for self-defense.",
                ],
        ):
            debate.process()

        self.assertEqual(task1, debate.agents[0].original_task_description)
        self.assertEqual(task2, debate.agents[1].original_task_description)
        self.assertEqual(4, len(debate.responses))
        self.assertIn("Stricter laws will reduce", debate.responses[0])
        self.assertIn("infringe on Second Amendment", debate.responses[1])
        self.assertIn("effective in other countries", debate.responses[2])
        self.assertIn("self-defense", debate.responses[3])

    def test_debate_with_different_combination_instructions(self):
        task = "Debate the pros and cons of artificial intelligence in 10 words."
        agent1 = Agent(
            task=task,
            combination_instructions="Respond to previous argument: ${previous_responses}",
            model="gpt-3.5-turbo",
        )
        agent2 = Agent(
            task=task,
            combination_instructions="Counter the previous point: ${previous_responses}",
            model="gpt-4",
        )

        debate = Debate([agent1, agent2], task=task)
        debate.process()

        print(agent1.combination_instructions)
        self.assertEqual(
            agent1.combination_instructions,
            "Respond to previous argument: ${previous_responses}",
        )
        self.assertEqual(
            agent2.combination_instructions,
            "Counter the previous point: ${previous_responses}",
        )

        self.assertEqual(len(debate.responses), 2)

        self.assertIn("Counter the previous point:", agent2.prompts[0]["user"])

    def test_set_all_individual_agent_combination_instructions(self):
        """Set custom combo insts for all agents"""
        task = "Generate argument for or against social media in 10 words."
        agent1 = Agent(
            task=task,
            combination_instructions="Respond to previous argument: ${previous_responses}",
            model="gpt-3.5-turbo",
            kwargs={"max_tokens": 30},
        )
        agent2 = Agent(
            task=task,
            combination_instructions="Counter the previous point: ${previous_responses}",
            model="gpt-3.5-turbo",
            kwargs={"max_tokens": 30},
        )

        debate = Debate([agent1, agent2], task=task)
        debate.process()

        self.assertEqual(
            agent1.combination_instructions,
            "Respond to previous argument: ${previous_responses}",
        )
        self.assertEqual(
            agent2.combination_instructions,
            "Counter the previous point: ${previous_responses}",
        )

        self.assertNotIn("${previous_responses}", agent2.prompts[0]["user"])
        self.assertIn("Counter the previous point:", agent2.prompts[0]["user"])

    def test_set_some_individual_agent_combination_instructions(self):
        """When combo insts set for some Agents, we use the set instructions for the relevant Agents
        and structure combo instructions for other Agents"""
        task = "Generate argument for or against social media in 10 words."
        agent1 = Agent(
            task=task,
            combination_instructions="Address the previous point: ${previous_responses}",
            model="gpt-3.5-turbo",
            kwargs={"max_tokens": 30},
        )
        agent2 = Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})

        debate = Debate([agent1, agent2], task=task, combination_instructions="debate")
        debate.process()

        self.assertEqual(
            "Address the previous point: ${previous_responses}",
            agent1.combination_instructions,
        )
        self.assertEqual(
            DEFAULTS["combination_instructions"]["debate"],
            agent2.combination_instructions,
        )
        self.assertNotIn("${previous_responses}", agent2.prompts[0]["user"])
        self.assertIn("in the third person", agent2.prompts[0]["user"])

    def test_no_individual_agent_combination_instructions(self):
        """Make sure when no combo inst set, but set in structure, Agents get what is set in structure"""
        task = "Generate argument for or against social media in 10 words."
        agent1 = Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})
        agent2 = Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})

        debate = Debate(
            [agent1, agent2], task=task, combination_instructions="first_wave"
        )
        debate.process()

        self.assertEqual(
            DEFAULTS["combination_instructions"]["first_wave"],
            agent1.combination_instructions,
        )
        self.assertEqual(
            DEFAULTS["combination_instructions"]["first_wave"],
            agent2.combination_instructions,
        )

        self.assertEqual(len(debate.responses), 2)
        self.assertNotIn("${previous_responses}", agent2.prompts[0]["user"])

        self.assertIn("rational-critical debate", agent2.prompts[0]["user"])

    def test_no_individual_agent_combination_instructions_default(self):
        """Make sure when no combo inst set every Agent gets default"""
        task = "Generate argument for or against social media in 10 words."
        agent1 = Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})
        agent2 = Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})

        debate = Debate([agent1, agent2], task=task)
        debate.process()

        self.assertEqual(
            DEFAULTS["combination_instructions"]["debate"],
            agent1.combination_instructions,
        )
        self.assertEqual(
            DEFAULTS["combination_instructions"]["debate"],
            agent2.combination_instructions,
        )
        self.assertNotIn("${previous_responses}", agent2.prompts[0]["user"])

        self.assertEqual(len(debate.responses), 2)
        self.assertIn("third person", agent2.prompts[0]["user"])


class TestAgentStructures(unittest.TestCase):

    def setUp(self):
        self.task = "How should the US handle gun control? Answer in 100 words."
        self.model = "gpt-3.5-turbo"
        self.kwargs = {"temperature": 0.7, "max_tokens": 50, "top_p": 0.9}

    def test_info_method(self):
        agents = [
            Agent(task="First task", model=self.model, kwargs=self.kwargs),
            Agent(task="Second task", model=self.model, kwargs=self.kwargs),
        ]

        moderator = Moderator(persona="default", model=self.model)

        structure = Chain(
            agents=agents, task="General task for agents", moderator=moderator
        )

        # using mocking with this method
        structure.process = MagicMock(return_value=None)
        structure.final_response = "Aggregated final response from mock"
        structure.responses = ["Response from First task", "Response from Second task"]

        info = structure.info

        # validate the dictionary structure and types
        self.assertIsInstance(info, dict)
        self.assertIn("structure_information", info)
        self.assertIn("agent_information", info)

        # validate structure_information
        self.assertEqual(
            "General task for agents", info["structure_information"]["task"]
        )
        self.assertIn("final_response", info["structure_information"])
        self.assertTrue(isinstance(info["structure_information"]["responses"], list))
        self.assertEqual(
            "Aggregated final response from mock",
            info["structure_information"]["final_response"],
        )
        self.assertIn(
            "Response from First task", info["structure_information"]["responses"]
        )
        self.assertIn(
            "Response from Second task", info["structure_information"]["responses"]
        )

        # validate agent_information
        self.assertTrue(isinstance(info["agent_information"], list))
        self.assertEqual(2, len(info["agent_information"]))
        for agent_info in info["agent_information"]:
            self.assertIn("current_task_description", agent_info)
            self.assertIn(
                agent_info["current_task_description"], ["First task", "Second task"]
            )


class TestNetworkStructure(unittest.TestCase):
    """Note: We test that Method 2 initialization results in the same graph as Method 1. The rest of the tests are for Method 1."""

    def setUp(self):
        super().setUp()
        self.task = "What are your thoughts on the role of government in society?"
        self.model = "gpt-3.5-turbo"
        self.kwargs = {"temperature": 0.7, "max_tokens": 50, "top_p": 0.9}

        self.agents_dict = {
            "liberal": Agent(
                system_instructions="you are a liberal",
                model=self.model,
                kwargs=self.kwargs,
            ),
            "conservative": Agent(
                system_instructions="you are a conservative",
                model=self.model,
                kwargs=self.kwargs,
            ),
            "libertarian": Agent(
                system_instructions="you are a libertarian",
                model=self.model,
                kwargs=self.kwargs,
            ),
        }

        self.agents_list = list(self.agents_dict.values())
        self.edges = [
            (
                self.agents_list.index(self.agents_dict["liberal"]),
                self.agents_list.index(self.agents_dict["conservative"]),
            ),
            (
                self.agents_list.index(self.agents_dict["liberal"]),
                self.agents_list.index(self.agents_dict["libertarian"]),
            ),
            (
                self.agents_list.index(self.agents_dict["conservative"]),
                self.agents_list.index(self.agents_dict["libertarian"]),
            ),
        ]

    def test_graph_with_different_agent_tasks(self):
        """Test Graph processes Agents with different tasks correctly."""
        task1 = "Discuss economic policies."
        task2 = "Discuss social policies."
        task3 = "Summarize policy discussions."

        agent1 = Agent(
            system_instructions="you are an economist", model=self.model, task=task1
        )
        agent2 = Agent(
            system_instructions="you are a sociologist", model=self.model, task=task2
        )
        agent3 = Agent(
            system_instructions="you are a policy analyst", model=self.model, task=task3
        )

        agents = [agent1, agent2, agent3]
        edges = [(0, 2), (1, 2)]

        graph = Graph(agents=agents, edges=edges)

        with patch.object(
                Agent,
                "process",
                side_effect=[
                    "Economic policies should focus on growth.",
                    "Social policies should address inequality.",
                    "Both economic growth and social equality are important policy goals.",
                ],
        ):
            final_response = graph.process()

        self.assertEqual(task1, graph.agents[0].original_task_description)
        self.assertEqual(task2, graph.agents[1].original_task_description)
        self.assertEqual(task3, graph.agents[2].original_task_description)
        self.assertEqual(3, len(graph.responses))
        self.assertIn("growth", graph.responses[0])
        self.assertIn("inequality", graph.responses[1])
        self.assertIn("Both economic growth and social equality", final_response)

    def test_graph_with_different_combination_instructions(self):
        task = "Say hello"
        agent1 = Agent(
            task=task,
            combination_instructions="Hello to previous ${previous_responses}",
            model="gpt-3.5-turbo",
        )
        agent2 = Agent(
            task=task,
            combination_instructions="Prev2 to previous ${previous_responses}",
            model="gpt-4",
        )
        agent3 = Agent(
            task=task,
            combination_instructions="Greetings to previous ${previous_responses}",
            model="gpt-3.5-turbo",
        )

        agents = {"agent1": agent1, "agent2": agent2, "agent3": agent3}
        edges = [("agent1", "agent2"), ("agent1", "agent3"), ("agent2", "agent3")]

        graph = Graph(agents=agents, edges=edges, task=task)
        graph.process()

        # Check if the combination instructions are preserved for each agent
        self.assertEqual(
            agent1.combination_instructions, "Hello to previous ${previous_responses}"
        )
        self.assertEqual(
            agent2.combination_instructions, "Prev2 to previous ${previous_responses}"
        )
        self.assertEqual(
            agent3.combination_instructions,
            "Greetings to previous ${previous_responses}",
        )

        self.assertEqual(len(graph.responses), 3)

        # Check if the combination instructions are used in the prompts
        self.assertIn("Prev2 to previous", agent2.prompts[0]["user"])
        self.assertIn("Greetings to previous", agent3.prompts[0]["user"])

        self.assertNotIn("${previous_responses}", agent2.prompts[0]["user"])
        self.assertNotIn("${previous_responses}", agent3.prompts[0]["user"])

    def test_set_all_individual_agent_combination_instructions(self):
        """Set custom combo insts for all agents"""
        task = "Generate argument for or against social media in 10 words."
        agent1 = Agent(
            task=task,
            combination_instructions="Summarize previous insights: ${previous_responses}",
            model="gpt-3.5-turbo",
            kwargs={"max_tokens": 30},
        )
        agent2 = Agent(
            task=task,
            combination_instructions="Provide contrasting viewpoint: ${previous_responses}",
            model="gpt-3.5-turbo",
            kwargs={"max_tokens": 30},
        )
        agent3 = Agent(
            task=task,
            combination_instructions="Synthesize all perspectives: ${previous_responses}",
            model="gpt-3.5-turbo",
            kwargs={"max_tokens": 30},
        )

        agents = {"agent1": agent1, "agent2": agent2, "agent3": agent3}
        edges = [("agent1", "agent2"), ("agent1", "agent3"), ("agent2", "agent3")]

        graph = Graph(agents=agents, edges=edges, task=task)
        graph.process()

        self.assertEqual(
            "Summarize previous insights: ${previous_responses}",
            agent1.combination_instructions,
        )
        self.assertEqual(
            "Provide contrasting viewpoint: ${previous_responses}",
            agent2.combination_instructions,
        )
        self.assertEqual(
            "Synthesize all perspectives: ${previous_responses}",
            agent3.combination_instructions,
        )

        self.assertIn("Provide contrasting viewpoint:", agent2.prompts[0]["user"])
        self.assertIn("Synthesize all perspectives:", agent3.prompts[0]["user"])
        self.assertNotIn("${previous_responses}", agent2.prompts[0]["user"])
        self.assertNotIn("${previous_responses}", agent3.prompts[0]["user"])
        self.assertEqual(3, len(graph.responses))

    def test_set_some_individual_agent_combination_instructions(self):
        """When combo insts set for some Agents, we use the set instructions for the relevant Agents
        and structure combo instructions for other Agents"""
        task = "Generate argument for or against social media in 10 words."
        agent1 = Agent(
            task=task,
            combination_instructions="Build on previous ideas: ${previous_responses}",
            model="gpt-3.5-turbo",
            kwargs={"max_tokens": 30},
        )
        agent2 = Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})
        agent3 = Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})

        agents = {"agent1": agent1, "agent2": agent2, "agent3": agent3}
        edges = [("agent1", "agent2"), ("agent1", "agent3"), ("agent2", "agent3")]

        graph = Graph(
            agents=agents, edges=edges, task=task, combination_instructions="voting"
        )
        graph.process()

        self.assertEqual(
            "Build on previous ideas: ${previous_responses}",
            agent1.combination_instructions,
        )
        self.assertEqual(
            DEFAULTS["combination_instructions"]["voting"],
            agent2.combination_instructions,
        )
        self.assertEqual(
            DEFAULTS["combination_instructions"]["voting"],
            agent3.combination_instructions,
        )

        self.assertIn("single and", agent2.prompts[0]["user"])
        self.assertIn("single and", agent3.prompts[0]["user"])
        self.assertNotIn("${previous_responses}", agent2.prompts[0]["user"])
        self.assertNotIn("${previous_responses}", agent3.prompts[0]["user"])
        self.assertEqual(3, len(graph.responses))

    def test_no_individual_agent_combination_instructions(self):
        """Make sure when no combo inst set, but set in structure, Agents get what is set in structure"""
        task = "Generate argument for or against social media in 10 words."
        agent1 = Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})
        agent2 = Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})
        agent3 = Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})

        agents = {"agent1": agent1, "agent2": agent2, "agent3": agent3}
        edges = [("agent1", "agent2"), ("agent1", "agent3"), ("agent2", "agent3")]

        graph = Graph(
            agents=agents,
            edges=edges,
            task=task,
            combination_instructions="second_wave",
        )
        graph.process()

        self.assertEqual(
            DEFAULTS["combination_instructions"]["second_wave"],
            agent1.combination_instructions,
        )
        self.assertEqual(
            DEFAULTS["combination_instructions"]["second_wave"],
            agent2.combination_instructions,
        )
        self.assertEqual(
            DEFAULTS["combination_instructions"]["second_wave"],
            agent3.combination_instructions,
        )

        self.assertIn("Use empathy", agent2.prompts[0]["user"])
        self.assertIn("Use empathy", agent3.prompts[0]["user"])

        self.assertNotIn("${previous_responses}", agent2.prompts[0]["user"])
        self.assertNotIn("${previous_responses}", agent3.prompts[0]["user"])
        self.assertEqual(3, len(graph.responses))

    def test_no_individual_agent_combination_instructions_default(self):
        """Make sure when no combo inst set every Agent gets default"""
        task = "Generate argument for or against social media in 10 words."
        agent1 = Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})
        agent2 = Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})
        agent3 = Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})

        agents = {"agent1": agent1, "agent2": agent2, "agent3": agent3}
        edges = [("agent1", "agent2"), ("agent1", "agent3"), ("agent2", "agent3")]

        graph = Graph(agents=agents, edges=edges, task=task)
        graph.process()

        self.assertEqual(
            DEFAULTS["combination_instructions"]["default"],
            agent1.combination_instructions,
        )
        self.assertEqual(
            DEFAULTS["combination_instructions"]["default"],
            agent2.combination_instructions,
        )
        self.assertEqual(
            DEFAULTS["combination_instructions"]["default"],
            agent3.combination_instructions,
        )

        self.assertIn("USE PREVIOUS", agent2.prompts[0]["user"])
        self.assertIn("USE PREVIOUS", agent3.prompts[0]["user"])

        self.assertNotIn("${previous_responses}", agent2.prompts[0]["user"])
        self.assertNotIn("${previous_responses}", agent3.prompts[0]["user"])

        self.assertEqual(3, len(graph.responses))

    def test_dict_to_list_conversion(self):
        """Test that the dictionary method (Method 2) correctly converts to the list method (Method 1) internally."""
        agents_dict = {
            "liberal": Agent(
                system_instructions="you are a liberal",
                model=self.model,
                kwargs=self.kwargs,
            ),
            "conservative": Agent(
                system_instructions="you are a conservative",
                model=self.model,
                kwargs=self.kwargs,
            ),
            "libertarian": Agent(
                system_instructions="you are a libertarian",
                model=self.model,
                kwargs=self.kwargs,
            ),
        }
        edges_dict = [
            ("liberal", "conservative"),
            ("liberal", "libertarian"),
            ("conservative", "libertarian"),
        ]

        network_dict = Graph(agents=agents_dict, edges=edges_dict, task=self.task)

        # Check that agents are correctly stored as a list of Agent objects
        self.assertIsInstance(network_dict.agents, list)
        self.assertEqual(len(agents_dict), len(network_dict.agents))
        for agent in agents_dict.values():
            self.assertIn(agent, network_dict.agents)

        # Check that edges are correctly converted to use indices
        expected_edges = [
            (
                list(agents_dict.keys()).index("liberal"),
                list(agents_dict.keys()).index("conservative"),
            ),
            (
                list(agents_dict.keys()).index("liberal"),
                list(agents_dict.keys()).index("libertarian"),
            ),
            (
                list(agents_dict.keys()).index("conservative"),
                list(agents_dict.keys()).index("libertarian"),
            ),
        ]
        self.assertEqual(expected_edges, network_dict.edges)

        # Check that the graph is built correctly
        expected_graph = {
            agents_dict["liberal"]: [
                agents_dict["conservative"],
                agents_dict["libertarian"],
            ],
            agents_dict["conservative"]: [agents_dict["libertarian"]],
            agents_dict["libertarian"]: [],
        }
        self.assertEqual(expected_graph, network_dict.graph)

        # Check that the in-degree is calculated correctly
        expected_in_degree = {
            agents_dict["liberal"]: 0,
            agents_dict["conservative"]: 1,
            agents_dict["libertarian"]: 2,
        }
        self.assertEqual(expected_in_degree, network_dict.in_degree)

        # Check that original agents and edges are stored correctly
        self.assertEqual(agents_dict, network_dict.original_agents)
        self.assertEqual(edges_dict, network_dict.original_edges)

        # Check that combination instructions are set correctly for all agents
        for agent in network_dict.agents:
            self.assertEqual(
                agent.combination_instructions, network_dict.combination_instructions
            )

    def test_initialization(self):
        """Test that the Graph initializes correctly."""
        network = Graph(agents=self.agents_list, edges=self.edges, task=self.task)
        self.assertEqual(self.agents_list, network.agents)
        self.assertEqual(self.edges, network.edges)
        self.assertEqual(self.task, network.task)

    def test_build_graph(self):
        """Test that the graph and in-degree are built correctly."""
        network = Graph(agents=self.agents_list, edges=self.edges, task=self.task)
        expected_graph = {
            self.agents_dict["liberal"]: [
                self.agents_dict["conservative"],
                self.agents_dict["libertarian"],
            ],
            self.agents_dict["conservative"]: [self.agents_dict["libertarian"]],
            self.agents_dict["libertarian"]: [],
        }
        expected_in_degree = {
            self.agents_dict["liberal"]: 0,
            self.agents_dict["conservative"]: 1,
            self.agents_dict["libertarian"]: 2,
        }
        self.assertEqual(expected_graph, network.graph)
        self.assertEqual(expected_in_degree, network.in_degree)

    def test_process(self):
        """Test that the task is processed correctly in topological order."""
        for agent in self.agents_list:
            agent.process = MagicMock(
                return_value=f"Response from {agent.system_instructions}"
            )

        network = Graph(agents=self.agents_list, edges=self.edges, task=self.task)
        final_response = network.process()

        # Verify that agents were processed in topological order
        liberal_response = "Response from you are a liberal"
        conservative_response = "Response from you are a conservative"
        libertarian_response = "Response from you are a libertarian"

        self.assertEqual(libertarian_response, final_response)
        self.assertEqual(
            [liberal_response, conservative_response, libertarian_response],
            network.responses,
        )

    def test_cycle_detection(self):
        """Test that a cycle in the graph raises a ValueError."""
        cyclic_edges = [
            (
                self.agents_list.index(self.agents_dict["liberal"]),
                self.agents_list.index(self.agents_dict["conservative"]),
            ),
            (
                self.agents_list.index(self.agents_dict["conservative"]),
                self.agents_list.index(self.agents_dict["libertarian"]),
            ),
            (
                self.agents_list.index(self.agents_dict["libertarian"]),
                self.agents_list.index(self.agents_dict["liberal"]),
            ),
        ]
        with self.assertRaises(ValueError):
            Graph(agents=self.agents_list, edges=cyclic_edges, task=self.task).process()

    def test_moderator_integration(self):
        """Test that the moderator processes the final response correctly."""
        for agent in self.agents_list:
            agent.process = MagicMock(
                return_value=f"Response from {agent.system_instructions}"
            )

        moderator = Moderator(persona="You are a neutral moderator.", model=self.model)
        network = Graph(
            agents=self.agents_list,
            edges=self.edges,
            task=self.task,
            moderator=moderator,
        )
        network.moderator._moderate_responses = MagicMock(
            return_value="Moderated final response"
        )

        final_response = network.process()

        self.assertEqual("Moderated final response", final_response)
        self.assertEqual(1, network.moderator._moderate_responses.call_count)
        self.assertEqual("Moderated final response", network.responses[-1])

    def test_current_task_description(self):
        """Test that the current task description is correct for each agent in a simple two-agent network."""
        task = "Describe the impact of social media on society in 50 words."
        agent1 = Agent(
            ideology="moderate", task=task, model=self.model, kwargs=self.kwargs
        )
        agent2 = Agent(
            ideology="conservative", task=task, model=self.model, kwargs=self.kwargs
        )
        network = Graph([agent1, agent2], [(0, 1)], task=task)

        # Mock process method to return a predefined response
        agent1.process = MagicMock(
            return_value="Social media has both positive and negative impacts on society."
        )
        network.process()

        # Expected formatted previous responses
        previous_responses = [
            "Social media has both positive and negative impacts on society."
        ]

        # Expected current task descriptions
        expected_agent1_task_description = task
        expected_agent2_task_description = """Describe the impact of social media on society in 50 words.\nUSE PREVIOUS RESPONSES TO COMPLETE THE TASK
Here are the previous responses: 
 <start>
 Agent 0: Social media has both positive and negative impacts on society.
 <end>"""

        # Assertions
        self.assertEqual(
            expected_agent1_task_description, agent1.current_task_description
        )
        self.assertEqual(
            expected_agent2_task_description, agent2.current_task_description
        )


class TestNetworkStructureValidation(TestNetworkStructure):
    """
    Due to the complexity of the Graph class---and the high likelihood of users entering things in a wrong format---we make a subclass of tests dedicated to the
    `validate` method.
    """

    def test_invalid_agents_list_input(self):
        """Test passing non-Agent objects in the agents list."""
        invalid_agents_list = ["liberal", "conservative", "libertarian"]
        edges = [(0, 1), (1, 2)]
        with self.assertRaises(ValueError):
            Graph(agents=invalid_agents_list, edges=edges)

    def test_invalid_edges_list_input(self):
        """Test passing incorrectly formatted edges."""
        edges = ["0-1", "1-2"]  # Invalid because they are not tuples
        with self.assertRaises(ValueError):
            Graph(agents=self.agents_list, edges=edges)

    def test_edges_with_invalid_indices(self):
        """Test edges with indices that are out of bounds for the agents list."""
        edges = [(0, 1), (1, 3)]  # Index 3 is out of bounds
        with self.assertRaises(ValueError):
            Graph(agents=self.agents_list, edges=edges)

    def test_self_loop_edges(self):
        """Test edges that create self-loops, which are not allowed in a DAG."""
        edges = [(0, 1), (1, 1)]  # Self-loop at index 1
        with self.assertRaises(ValueError):
            Graph(agents=self.agents_list, edges=edges)

    def test_invalid_agents_dict_input(self):
        """Test passing incorrectly formatted agent dictionary."""
        invalid_agents_dict = {
            "liberal": "Agent(system_instructions='you are a liberal')",  # Not an Agent object
            "conservative": Agent(
                system_instructions="you are a conservative",
                model=self.model,
                kwargs=self.kwargs,
            ),
        }
        edges = [("liberal", "conservative")]
        with self.assertRaises(ValueError):
            Graph(agents=invalid_agents_dict, edges=edges)

    def test_invalid_edge_names_in_dict(self):
        """Test edges with names not matching any keys in the agent dictionary."""
        agents_dict = {
            "liberal": Agent(
                system_instructions="you are a liberal",
                model=self.model,
                kwargs=self.kwargs,
            ),
            "conservative": Agent(
                system_instructions="you are a conservative",
                model=self.model,
                kwargs=self.kwargs,
            ),
        }
        edges = [
            ("liberal", "conservative"),
            ("liberal", "nonexistent"),
        ]  # 'nonexistent' is not a valid agent key
        with self.assertRaises(ValueError):
            Graph(agents=agents_dict, edges=edges)

    def test_mixed_type_agents_input(self):
        """Test mixed types in agents input."""
        mixed_agents = [
            Agent(
                system_instructions="you are a liberal",
                model=self.model,
                kwargs=self.kwargs,
            ),
            "conservative",  # Not an Agent object
        ]
        edges = [(0, 1)]
        with self.assertRaises(ValueError):
            Graph(agents=mixed_agents, edges=edges)


class TestStructureTaskDescription(unittest.TestCase):
    """
    This tests the 4 cases of setting task descriptions for *agents* where the two factors are:

    - Agent has a task: Y, N
    - Structure has a task: Y, N
    """

    def setUp(self):
        self.model = "gpt-3.5-turbo"

    def test_set_agent_task_description_case1(self):
        """Test Case 1: Task provided to both Structure and agents."""
        structure_task = "Structure task"
        agent_task = "Agent task"
        agent = Agent(task=agent_task, model=self.model)

        with self.assertWarns(UserWarning):
            structure = TestStructure([agent], task=structure_task)

        self.assertEqual(structure_task, agent.task_description)
        self.assertEqual(structure_task, agent.original_task_description)

    def test_set_agent_task_description_case2(self):
        """Test Case 2: No task provided to either Structure or agents."""
        agent = Agent(model=self.model)

        with self.assertRaises(ValueError) as context:
            TestStructure([agent])

        self.assertTrue(
            "Error: You did not specify a task for agents or chain"
            in str(context.exception)
        )

    def test_set_agent_task_description_case3(self):
        """Test Case 3: Task provided to Structure but not agents."""
        structure_task = "Structure task"
        agent = Agent(model=self.model)
        structure = TestStructure([agent], task=structure_task)

        self.assertEqual(structure_task, agent.task_description)
        self.assertEqual(structure_task, agent.original_task_description)

    def test_set_agent_task_description_case4(self):
        """Test Case 4: Task provided to agents but not Structure."""
        agent_task = "Agent task"
        agent = Agent(task=agent_task, model=self.model)
        structure = TestStructure([agent])

        self.assertEqual(agent_task, agent.task_description)
        self.assertEqual(agent_task, agent.original_task_description)

    def test_set_agent_task_description_system_instructions(self):
        """Test that system_instructions are updated with the task."""
        structure_task = "Structure task"
        agent = Agent(model=self.model, system_instructions="Instructions: ${task}")
        structure = TestStructure([agent], task=structure_task)

        self.assertEqual(f"Instructions: {structure_task}", agent.system_instructions)


class TestModeratorTaskDescription(unittest.TestCase):
    """
    This tests the 4 cases of setting task descriptions for moderators where the two factors are:

    - Moderator has a task: Y, N
    - Structure has a task: Y, N
    """

    def setUp(self):
        self.model = "gpt-3.5-turbo"

    def test_set_moderator_task_description_case1(self):
        """Test Case 1: Task provided to both Structure and moderator."""
        structure_task = "Structure task"
        moderator_task = "Moderator task"
        moderator = Moderator(task=moderator_task, model=self.model)

        with self.assertWarns(UserWarning):
            structure = TestStructure(
                [Mock()], task=structure_task, moderator=moderator
            )

        self.assertEqual(moderator_task, moderator.task)

    def test_set_moderator_task_description_case2(self):
        """Test Case 2: No task provided to either Structure or moderator."""
        moderator = Moderator(model=self.model)

        with self.assertRaises(ValueError) as context:
            TestStructure([Mock()], moderator=moderator)

        self.assertTrue(
            "Error: You did not specify a task for Moderator or Structure"
            in str(context.exception)
        )

    def test_set_moderator_task_description_case3(self):
        """Test Case 3: Task provided to Structure but not moderator."""
        structure_task = "Structure task"
        moderator = Moderator(model=self.model)
        structure = TestStructure([Mock()], task=structure_task, moderator=moderator)

        self.assertEqual(structure_task, moderator.task)

    def test_set_moderator_task_description_case4(self):
        """Test Case 4: Task provided to moderator but not Structure."""
        moderator_task = "Moderator task"
        moderator = Moderator(task=moderator_task, model=self.model)
        structure = TestStructure([Mock()], moderator=moderator)

        self.assertEqual(moderator_task, moderator.task)

    def test_set_moderator_task_description_system_instructions(self):
        """Test that system_instructions are updated with the task."""
        structure_task = "Structure task"
        moderator = Moderator(
            model=self.model, system_instructions="Instructions: ${task}"
        )
        structure = TestStructure([Mock()], task=structure_task, moderator=moderator)

        self.assertEqual(
            f"Instructions: {structure_task}", moderator.system_instructions
        )


#############################################
# HELPERS
#############################################


class TestStripNestedDict(unittest.TestCase):
    """
    Makes sure the strip_nested_dict function works as expected for many cases.
    """

    def test_simple_dict(self):
        """Test stripping a simple dictionary with string values."""
        input_dict = {"a": " hello ", "b": "world "}
        expected = {"a": "hello", "b": "world"}
        self.assertEqual(expected, strip_nested_dict(input_dict))

    def test_nested_dict(self):
        """Test stripping a nested dictionary."""
        input_dict = {"a": " outer ", "b": {"c": " inner ", "d": " nested "}}
        expected = {"a": "outer", "b": {"c": "inner", "d": "nested"}}
        self.assertEqual(expected, strip_nested_dict(input_dict))

    def test_dict_with_list(self):
        """Test stripping a dict with a list."""
        input_dict = {"a": " first ", "b": [" second ", " third "]}
        expected = {"a": "first", "b": ["second", "third"]}
        self.assertEqual(expected, strip_nested_dict(input_dict))

    def test_deeply_nested(self):
        """Test stripping a deeply nested structure."""
        input_dict = {
            "a": " level1 ",
            "b": {"c": " level2 ", "d": [" level3 ", {"e": " level4 "}]},
        }
        expected = {
            "a": "level1",
            "b": {"c": "level2", "d": ["level3", {"e": "level4"}]},
        }
        self.assertEqual(expected, strip_nested_dict(input_dict))

    def test_non_string_values(self):
        """Test that non-string values are left unchanged."""
        input_dict = {"a": 42, "b": True, "c": None, "d": 3.14}
        self.assertEqual(input_dict, strip_nested_dict(input_dict))

    def test_empty_structures(self):
        """Test that empty structures are handled correctly."""
        input_dict = {"a": {}, "b": [], "c": ""}
        expected = {"a": {}, "b": [], "c": ""}
        self.assertEqual(expected, strip_nested_dict(input_dict))

    def test_mixed_types(self):
        """Test a dictionary with mixed types."""
        input_dict = {
            "a": " string ",
            "b": 42,
            "c": [" list_item ", 3.14],
            "d": {"e": " nested_string ", "f": True},
        }
        expected = {
            "a": "string",
            "b": 42,
            "c": ["list_item", 3.14],
            "d": {"e": "nested_string", "f": True},
        }
        self.assertEqual(expected, strip_nested_dict(input_dict))


class TestSmartString(unittest.TestCase):

    def test_correctly_replaces_placeholders_no_brackets(self):
        """Test that placeholders are correctly replaced when only thing in brackets is desired replacement."""
        initial_s = "Complete the following task: ${task}."
        formatted_string = SmartString(initial_s).format(task="Do the thing")
        self.assertEqual("Complete the following task: Do the thing.", formatted_string)

    def test_correctly_replaces_placeholders_with_brackets(self):
        """Test that placeholders are correctly replaced when something else uses curly brackets not meant to be
        replaced"""
        initial_s = (
            "Complete the following task: ${task} in json format like {'answer':answer}"
        )
        formatted_string = SmartString(initial_s).format(task="Do the thing")
        self.assertEqual(
            "Complete the following task: Do the thing in json format like {'answer':answer}",
            formatted_string,
        )

    def test_avoid_double_period(self):
        """Test that double periods are correctly removed."""
        initial_s = "Complete the following task: ${task}."
        formatted_string = SmartString(initial_s).format(
            task="Do the thing.", avoid_double_period=True
        )
        self.assertEqual("Complete the following task: Do the thing.", formatted_string)

    def test_no_change_needed(self):
        """Test that the string is not distorted if no change is needed."""
        initial_s = "Complete the following task: ${task}."
        formatted_string = SmartString(initial_s).format(
            task="Do the thing", avoid_double_period=True
        )
        self.assertEqual("Complete the following task: Do the thing.", formatted_string)

    def test_only_remove_double_period(self):
        """Only remove redundant periods induced by the placeholder and not extra ones from user"""
        initial_s = "Think about this task, ${task}."
        task = "respond slowly..."
        formatted_string = SmartString(initial_s).format(
            task=task, avoid_double_period=True
        )
        self.assertEqual(
            "Think about this task, respond slowly...",
            formatted_string,
        )

    def test_none_replacement_in_creation(self):
        """Test that 'None' is replaced with an empty string during string creation."""
        s = SmartString("This is None and this is ${var}")
        self.assertEqual("This is  and this is ${var}", s)

    def test_none_replacement_in_format(self):
        """Test that None values are replaced with empty strings during formatting."""
        s = SmartString("This is ${var1} and this is ${var2}")
        formatted = s.format(var1=None, var2="something")
        self.assertEqual("This is  and this is something", formatted)

    def test_none_replacement_in_both(self):
        """Test None replacement both in creation and formatting."""
        s = SmartString("This is None and this is ${var}")
        formatted = s.format(var=None)
        self.assertEqual("This is  and this is ", formatted)

    def test_none_replacement_with_newline(self):
        """Test None replacement with newline characters."""
        s = SmartString("${var1}\n${var2}")
        formatted = s.format(var1=None, var2="hello")
        self.assertEqual("\nhello", formatted)

    def test_none_replacement_empty_string(self):
        """Test that an empty string is returned when all content is None."""
        s = SmartString("${var1}${var2}")
        formatted = s.format(var1=None, var2=None)
        self.assertEqual("", formatted)


class TestAgentRepr(unittest.TestCase):
    def setUp(self):
        self.agent = Agent(task="Test task", model="gpt-3.5-turbo")

    def test_agent_repr(self):
        """Test that the Agent's __repr__ method produces a string"""
        repr_string = repr(self.agent)
        print(repr_string)
        self.assertIsInstance(repr_string, str)
        self.assertIn("Test task", repr_string)
        self.assertIn("gpt-3.5-turbo", repr_string)

    def test_agent_repr_with_none_values(self):
        """Test that the Agent's __repr__ handles None values correctly"""
        repr_string = repr(self.agent)
        print(repr_string)
        self.assertIn("'persona': None", repr_string)
        self.assertIn("'system_instructions': None", repr_string)

    def test_agent_repr_with_empty_collections(self):
        """Test that the Agent's __repr__ handles empty collections correctly"""
        repr_string = repr(self.agent)
        self.assertIn("'history': None", repr_string)
        self.assertIn("'kwargs': {}", repr_string)


class TestStructureRepr(unittest.TestCase):
    def setUp(self):
        self.agent1 = Agent(task="Task 1", model="gpt-3.5-turbo")
        self.agent2 = Agent(task="Task 2", model="gpt-3.5-turbo")
        self.chain = Chain([self.agent1, self.agent2], task="Chain task")

    def test_structure_repr(self):
        """Test that the Structure's __repr__ method produces a string"""
        repr_string = repr(self.chain)
        self.assertIsInstance(repr_string, str)
        self.assertIn("Chain task", repr_string)
        self.assertIn("gpt-3.5-turbo", repr_string)

    def test_structure_repr_with_none_values(self):
        """Test that the Structure's __repr__ handles None values correctly"""
        self.chain.final_response = None
        repr_string = repr(self.chain)
        self.assertIn("'final_response': None", repr_string)

    def test_structure_repr_with_empty_collections(self):
        """Test that the Structure's __repr__ handles empty collections correctly"""
        self.chain.responses = []
        repr_string = repr(self.chain)
        print(repr_string)
        self.assertIn("'responses': []", repr_string)


class TestPathHandling(unittest.TestCase):
    """Test cases for resource path handling."""

    def test_load_yaml_pkg_resources_paths(self):
        """Test load_yaml works both with and without pkg_resources. This has to do with different versions of Python"""

        # test we can load stuff with pkg_resources
        yaml_content_pkg_resources = load_yaml("instructions.yaml")
        self.assertIsInstance(yaml_content_pkg_resources, dict)
        self.assertIn("persona_template", yaml_content_pkg_resources)
        self.assertIn("combination_instructions", yaml_content_pkg_resources)

        # test we can load stuff without pkg_resources
        with patch("pkg_resources.resource_filename", side_effect=ImportError):
            yaml_content_pathlib = load_yaml("instructions.yaml")
            self.assertIsInstance(yaml_content_pathlib, dict)
            self.assertIn("persona_template", yaml_content_pathlib)
            self.assertIn("combination_instructions", yaml_content_pathlib)

        self.assertEqual(yaml_content_pkg_resources, yaml_content_pathlib)


class CombinationInstructionExpansionTests(unittest.TestCase):
    """Tests verifying the proper expansion of combination instruction templates across structures

    Notes:
        - We don't need to test ensemble because it never uses combination instructions
        - The reason why I am redefining agents a bunch of times is because if you use the same Agents, e.g. in setup,
        then their combination instructions are already set

    """

    def test_structure_template_expansion(self):
        """Test that when no agent has combination instructions, they inherit correctly expanded template from structure"""
        task = "Generate argument for social media in 10 words."

        # Chain
        chain_agents = [
            Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30}),
            Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})
        ]
        chain = Chain(chain_agents, task=task, combination_instructions="chain")
        chain.process()
        chain_template = DEFAULTS["combination_instructions"]["chain"]
        for agent in chain.agents:
            self.assertEqual(chain_template, agent.combination_instructions)

        debate_agents = [
            Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30}),
            Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})
        ]
        debate = Debate(debate_agents, task=task, combination_instructions="debate")
        debate.process()
        debate_template = DEFAULTS["combination_instructions"]["debate"]
        for agent in debate.agents:
            self.assertEqual(debate_template, agent.combination_instructions)

        graph_agents = {
            "agent1": Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30}),
            "agent2": Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})
        }
        graph = Graph(
            agents=graph_agents,
            edges=[("agent1", "agent2")],
            combination_instructions="critique_revise"
        )
        graph.process()
        critique_template = DEFAULTS["combination_instructions"]["critique_revise"]
        for agent in graph.agents:
            self.assertEqual(critique_template, agent.combination_instructions)

    def test_agent_template_expansion(self):
        """Test that agents with template names get their templates properly expanded"""
        task = "Generate argument for social media in 10 words."

        chain_agents = [
            Agent(task=task, combination_instructions="default", model="gpt-3.5-turbo", kwargs={"max_tokens": 30}),
            Agent(task=task, combination_instructions="chain", model="gpt-3.5-turbo", kwargs={"max_tokens": 30})
        ]
        chain = Chain(chain_agents, task=task)
        chain.process()
        self.assertEqual(DEFAULTS["combination_instructions"]["default"], chain_agents[0].combination_instructions)
        self.assertEqual(DEFAULTS["combination_instructions"]["chain"], chain_agents[1].combination_instructions)

        debate_agents = [
            Agent(task=task, combination_instructions="debate", model="gpt-3.5-turbo", kwargs={"max_tokens": 30}),
            Agent(task=task, combination_instructions="default", model="gpt-3.5-turbo", kwargs={"max_tokens": 30})
        ]
        debate = Debate(debate_agents, task=task)
        debate.process()
        self.assertEqual(DEFAULTS["combination_instructions"]["debate"], debate_agents[0].combination_instructions)
        self.assertEqual(DEFAULTS["combination_instructions"]["default"], debate_agents[1].combination_instructions)

        graph_agents = {
            "agent1": Agent(task=task, combination_instructions="critique_revise", model="gpt-3.5-turbo",
                            kwargs={"max_tokens": 30}),
            "agent2": Agent(task=task, combination_instructions="default", model="gpt-3.5-turbo",
                            kwargs={"max_tokens": 30})
        }
        graph = Graph(agents=graph_agents, edges=[("agent1", "agent2")])
        graph.process()
        agent_list = list(graph_agents.values())
        self.assertEqual(DEFAULTS["combination_instructions"]["critique_revise"],
                         agent_list[0].combination_instructions)
        self.assertEqual(DEFAULTS["combination_instructions"]["default"], agent_list[1].combination_instructions)

    def test_mixed_template_expansion(self):
        """Test when some agents have templates and others don't"""
        task = "Generate argument for social media in 10 words."

        chain_agents = [
            Agent(task=task, combination_instructions="default", model="gpt-3.5-turbo", kwargs={"max_tokens": 30}),
            Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})
        ]
        chain = Chain(chain_agents, task=task, combination_instructions="chain")
        chain.process()
        self.assertEqual(DEFAULTS["combination_instructions"]["default"], chain_agents[0].combination_instructions)
        self.assertEqual(DEFAULTS["combination_instructions"]["chain"], chain_agents[1].combination_instructions)

        debate_agents = [
            Agent(task=task, combination_instructions="debate", model="gpt-3.5-turbo", kwargs={"max_tokens": 30}),
            Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})
        ]
        debate = Debate(debate_agents, task=task, combination_instructions="chain")
        debate.process()
        self.assertEqual(DEFAULTS["combination_instructions"]["debate"], debate_agents[0].combination_instructions)
        self.assertEqual(DEFAULTS["combination_instructions"]["chain"], debate_agents[1].combination_instructions)

        graph_agents = {
            "agent1": Agent(task=task, combination_instructions="critique_revise", model="gpt-3.5-turbo",
                            kwargs={"max_tokens": 30}),
            "agent2": Agent(task=task, model="gpt-3.5-turbo", kwargs={"max_tokens": 30})
        }
        graph = Graph(
            agents=graph_agents,
            edges=[("agent1", "agent2")],
            combination_instructions="chain"
        )
        graph.process()
        agent_list = list(graph_agents.values())
        self.assertEqual(DEFAULTS["combination_instructions"]["critique_revise"],
                         agent_list[0].combination_instructions)
        self.assertEqual(DEFAULTS["combination_instructions"]["chain"], agent_list[1].combination_instructions)


class TestEnsembleOrdering(unittest.TestCase):
    """Minimal tests for Ensemble ordering functionality"""

    def setUp(self):
        self.task = "Say your number"
        self.model = "gpt-3.5-turbo"
        self.agents = [
            Agent(model=self.model, persona=f"Agent {i}")
            for i in range(3)
        ]

    def test_nopatch_order_cycles_moderator(self):
        """Test ordering with 10 agents, 3 cycles, and a moderator

        Note: This test uses real API calls, so it may occasionally fail if agents
        don't follow instructions exactly. The test includes retry logic to handle this.
        """

        def is_valid_agent_response(response):
            """Check if response contains any expected agent pattern (Agent 0-9)"""
            return any(f"Agent {i}" in response for i in range(10))

        max_attempts = 5

        for attempt in range(max_attempts):
            print(f"Attempt {attempt + 1}/{max_attempts}")

            try:
                agents = [
                    Agent(
                        model="gpt-3.5-turbo",
                        system_instructions=f"You must respond with exactly these 2 words: 'Agent {i}'. Do not repeat the question. Do not add any other text. Only respond: Agent {i}",
                        kwargs={"temperature": 0, "max_tokens": 5}  # Reduce tokens to force short response
                    )
                    for i in range(10)
                ]

                moderator = Moderator(
                    model="gpt-3.5-turbo",
                    system_instructions="You must respond with exactly these 2 words: 'Moderator summary'. Do not add any other text.",
                    kwargs={"temperature": 0, "max_tokens": 5}
                )

                task = "Respond now."  # Shorter, less likely to be echoed

                ensemble = Ensemble(agents=agents, task=task, cycles=3, moderator=moderator)
                ensemble.process()

                # Check response count - this should never be wrong, fail immediately
                if len(ensemble.responses) != 31:
                    print(f"Wrong response count: got {len(ensemble.responses)}, expected 31")
                    self.fail("Response count is wrong - this indicates a bug in the ordering logic")

                # Check agent responses - this can fail due to LLM not following instructions, so retry
                agent_responses = ensemble.responses[:-1]
                invalid_count = sum(1 for r in agent_responses if not is_valid_agent_response(r))

                if invalid_count > 0:
                    print(f"Found {invalid_count} invalid agent responses")
                    for i, r in enumerate(agent_responses):
                        if not is_valid_agent_response(r):
                            print(f"  Position {i}: '{r}'")
                    if attempt == max_attempts - 1:
                        self.fail(f"Invalid responses after {max_attempts} attempts")
                    continue

                # Check moderator response - this can fail due to LLM not following instructions, so retry
                if "Moderator" not in ensemble.responses[-1]:
                    print(f"Bad moderator response: '{ensemble.responses[-1]}'")
                    if attempt == max_attempts - 1:
                        self.fail(f"Bad moderator response after {max_attempts} attempts")
                    continue

                # All validations passed
                print("Validation passed")
                break

            except Exception as e:
                print(f"Error: {str(e)}")
                self.fail(f"Unexpected exception: {e}")  # Don't retry on exceptions

        # Test ordering - these should never fail, fail immediately
        print("Testing ordering...")
        for cycle in range(3):
            for agent_num in range(10):
                response_index = cycle * 10 + agent_num
                expected_text = f"Agent {agent_num}"
                actual_response = ensemble.responses[response_index]

                if expected_text not in actual_response:
                    print(
                        f"Ordering failure at position {response_index}: expected '{expected_text}', got '{actual_response}'")
                    self.fail("Ordering test failed - this indicates a bug in the ordering logic")

        # Test final response
        self.assertEqual(ensemble.final_response, ensemble.responses[-1])

        # Test agent histories
        for i, agent in enumerate(agents):
            if len(agent.history) != 3:
                print(f"Agent {i} has {len(agent.history)} history entries, expected 3")
                self.fail("History test failed - this indicates a bug")

        print("All tests passed")

    def test_single_cycle_no_moderator(self):
        """Test ordering with single cycle, no moderator"""
        with patch.object(Agent, '_get_response', side_effect=['A0', 'A1', 'A2']):
            ensemble = Ensemble(agents=self.agents, task=self.task, cycles=1)
            ensemble.process()

            self.assertEqual(ensemble.responses, ['A0', 'A1', 'A2'])
            self.assertEqual(ensemble.final_response, 'A2')

    def test_single_cycle_with_moderator(self):
        """Test ordering with single cycle, with moderator"""
        moderator = Moderator(model=self.model)

        with patch.object(Agent, '_get_response', side_effect=['A0', 'A1', 'A2', 'MOD']):
            ensemble = Ensemble(agents=self.agents, task=self.task, cycles=1, moderator=moderator)
            ensemble.process()

            self.assertEqual(ensemble.responses, ['A0', 'A1', 'A2', 'MOD'])
            self.assertEqual(ensemble.final_response, 'MOD')

    def test_three_cycles_no_moderator(self):
        """Test ordering with 3 cycles, no moderator"""
        # 3 agents * 3 cycles = 9 responses total
        mock_responses = [f'A{i}-C{c}' for c in range(3) for i in range(3)]

        with patch.object(Agent, '_get_response', side_effect=mock_responses):
            ensemble = Ensemble(agents=self.agents, task=self.task, cycles=3)
            ensemble.process()

            expected = ['A0-C0', 'A1-C0', 'A2-C0',  # Cycle 0
                        'A0-C1', 'A1-C1', 'A2-C1',  # Cycle 1
                        'A0-C2', 'A1-C2', 'A2-C2']  # Cycle 2

            self.assertEqual(ensemble.responses, expected)
            self.assertEqual(ensemble.final_response, 'A2-C2')

    def test_three_cycles_with_moderator(self):
        """Test ordering with 3 cycles, with moderator"""
        moderator = Moderator(model=self.model)

        # 3 agents * 3 cycles + 1 moderator = 10 responses total
        mock_responses = [f'A{i}-C{c}' for c in range(3) for i in range(3)] + ['MOD']

        with patch.object(Agent, '_get_response', side_effect=mock_responses):
            ensemble = Ensemble(agents=self.agents, task=self.task, cycles=3, moderator=moderator)
            ensemble.process()

            expected = ['A0-C0', 'A1-C0', 'A2-C0',  # Cycle 0
                        'A0-C1', 'A1-C1', 'A2-C1',  # Cycle 1
                        'A0-C2', 'A1-C2', 'A2-C2',  # Cycle 2
                        'MOD']  # Moderator

            self.assertEqual(ensemble.responses, expected)
            self.assertEqual(ensemble.final_response, 'MOD')


class TestGraphAgentNaming(unittest.TestCase):
    """Test that agent names appear correctly in Graph structure for both agents and moderators"""

    def setUp(self):
        self.task = "What are your thoughts on government? answer in 1 word only"
        self.model = "gpt-4o-mini"

    def test_graph_dict_method_agent_names_in_responses(self):
        """Test that when using dict method, agent names appear in previous_responses for agents"""
        agents = {
            'liberal': Agent(system_instructions="you are a liberal", model=self.model),
            'conservative': Agent(system_instructions="you are a conservative", model=self.model),
            'libertarian': Agent(system_instructions="you are a libertarian", model=self.model)
        }
        edges = [('liberal', 'conservative'), ('liberal', 'libertarian'), ('conservative', 'libertarian')]

        graph = Graph(agents=agents, edges=edges, task=self.task)
        graph.process()

        # Check that libertarian agent saw named responses
        libertarian_prompt = agents['libertarian'].prompts[0]['user']
        self.assertIn('liberal:', libertarian_prompt)
        self.assertIn('conservative:', libertarian_prompt)

    def test_graph_list_method_agent_names_in_responses(self):
        """Test that when using list method, agent indices appear in previous_responses for agents"""
        agents = [
            Agent(system_instructions="you are a liberal", model=self.model),
            Agent(system_instructions="you are a conservative", model=self.model),
            Agent(system_instructions="you are a libertarian", model=self.model)
        ]
        edges = [(0, 1), (0, 2), (1, 2)]

        graph = Graph(agents=agents, edges=edges, task=self.task)
        graph.process()

        # Check that libertarian agent (index 2) saw numbered agent responses
        libertarian_prompt = agents[2].prompts[0]['user']
        self.assertIn('Agent 0:', libertarian_prompt)
        self.assertIn('Agent 1:', libertarian_prompt)

    def test_graph_dict_method_moderator_sees_agent_names(self):
        """Test that moderator sees agent names when using dict method"""
        agents = {
            'liberal': Agent(system_instructions="you are a liberal", model=self.model),
            'conservative': Agent(system_instructions="you are a conservative", model=self.model),
        }
        edges = [('liberal', 'conservative')]

        moderator = Moderator(persona='default', model=self.model)
        graph = Graph(agents=agents, edges=edges, task=self.task, moderator=moderator)
        graph.process()

        # Check that moderator saw named responses
        moderator_prompt = moderator.prompts[0]['user']
        self.assertIn('liberal:', moderator_prompt)
        self.assertIn('conservative:', moderator_prompt)

    def test_graph_list_method_moderator_sees_agent_indices(self):
        """Test that moderator sees agent indices when using list method"""
        agents = [
            Agent(system_instructions="you are a liberal", model=self.model),
            Agent(system_instructions="you are a conservative", model=self.model),
        ]
        edges = [(0, 1)]

        moderator = Moderator(persona='default', model=self.model)
        graph = Graph(agents=agents, edges=edges, task=self.task, moderator=moderator)
        graph.process()

        # Check that moderator saw numbered agent responses
        moderator_prompt = moderator.prompts[0]['user']
        self.assertIn('Agent 0:', moderator_prompt)
        self.assertIn('Agent 1:', moderator_prompt)

    def test_graph_complex_dag_agent_names(self):
        """Test agent names in a more complex DAG structure"""
        agents = {
            'A': Agent(system_instructions="Agent A", model=self.model),
            'B': Agent(system_instructions="Agent B", model=self.model),
            'C': Agent(system_instructions="Agent C", model=self.model),
            'D': Agent(system_instructions="Agent D", model=self.model),
        }
        # A -> B, A -> C, B -> D, C -> D
        edges = [('A', 'B'), ('A', 'C'), ('B', 'D'), ('C', 'D')]

        graph = Graph(agents=agents, edges=edges, task=self.task)
        graph.process()

        # Agent D should see responses from B and C
        agent_d_prompt = agents['D'].prompts[0]['user']
        self.assertIn('B:', agent_d_prompt)
        self.assertIn('C:', agent_d_prompt)
        self.assertNotIn('A:', agent_d_prompt)  # D doesn't directly receive from A

    def test_graph_agent_name_mapping_consistency(self):
        """Test that agent name mapping is consistent throughout processing"""
        agents = {
            'first': Agent(system_instructions="first agent", model=self.model),
            'second': Agent(system_instructions="second agent", model=self.model),
            'third': Agent(system_instructions="third agent", model=self.model),
        }
        edges = [('first', 'second'), ('second', 'third')]

        graph = Graph(agents=agents, edges=edges, task=self.task)

        # Get the mapping
        agent_to_name = graph._create_agent_name_mapping()

        # Verify mapping is correct
        self.assertEqual(agent_to_name[agents['first']], 'first')
        self.assertEqual(agent_to_name[agents['second']], 'second')
        self.assertEqual(agent_to_name[agents['third']], 'third')
        self.assertEqual(len(agent_to_name), 3)

    def test_graph_list_agent_name_mapping_consistency(self):
        """Test that agent name mapping is consistent for list method"""
        agents = [
            Agent(system_instructions="first agent", model=self.model),
            Agent(system_instructions="second agent", model=self.model),
            Agent(system_instructions="third agent", model=self.model),
        ]
        edges = [(0, 1), (1, 2)]

        graph = Graph(agents=agents, edges=edges, task=self.task)

        # Get the mapping
        agent_to_name = graph._create_agent_name_mapping()

        # Verify mapping uses indices
        self.assertEqual(agent_to_name[agents[0]], 'Agent 0')
        self.assertEqual(agent_to_name[agents[1]], 'Agent 1')
        self.assertEqual(agent_to_name[agents[2]], 'Agent 2')
        self.assertEqual(len(agent_to_name), 3)

    def test_graph_no_moderator_agent_names_still_work(self):
        """Test that agent names work correctly even without a moderator"""
        agents = {
            'alice': Agent(system_instructions="alice", model=self.model),
            'bob': Agent(system_instructions="bob", model=self.model),
        }
        edges = [('alice', 'bob')]

        graph = Graph(agents=agents, edges=edges, task=self.task)
        graph.process()

        # Bob should see Alice's response with name
        bob_prompt = agents['bob'].prompts[0]['user']
        self.assertIn('alice:', bob_prompt)
        self.assertNotIn('Response 0:', bob_prompt)



if __name__ == "__main__":
    unittest.main()
