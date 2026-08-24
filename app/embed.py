import numpy as np
import os
from dotenv import load_dotenv
from google.genai import types
from google import genai

load_dotenv() 

gemini_key = os.getenv("GEMINI_KEY")

client = genai.Client(api_key=gemini_key)

class embed:
    
    def __init__(self, embed_text):
        self.embed_text = embed_text 

    def get_embedding(self):
        response = client.models.embed_content(
        model="gemini-embedding-2-preview",
        contents=self.embed_text,  
        config=types.EmbedContentConfig(output_dimensionality=1536) 
            
        )
        
        raw_vector = np.array(response.embeddings[0].values)
        norm = np.linalg.norm(raw_vector)
        
        if norm > 0:
            vector_embedding = (raw_vector / norm).tolist()
        else:
            vector_embedding = raw_vector.tolist()

        return vector_embedding