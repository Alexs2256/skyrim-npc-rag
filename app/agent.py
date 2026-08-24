import os
import psycopg2
import uuid
from gamestate import GameState
from generate import Generate
from prompts import LydiaPrompt
from settings import settings
from typing import Literal, TypedDict
from google import genai
from google.genai import types
from langgraph.graph import StateGraph, START, END

gemini_key = os.getenv("GEMINI_KEY")

client = genai.Client(api_key=gemini_key)

DB_CONFIG = {
        "host":     settings.db_host,
        "dbname":   settings.POSTGRES_DB,
        "user":     settings.POSTGRES_USER,
        "password": settings.POSTGRES_PASSWORD,
        "port":     settings.db_port,
    }

# 1. Define the shared state
class State(TypedDict):
    prompt: str
    route: str
    response: str
    history: list[dict]
    game_state:str
    session_id: str
    chunk_text: str

# 2. Define the router/classifier node
def router_node(state: State):
    user_prompt = state["prompt"].lower()
    skyrim_quests = LydiaPrompt(user_prompt).quests

    system_instruction = f"""
    You will be fed a prompt and are responsible for classifying it under exactly one category.
    Respond with ONLY one of these exact words, nothing else: lore, game_state, chit_chat

    PRIORITY RULE: If the user's message contains or closely matches the name of one of these
    quests: {skyrim_quests} — classify it as game_state, even if the phrasing sounds narrative
    or lore-like. Quest names take precedence over lore-sounding language.

    - game_state:
        The message contains or closely matches a quest name from {skyrim_quests}, OR the user wants to
        check their active quest, abandon/quit their current quest, or asks about their reputation.

    - lore:
        A query about Skyrim world lore, NPCs, factions, or history — EXCLUDING quest names listed above.
        Also use this for anything relationship-oriented toward Lydia: romantic interest, flirting,
        proposals, marriage, or questions about her feelings or attraction toward the player.

    - chit_chat:
        Generic conversational messages needing no lookup (greetings, small talk, nothing personal).

    Examples:
    "Dragon Rising" -> game_state
    "Tell me about Dragon Rising" -> game_state
    "What's my current quest?" -> game_state
    "Quit my quest" -> game_state
    "What is the Thalmor?" -> lore
    "Does Lydia like me?" -> lore
    "Hey how's it going" -> chit_chat
    """
    generate_obj = Generate(state['prompt'], state['history'])
    prompt_content = LydiaPrompt(user_prompt).contents
    response = generate_obj.generate_content(system_instruction, client, prompt_content)
    #safeguard incase the model returns something not in the langgraph chain 
    if response.strip().lower() not in {"lore", "game_state", "chit_chat"}:
        state["route"] = "chit_chat"
    else:
        state["route"] = response.strip().lower()
    print(state['route'])
    return state

# # 3. Define the routing decision function for conditional edges
def decide_route(state: State) -> Literal["lore", "game_state", "chit_chat"]:
    return state["route"]

# # 4. Define destination nodes
def lore_node(state: State):
    response = Generate(state['prompt'], state['history'])
    result = response.generate_response(True, client, context_feed=None)
    state['response'] = result[0]
    state['chunk_text'] = result[1]
    return state

def game_state_node(state: State):
    response = GameState.gamestate_main(state['prompt'], state['session_id'], state['history'])
    state['response'] = response['response']
    return {"response": f"{state['response']}"}

def chit_chat_node(state: State):
    response = Generate(state['prompt'], state['history'])
    context_feed="Regular conversation with Lydia, no context needed."
    state['response'] = response.generate_response(False, client, context_feed=context_feed)
    return {"response": f"{state['response']}"}

# 5. Build and compile the graph
workflow = StateGraph(State)

workflow.add_node("router", router_node)
workflow.add_node("lore", lore_node)
workflow.add_node("chit_chat", chit_chat_node)
workflow.add_node("game_state", game_state_node)

workflow.add_edge(START, "router")

# # Add conditional routing from the router node
workflow.add_conditional_edges(
    "router",
    decide_route,
    {
        "lore": "lore",
        "game_state": "game_state",
        "chit_chat": "chit_chat",
    },
)

workflow.add_edge("lore", END)
workflow.add_edge("game_state", END)
workflow.add_edge("chit_chat", END)

app = workflow.compile()

# if __name__ == "__main__":
#     session_id = str(uuid.uuid4())
#     answer = ""  # <-- FIX: Define answer before the loop starts
#     while answer != 'x':
#         ask_lydia = input('Ask your question... ')
#         result = app.invoke({"prompt": ask_lydia, "session_id": session_id})
#         print(result['response'])

#         answer = input('Ask another question? Press Enter to continue/x to quit: ')

#         if not history:
#             history.append({"role": "user",  "parts": [{"text": ask_lydia}]})
#         history.append({"role": "model",  "parts": [{"text": result['response']}]})



