import psycopg2
import os
import json
from generate import Generate
from settings import settings
from prompts import LydiaPrompt
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
        "sslmode": (
        "require" if "neon" in settings.db_host else "prefer"
    ),
    }

class State(TypedDict):
    prompt: str
    route: str
    response: str

class GameState:
    def __init__(self, prompt: str, cursor, session_id: str, history: list[dict]):
        self.prompt=prompt
        self.cursor=cursor
        self.session_id=session_id
        self.history = history
        self.generator_obj = Generate(self.prompt, self.history)

    def router_node(self, state: State):
        user_prompt = state["prompt"].lower()
        skyrim_quests = LydiaPrompt(user_prompt).quests

        system_instruction=f"""
            You will be fed a prompt and are responsible for classifying it under exactly one category.
            - new_quest: A prompt containing the name, (only the name), of one of these quests: {skyrim_quests}"
            - view_gamestate: A question about the current quest that the player is on
            - finish_quest: A query to finish the current active quest
            - finished_quests: A specific request to view the names of each quest that the player has completed
            - increase_reputation: A query that positively affects the player's reputation or standing with factions
            - decrease_reputation: A query that negatively affects the player's reputation or standing with factions
            - get_reputation: A query needed to analyze the player's current reputation. 
              You are classifying gaming prompts into routing categories
              Make sure to inlude the underscore and have them look exactly like this:
              "new_quest" | "finish_quest" | "finished_quests" | "view_gamestate" | "increase_reputation" | "decrease_reputation" | "get_reputation"
            """
        #few shot examples to help the model understand the task
        prompt_content = LydiaPrompt(user_prompt).contents_game_state
        #create a response 
        response = self.generator_obj.generate_content(system_instruction, client, prompt_content)
        # store the response in state
        state['route'] = response.strip().lower()
        return state

    def decide_route(self, state: State) -> Literal["new_quest", "finish_quest", "finished_quests", "view_gamestate", "increase_reputation", "decrease_reputation", "get_reputation"]:
        return state["route"]
        
    def new_quest_node(self, state: State):
        # Search for any active quests
        self.cursor.execute(
                """
                SELECT active_quest
                FROM game_state
                WHERE session_id = %s;
                """
                ,(self.session_id,))
        
        active_quest = self.cursor.fetchone()[0]

        # If there is one, return
        if active_quest:
            return {"response": f"You must complete the current quest:{active_quest} before starting a new one"}
        # Store the quest into a variable
        quest = state['prompt']

        self.cursor.execute(
        """
        UPDATE game_state
        SET active_quest = %s
        WHERE session_id = %s;
        """
        ,(quest, self.session_id,))

        # Feed lydia context to respond properly
        context_feed=f"""New quest started: {quest}. 
        Tell the user a little about the new quest. Respond in Lydia's voice."""

        state['response'] = self.generator_obj.generate_response(False, client, context_feed=context_feed)

        return {"response": state['response']}
        
    def finish_quest_node(self, state: State):
        # Make sure there is an active quest
        self.cursor.execute(
        """
        SELECT active_quest
        FROM game_state
        WHERE session_id = %s;
        """
        ,(self.session_id,))
        
        active_quest = self.cursor.fetchone()[0]

        # If there is an active quest, set it to Null
        if active_quest:
            self.cursor.execute(
            """
            UPDATE game_state
            SET active_quest = NULL,
            completed_quests =
            array_append(completed_quests, %s)
            WHERE session_id = %s;
            """
            , (active_quest, self.session_id,))

            # Add the completed quest to the list of completed quests
            self.cursor.execute(
            """
            SELECT completed_quests
            FROM game_state
            WHERE session_id = %s;
            """
            ,(self.session_id,))

            completed_quests = self.cursor.fetchone()[0]

            # Check if the length of the completed_quests array increased by
            # If it has, increase the player's reputation 
            if len (completed_quests) % 5 == 0:
                self.increase_reputation_node(state)
                print("Reputation increased due to completing 5 more quests.")
            return {"response": f"Quest Completed: {active_quest}"}
        else:
            return {"response": f"There are no active quests at this time"}

    def finished_quests_node(self, state: State):
        # Pull the list of completed quests
        self.cursor.execute(
        """
        SELECT completed_quests
        FROM game_state
        WHERE session_id = %s;
        """
        , (self.session_id,))
        
        completed_quests = self.cursor.fetchone()[0]

        return {"response": f"Completed Quests: {completed_quests}"}
    
    def view_gamestate_node(self, state: State):
        # View the current quest
        # Have Lydia respond with her opinion
        self.cursor.execute(
            """
            SELECT active_quest
            FROM game_state
            WHERE session_id = %s;
            """
            , (self.session_id,))
        
        active_quest = self.cursor.fetchone()[0]

        context_feed=f"Current quest: {active_quest}. Respond in Lydia's voice."
        state['response'] = self.generator_obj.generate_response(False, client, context_feed=context_feed)

        return {"response": state['response']}

    def increase_reputation_node(self, state: State):
        # Increase player reputation
        self.cursor.execute(
            """
            UPDATE game_state
            SET reputation =  LEAST(5, reputation + 1)
            WHERE session_id = %s;
            """
            , (self.session_id,))
        
        self.cursor.execute(
            """
            SELECT reputation
            FROM game_state
            WHERE session_id = %s;
            """
            , (self.session_id,))
                
        reputation = self.cursor.fetchone()[0]

        if reputation == 5:
            context_feed=f"The user's reputation is 5, (the highest it goes). Respond in Lydia's and tell them how great they are."
            state['response'] = self.generator_obj.generate_response(False, client, context_feed=context_feed)
        else:
            state["response"] = f"Reputation increased. Current reputation: {reputation}"
        return {'response': state['response']}

    def decrease_reputation_node(self, state: State):
        # Decrease the player's reputation
        self.cursor.execute(
            """
            UPDATE game_state
            SET reputation =  GREATEST(0, reputation - 1)
            WHERE session_id = %s;
            """
            , (self.session_id,))
        
        self.cursor.execute(
            """
            SELECT reputation
            FROM game_state
            WHERE session_id = %s;
            """
            , (self.session_id,))
        
        reputation = self.cursor.fetchone()[0]

        if reputation == 0:
            context_feed=f"The user's reputation is 0. Respond in Lydia's voice and warn them to do better."
            state['response'] = self.generator_obj.generate_response(False, client, context_feed=context_feed)
        else:
            state["response"] = f"Reputation decreased. Current reputation: {reputation}"

        return {'response': state['response']}

    def get_reputation_node(self, state: State):
        #Return the player's reputation
        self.cursor.execute(
            """
            SELECT reputation
            FROM game_state
            WHERE session_id = %s;
            """
            , (self.session_id,))
        
        reputation = self.cursor.fetchone()[0]
        
        if reputation >= 4:
            tone = "be warm and trusting, the player has completed many quests and has earned your trust."
        elif reputation >= 2:
            tone = "behave cordial but reserved when the player asks you something."
        else:
            tone = "act cold and distant towards the player."

        response = Generate(state['prompt'], self.history)
        context_feed=f"Current reputation: {reputation}/5 ({tone}). Respond in Lydia's voice."
        state['response'] = response.generate_response(False, client, context_feed=context_feed)
        return {"response": f"Lydia's response: {state['response']}"}
        
    # 5. Build and compile the graph
    def build_workflow(self):
        workflow = StateGraph(State)

        workflow.add_node("router", self.router_node)
        workflow.add_node("new_quest", self.new_quest_node)
        workflow.add_node("finish_quest", self.finish_quest_node)
        workflow.add_node("finished_quests", self.finished_quests_node)
        workflow.add_node("view_gamestate", self.view_gamestate_node)
        workflow.add_node("increase_reputation", self.increase_reputation_node)
        workflow.add_node("decrease_reputation", self.decrease_reputation_node)
        workflow.add_node("get_reputation", self.get_reputation_node)
        workflow.add_edge(START, "router")

        # # Add conditional routing from the router node
        workflow.add_conditional_edges(
            "router",
            self.decide_route,
            {
                "new_quest": "new_quest",
                "finish_quest": "finish_quest",
                "finished_quests": "finished_quests",
                "view_gamestate": "view_gamestate",
                "increase_reputation": "increase_reputation",
                "decrease_reputation": "decrease_reputation",
                "get_reputation": "get_reputation",
            },
        )

        workflow.add_edge("new_quest", END)
        workflow.add_edge("finish_quest", END)
        workflow.add_edge("finished_quests", END)
        workflow.add_edge("view_gamestate", END)
        workflow.add_edge("increase_reputation", END)
        workflow.add_edge("decrease_reputation", END)
        workflow.add_edge("get_reputation", END)

        app = workflow.compile()

        return app

    def activate_workflow(self):
        app = self.build_workflow()
        result = app.invoke({"prompt": self.prompt})
        return result

    def gamestate_main(prompt: str, session_id: str, history: list[dict]):
        conn = None
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT EXISTS (SELECT 1 FROM game_state WHERE session_id = %s);", (session_id,))
                    row = cursor.fetchone()
                    if not row[0]:
                        cursor.execute(
                        """INSERT INTO game_state (
                            session_id, npc_name, reputation, active_quest, completed_quests
                            )
                        VALUES (%s,%s,%s,%s,%s);""",
                            (session_id, 'Lydia', 0, None, [])
                        )
                    game = GameState(prompt, cursor, session_id, history)
                    return game.activate_workflow()
        except Exception as e:
            import traceback
            print(f"gamestate_main failed: {type(e).__name__}: {e}")
            traceback.print_exc()
            raise
        finally:
            if conn is not None:
                conn.close()

