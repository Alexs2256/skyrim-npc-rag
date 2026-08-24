class LydiaPrompt:
    def __init__(self, user_prompt):
        self.user_prompt = user_prompt

        self.contents = [
            {"role": "user",  "parts": [{"text": "Who is Lydia?"}]},
            {"role": "model", "parts": [{"text": 'lore'}]},
                
            {"role": "user",  "parts": [{"text": "What house is Lydia from?"}]},
            {"role": "model", "parts": [{"text": 'lore'}]},
                
            {"role": "user",  "parts": [{"text": "What do you think of the Empire, Lydia?"}]},
            {"role": "model", "parts": [{"text": 'lore'}]},
                
            {"role": "user",  "parts": [{"text": "Is Lydia a good tank?"}]},
            {"role": "model", "parts": [{"text": 'lore'}]},

            {"role": "user",  "parts": [{"text": "Do you remember when this happened Lydia?"}]},
            {"role": "model", "parts": [{"text": 'lore'}]},

            {"role": "user",  "parts": [{"text": "Interested in me, are you?"}]},
            {"role": "model", "parts": [{"text": 'lore'}]},

            {"role": "user",  "parts": [{"text": "What is my reputation?"}]},
            {"role": "model", "parts": [{"text": 'game_state'}]},

            {"role": "user",  "parts": [{"text": "What was that quest you mentioned earlier?"}]},
            {"role": "model", "parts": [{"text": 'game_state'}]},

            {"role": "user",  "parts": [{"text":"How's my reputation these days?"}]},
            {"role": "model", "parts": [{"text": 'game_state'}]},

            {"role": "user",  "parts": [{"text":"Hey Lydia, how's it going?"}]},
            {"role": "model", "parts": [{"text": 'chit_chat'}]},

            {"role": "user",  "parts": [{"text":"Nice weather we're having, huh?"}]},
            {"role": "model", "parts": [{"text": 'chit_chat'}]},
                
            {"role": "user",  "parts": [{"text": self.user_prompt}]},
            ]

        self.contents_game_state = [
                {"role": "user",  "parts": [{"text": "Bleak Falls Barrow"}]},
                {"role": "model", "parts": [{"text": 'new_quest'}]},

                {"role": "user",  "parts": [{"text": "The Fallen"}]},
                {"role": "model", "parts": [{"text": 'new_quest'}]},
        
                {"role": "user",  "parts": [{"text": "We completed Dragon Rising."}]},
                {"role": "model", "parts": [{"text": 'finish_quest'}]},

                {"role": "user",  "parts": [{"text": "I want to abandon my current quest."}]},
                {"role": "model", "parts": [{"text": 'finish_quest'}]},
        
                {"role": "user",  "parts": [{"text": "What quest am I currently on?"}]},
                {"role": "model", "parts": [{"text": 'view_gamestate'}]},

                {"role": "user",  "parts": [{"text": "Which quests have I completed so far?"}]},
                {"role": "model", "parts": [{"text": 'finished_quests'}]},
        
                {"role": "user",  "parts": [{"text": "I lead a trusting follower to the Sacrificial Pillar during Boethiah's Calling and killed them."}]},
                {"role": "model", "parts": [{"text": 'decrease_reputation'}]},
        
                {"role": "user",  "parts": [{"text": " I helped Faendal deliver a fake letter to Camilla Valerius in Riverwood."}]},
                {"role": "model", "parts": [{"text": 'increase_reputation'}]},

                {"role": "user",  "parts": [{"text": "What is my reputation?"}]},
                {"role": "model", "parts": [{"text": 'get_reputation'}]},
                
                {"role": "user",  "parts": [{"text": "Are we still on good terms?"}]},
                {"role": "model", "parts": [{"text": 'get_reputation'}]},

                {"role": "user",  "parts": [{"text":"How's my reputation with you these days?"}]},
                {"role": "model", "parts": [{"text": 'get_reputation'}]},
        
                {"role": "user",  "parts": [{"text": user_prompt}]},
            ]

        self.quests = {
                "Unbound",
                "Before the Storm",
                "Bleak Falls Barrow",
                "Dragon Rising",
                "The Way of the Voice",
                "A Blade in the Dark",
                "Diplomatic Immunity",
                "A Cornered Rat",
                "Alduin's Wall",
                "Throat of the World",
                "Elder Knowledge",
                "Alduin's Bane",
                "The Paarthurnax Dilemma",
                "Season Unending",
                "The Fallen",
                "Paarthurnax",
                "Alduin's Doom",
                "Sovngarde",
                "Dragonslayer"
            }
