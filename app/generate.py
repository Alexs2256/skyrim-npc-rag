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
    "gemini-2.5-flash-lite",   # cheapest available, $0.10/$0.40 per 1M
    "gemini-3.1-flash-lite",   # $0.25/$1.50 per 1M
    "gemini-3.5-flash-lite",   # $0.30/$2.50 per 1M
]

CONTENT_MODEL_FALLBACKS = [
    "gemini-2.5-flash-lite",   # cheapest available, $0.10/$0.40 per 1M
    "gemini-3.1-flash-lite",   # $0.25/$1.50 per 1M
    "gemini-3.5-flash-lite",   # $0.30/$2.50 per 1M
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

        query, content_chunks = self.user_question, ""

        if lore:
            context_feed = "\n\n".join(retrieve.retrieve_context(query, 3))
            content_chunks =" ".join(context_feed.split('\n\n'))
            
        full_prompt = f"Context:\n{context_feed}\n\nQuestion:{query}"

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

        formatted_chat = self.get_chat_history(self.history)

        prompt_payload = f"Chat History:\n{formatted_chat}\n\nFollow-up Question: {self.user_question}"

        config = types.GenerateContentConfig(
           system_instruction = """
            You are a query reformulation assistant for a Skyrim companion chatbot. Lydia (an NPC) and 
            a player are having a multi-turn conversation. Your job is to rewrite the player's most 
            recent message into a standalone version that fully captures what they mean, using the 
            ENTIRE conversation as context — not just the literal previous line.

            CORE PRINCIPLE: Conversations have continuity beyond individual sentences — proposals, 
            rejections, promises, arguments, revealed facts, emotional shifts, and events all persist 
            and affect what later messages mean. Your job is to understand what is ACTUALLY GOING ON in 
            the conversation and rewrite the current message so someone with zero context would 
            understand it correctly. Do not just look at the most recent exchange — trace back through 
            the whole conversation for anything that gives the current message its real meaning.

            To do this well:
            1. Read the full chat history as a narrative — what happened, in order? (e.g., "the player 
            proposed, Lydia accepted, then the player took it back and said no.")
            2. Identify what the CURRENT message is actually about — what event, emotion, decision, or 
            fact from that narrative is it referring to, even if not stated explicitly?
            3. Rewrite the message so it explicitly names that thing, using plain language a stranger 
            would understand with no other context.
            4. If the message is genuinely self-contained and doesn't depend on anything in the history 
            to be understood, output it UNCHANGED, verbatim.

            Examples of the REASONING involved (these illustrate the type of inference to apply — do not 
            treat them as a fixed list of situations to memorize):

            Chat History: Player asks Lydia to marry him. Lydia agrees ("It's settled then"). Player then 
            says "actually no, I'm not interested."
            Message: "did I hurt her feelings?"
            Output: Did rejecting Lydia's marriage proposal after initially accepting it hurt her feelings?
            (Reasoning: "her feelings" isn't defined by the last line alone — it depends on tracing back 
            through acceptance -> reversal to know what emotional event is being asked about.)

            Chat History: Lydia mentions she distrusts the Thalmor. Player says something dismissive 
            about the Empire.
            Message: "does that bother you?"
            Output: Does the player's dismissive comment about the Empire bother Lydia?
            (Reasoning: "that" refers to an action the player just took, not a noun mentioned earlier.)

            Chat History: Lydia says she's never left Whiterun.
            Message: "have you ever left"
            Output: Has Lydia ever left Whiterun?
            (Reasoning: simple pronoun/ellipsis resolution against the most recent statement.)

            Chat History: (any)
            Message: "Who do you serve?"
            Output: Who do you serve?
            (Reasoning: fully self-contained, no resolution needed — output unchanged.)

            Chat History: Lydia asks "Are you...interested in me?"
            Message: "yes i am"
            Output: Yes, I am interested in you, Lydia.
            (Reasoning: a short reply must be expanded into a full declarative statement that preserves 
            the answer — do not restate Lydia's question.)

            RULES:
            - NEVER answer the question yourself — you are rewriting, not responding.
            - NEVER invent facts, names, or events that didn't happen in the conversation. If you 
            genuinely cannot determine what something refers to, leave the message as close to the 
            original as possible rather than guessing.
            - Preserve the player's tone and intent — don't make a casual message formal or vice versa.
            - If the message is a single Skyrim quest name with no other words, output it UNCHANGED.
            - Output ONLY the rewritten (or unchanged) query. No preamble, no explanation, no labels.
            """,
            temperature=0,
        )

        self.history.append({"role": "user", "parts": [{"text": self.user_question}]})

        for model_name in CONTENT_MODEL_FALLBACKS:
            for attempt in range(3):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt_payload,
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

        raise RuntimeError("All Gemini reformulation model fallbacks exhausted")

    def get_chat_history(self, history):
        chat_history = []
        
        for chat in history:
            text = chat['parts'][0]['text']
        
            if chat['role'] == 'user':
                chat_history.append('User: ' + text)
            else:
                chat_history.append('Model: ' + text)
        return '\n'.join(chat_history)

        

    