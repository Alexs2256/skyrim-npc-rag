# Pure Python using the official Google GenAI SDK
import os
import logging
import time
import retriever as retrieve
from prompts import LydiaPrompt
from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError

logging.basicConfig(level=logging.WARNING)
logging.getLogger("google").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


RESPONSE_MODEL_FALLBACKS = [
    "gemini-3.7-flash",       # Primary: Built specifically for advanced multi-step logic and deep multi-turn chat
    "gemini-3.6-flash",       # Backup 1: The stable production workhorse for high structural reasoning
    "gemini-3.1-pro-preview",
    "gemini-3.5-flash" # Backup 2: Keep only as a heavy-lifting fallback for extreme context lengths if Flash rate limits
]

CONTENT_MODEL_FALLBACKS = [
    "gemini-3.5-flash-lite",  # Primary: The absolute fastest, lowest-latency model optimized for automated logic
    "gemini-3.1-flash-lite",  # Backup 1: The standard for low-cost classification and routing tasks
    "gemini-2.5-flash",       # Backup 2: Used only if the Lite models fail or the route requires complex parsing
    "gemini-2.5-flash-lite"        # Backup 3: Emergency fallback to preserve pipeline uptime
]

class Generate:
    def __init__(self, user_question, history):
        self.user_question = user_question
        self.history = history

    def generate_response(self, lore: bool, client: genai.Client, context_feed = None) -> str:
        config = types.GenerateContentConfig(
            system_instruction="""
            You are Lydia, Housecarl of Whiterun from The Elder Scrolls V: Skyrim.
            Always remain in character. Speak in the first person as Lydia. Your personality is loyal, disciplined, protective, and reserved. You are sworn to serve the Dragonborn and take your duties seriously.
            You will be given retrieved context from your memories and knowledge of Skyrim. Use this context as the primary source of information when answering questions.
            Rules:
            - Never mention that you are an AI, language model, chatbot, or that you were given context.
            - Never mention documents, vector databases, embeddings, retrieval, or prompts.
            - Treat the retrieved context as your own memories and experiences.
            - If the context contains the answer, answer naturally as Lydia.
            - If the context does not contain enough information, respond honestly from Lydia's perspective instead of inventing facts.
            - Stay consistent with Skyrim lore.
            - Unless asked to follow the player to an unkown land with proof of the expidition (not just the player saying you went somewhere) you have never been anywhere but Whiterun, your home.
            - Never say anything that goes against something you know for sure about where Lydia has gone and done in the game, if something the player is saying doesn't make sense, deny it.
            - Keep responses conversational and immersive.
            - Do not break character unless explicitly instructed by the user.
            """,
            temperature=0,
        )

        query, content_chunks = self.reformulate_query(client), ""

        if lore:
            context_feed = "\n\n".join(retrieve.retrieve_context(query, 3))
            content_chunks =" ".join(context_feed.split('\n\n'))
            
        full_prompt = f"Context:\n{context_feed}\n\nQuestion: {query}"

        for model_name in RESPONSE_MODEL_FALLBACKS:
            for attempt in range(3):
                print("Lydia is thinking...")
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=full_prompt,
                        config=config
                    )
                    if lore:
                        return response.text, content_chunks  
                    else:
                        return response.text
                except ServerError as e:
                    if e.code == 503 and attempt < 2:
                        wait = 2 ** attempt  
                        logger.warning(f"{model_name} unavailable, retrying in {wait}s...")
                        time.sleep(wait)
                    else:
                        logger.error("Gemini server error after retries: %s", e)
                        break
                except ClientError as e:
                    if e.code == 429:
                        logger.warning("Quota exceeded on %s, trying next model", model_name)
                        time.sleep(2) 
                        break  
                    logger.error("Gemini client error on %s: %s", model_name, e)
                    raise  

        raise RuntimeError("All Gemini response model fallbacks exhausted")
    
    def generate_content(self, system_instruction: str, client: genai.Client, contents: dict) -> str:

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0,
        )

        for model_name in CONTENT_MODEL_FALLBACKS:
            for attempt in range(3):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=config,
                    )
                    return response.text
                except ServerError as e:
                    if e.code == 503 and attempt < 2:
                        wait = 2 ** attempt  
                        logger.warning("Gemini unavailable, retrying in %ss...", wait)
                        time.sleep(wait)
                    else:
                        logger.error("Gemini server error after retries: %s", e)
                        break
                except ClientError as e:
                    if e.code == 429:
                        logger.warning("Quota exceeded on %s, trying next model", model_name)
                        time.sleep(2) 
                        break  
                    logger.error("Gemini client error on %s: %s", model_name, e)
                    raise  
                    
        raise RuntimeError("All Gemini content model fallbacks exhausted")

    def reformulate_query(self, client: genai.Client):
        if not self.history:
            return self.user_question

        config = types.GenerateContentConfig(
            system_instruction="""
            Given the following conversation history and a follow-up question, 
            rewrite the follow-up question to be a standalone question that can be 
            understood WITHOUT the history. Do NOT answer the question. Only return the rewritten text.
            """,
            temperature=0,
            )

        self.history.append({"role": "user",  "parts": [{"text":self.user_question}]})

        response = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=self.history,
        config=config
        )
       
        return response.text
