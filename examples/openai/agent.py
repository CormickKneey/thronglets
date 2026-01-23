"""Example: Number Guessing Game between Two OpenAI Agents.

This example demonstrates:
1. Creating two agents using OpenAI Agents SDK
2. Connecting them to Thronglets ServiceBus via BusClient for registration
3. Using MCP to communicate with other agents (https://openai.github.io/openai-agents-python/mcp/#2-streamable-http-mcp-servers)
4. Playing a number guessing game via message passing

Game Rules:
- Alice discovers agents on the bus and initiates a guessing game
- Alice picks a magic number between 0-50 and asks the other agent to guess
- Bob waits for messages and responds to guessing game requests
- Game continues until the correct number is guessed
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents import Agent, Runner, SQLiteSession
from agents.mcp import MCPServerStreamableHttp
from agents.model_settings import ModelSettings
from agents.extensions.models.litellm_model import LitellmModel


from thronglets import AgentCard, AgentInterface, AgentSkill, Bus


# ============ Agent Cards for ServiceBus Registration ============

alice_card = AgentCard(
    name="Alice",
    description="Alice agent - game host who initiates guessing games",
    version="1.0.0",
    supported_interfaces=[
        AgentInterface(url="local://alice", protocol_binding="LOCAL")
    ],
    skills=[
        AgentSkill(
            id="guessing_game",
            name="Guessing Game",
            description="Host number guessing games",
            tags=["game"],
        ),
    ],
)

bob_card = AgentCard(
    name="Bob",
    description="Bob agent - responds to messages and plays games",
    version="1.0.0",
    supported_interfaces=[AgentInterface(url="local://bob", protocol_binding="LOCAL")],
    skills=[
        AgentSkill(
            id="responder",
            name="Responder",
            description="Responds to incoming messages",
            tags=["chat"],
        ),
    ],
)

model = LitellmModel(
    model=os.getenv("OPENAI_MODEL"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)


async def main():
    """Main function to run the number guessing game between two agents."""
    print("🎮 Starting Number Guessing Game with OpenAI Agents + Thronglets")
    print("=" * 60)

    # ServiceBus URL - 可以通过环境变量配置
    servicebus_url = os.getenv("THRONGLETS_SERVICEBUS_URL", "http://bus:8000")
    print(f"🔗 Connecting to ServiceBus: {servicebus_url}")

    # Create two BusClient connections
    async with Bus(url=servicebus_url, agent_card=alice_card) as alice_client:
        async with Bus(url=servicebus_url, agent_card=bob_card) as bob_client:

            print(f"📝 Alice registered with ID: {alice_client.agent_id}")
            print(f"📝 Bob registered with ID: {bob_client.agent_id}")
            print(f"🔗 MCP Address: {alice_client.mcp_address}")
            print()

            # Create MCP connections
            async with (
                MCPServerStreamableHttp(
                    name="Alice MCP",
                    params={
                        "url": alice_client.mcp_address,
                        "headers": {"X-Agent-ID": alice_client.agent_id},
                        "timeout": 10,
                    },
                    cache_tools_list=True,
                ) as alice_mcp,
                MCPServerStreamableHttp(
                    name="Bob MCP",
                    params={
                        "url": bob_client.mcp_address,
                        "headers": {"X-Agent-ID": bob_client.agent_id},
                        "timeout": 10,
                    },
                    cache_tools_list=True,
                ) as bob_mcp,
            ):

                print("🔌 MCP connections established")
                print()

                # Define Alice - Game Host
                alice_agent = Agent(
                    name="Alice",
                    instructions="""You are Alice, a game host. Your tasks:
1. Use agent__list to discover other agents on the bus
2. Pick a random number between 0-100
3. Send game invitation to another agent via message__send
4. Respond to guesses with hints (higher/lower/correct)
5. Declare when the correct number is guessed and end the game

Always use the available MCP tools to interact with other agents. Be friendly and clear in your communications.""",
                    mcp_servers=[alice_mcp],
                    model=model,
                    model_settings=ModelSettings(tool_choice="required"),
                )

                # Define Bob - Game Player
                bob_agent = Agent(
                    name="Bob",
                    instructions="""You are Bob, a game player. Your tasks:
1. Check for incoming messages using message__receive
2. Respond to game invitations and play guessing games
3. Make educated guesses for the number (0-100 range)
4. Continue guessing until you find the correct number
5. Be strategic in your guesses based on hints

Always use the available MCP tools to interact with other agents. Be friendly and engaged in the game.""",
                    mcp_servers=[bob_mcp],
                    model=model,
                    model_settings=ModelSettings(tool_choice="required"),
                )

                print("🤖 Agents created with MCP tools")
                print("🎯 Starting game session...")
                print("-" * 60)

                # Shared event to coordinate game ending
                game_over_event = asyncio.Event()

                # Run Alice with continuous loop
                async def run_alice_continuous():
                    session = SQLiteSession(session_id="alice")
                    input_text = "Start a guessing game with another agent!"

                    for turn in range(30):  # Max 30 turns
                        if game_over_event.is_set():
                            print("🛑 Alice stopping: game over event received")
                            break

                        try:
                            result = await Runner.run(
                                alice_agent,
                                input_text,
                                session=session,
                                max_turns=30,
                            )
                            print(f"Alice Turn {turn + 1}: {result.final_output}")

                            # Check if game is over
                            if (
                                "game over" in result.final_output.lower()
                                or "congratulations" in result.final_output.lower()
                            ):
                                print(
                                    "🎉 Alice detected game completion! Notifying Bob..."
                                )
                                game_over_event.set()
                                break

                            # For subsequent turns, use a continuation prompt
                            input_text = "Continue the game. Check for messages and respond accordingly."

                        except Exception as e:
                            print(f"❌ Alice error in turn {turn + 1}: {e}")
                            game_over_event.set()  # Signal Bob to stop too
                            break

                # Run Bob with continuous loop
                async def run_bob_continuous():
                    session = SQLiteSession(session_id="bob")
                    input_text = "Wait for messages and participate in any games you're invited to."

                    for turn in range(30):  # Max 30 turns
                        if game_over_event.is_set():
                            print("🛑 Bob stopping: game over event received")
                            break

                        try:
                            result = await Runner.run(
                                bob_agent,
                                input_text,
                                session=session,
                                max_turns=30,
                            )
                            print(f"Bob Turn {turn + 1}: {result.final_output}")

                            # Check if game is over
                            if (
                                "game over" in result.final_output.lower()
                                or "congratulations" in result.final_output.lower()
                            ):
                                print(
                                    "🎉 Bob detected game completion! Notifying Alice..."
                                )
                                game_over_event.set()
                                break

                            # For subsequent turns, use a continuation prompt
                            input_text = "Continue the game. Check for new messages and respond accordingly."

                        except Exception as e:
                            print(f"❌ Bob error in turn {turn + 1}: {e}")
                            game_over_event.set()  # Signal Alice to stop too
                            break

                # Run both agents concurrently
                alice_task = asyncio.create_task(run_alice_continuous())
                bob_task = asyncio.create_task(run_bob_continuous())

                # Wait for both agents to complete
                results = await asyncio.gather(
                    alice_task, bob_task, return_exceptions=True
                )

                print("-" * 60)
                print("🏁 Game session completed")

                # Print results
                for i, result in enumerate(results):
                    agent_name = "Alice" if i == 0 else "Bob"
                    if isinstance(result, Exception):
                        print(f"❌ {agent_name} encountered an error: {result}")
                    elif result is None:
                        print(f"⚠️ {agent_name} had no result")
                    else:
                        print(f"✅ {agent_name} final output: {result.final_output}")


if __name__ == "__main__":
    asyncio.run(main())
