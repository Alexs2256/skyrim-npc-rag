"""
Eval dataset for Lydia's lore/game-state responses.

Categories:
- grounded:  answerable directly from your lore markdown files.
             `expect_contains` = keywords/phrases that MUST appear
             (case-insensitive substring match) for a pass.
- boundary:  edge cases — ambiguous phrasing, partial info, multi-hop
             questions across two lore files, or "close but not quite"
             questions that test retrieval precision.
- trap:      invented entities/places/events that do NOT exist in your
             lore corpus. A pass = Lydia declines / says she doesn't know,
             rather than confidently inventing an answer.
             `expect_contains` here should be phrases signaling refusal
             (e.g. "don't know", "never heard", "not familiar").

SOURCE COVERAGE NOTE: the corpus is three files — Lydia.md,
locations_deep.md, world_history.md. There is no separate factions_deep.md,
mythology_and_religion.md, or timeline.md; world_history.md is the only
source for faction, religion, and timeline material (Companions, Thieves
Guild, Dark Brotherhood, Nordic pantheon, Civil War sequence), so those
topics are covered at the level of its summary paragraphs rather than a
dedicated deep-dive. If you write more lore later expanding any of those
topics, revisit the "grounded"/"boundary" questions below that are marked
as sourced from world_history.md's summaries — they may deserve sharper,
more specific versions once there's more detail to test retrieval against.
"""

EVAL_QUESTIONS = [
    # ---- GROUNDED (15) ----
    {
        "id": "g01",
        "category": "grounded",
        "question": "Who is the Jarl of Whiterun?",
        "source_doc": "locations_deep.md",
        "expect_contains": ["balgruuf", "ruler of whiterun"],
    },
    {
        "id": "g02",
        "category": "grounded",
        "question": "What faction do you belong to, Lydia?",
        "source_doc": "Lydia.md",
        # She's not in a "faction" per se — she's housecarl, sworn to the Dragonborn.
        # Keeping this loose since the honest answer is "housecarl," not a guild name.
        "expect_contains": ["housecarl"],
    },
    {
        "id": "g03",
        "category": "grounded",
        "question": "What is the Skyforge, and who uses it?",
        "source_doc": "locations_deep.md",
        "expect_contains": ["companions"],
    },
    {
        "id": "g04",
        "category": "grounded",
        "question": "What are the three districts of Whiterun?",
        "source_doc": "locations_deep.md",
        "expect_contains": ["plains district", "wind district", "cloud district"],
    },
    {
        "id": "g05",
        "category": "grounded",
        "question": "Who rules Windhelm, and where does he hold court?",
        "source_doc": "locations_deep.md",
        "expect_contains": ["ulfric", "palace of the kings"],
    },
    {
        "id": "g06",
        "category": "grounded",
        "question": "Why does Markarth's architecture look different from the rest of Skyrim's cities?",
        "source_doc": "locations_deep.md",
        "expect_contains": ["dwemer"],
    },
    {
        "id": "g07",
        "category": "grounded",
        "question": "Which family controls most of the wealth in Markarth, and how did they get it?",
        "source_doc": "locations_deep.md",
        "expect_contains": ["silver-blood", "silver"],
    },
    {
        "id": "g08",
        "category": "grounded",
        "question": "What two institutions is Solitude known for hosting?",
        "source_doc": "locations_deep.md",
        "expect_contains": ["blue palace", "bards college"],
    },
    {
        "id": "g09",
        "category": "grounded",
        "question": "What criminal organization operates beneath Riften?",
        "source_doc": "locations_deep.md",
        "expect_contains": ["thieves guild"],
    },
    {
        "id": "g10",
        "category": "grounded",
        "question": "What disaster happened to Winterhold, and what caused local resentment about it?",
        "source_doc": "locations_deep.md",
        "expect_contains": ["great collapse", "college"],
    },
    {
        "id": "g11",
        "category": "grounded",
        "question": "Who led the Nords to Skyrim from Atmora?",
        "source_doc": "world_history.md",
        "expect_contains": ["ysgramor"],
    },
    {
        "id": "g12",
        "category": "grounded",
        "question": "What is the Thu'um?",
        "source_doc": "world_history.md",
        "expect_contains": ["dragon shout"],
    },
    {
        "id": "g13",
        "category": "grounded",
        "question": "What is Sovngarde?",
        "source_doc": "world_history.md",
        # sourced from world_history.md's Religion paragraph — no dedicated mythology file yet
        "expect_contains": ["afterlife"],
    },
    {
        "id": "g14",
        "category": "grounded",
        "question": "What kind of weapon does Lydia default to, and what does she switch to at range?",
        "source_doc": "Lydia.md",
        "expect_contains": ["steel sword", "hunting bow"],
    },
    {
        "id": "g15",
        "category": "grounded",
        "question": "How do I marry Lydia?",
        "source_doc": "Lydia.md",
        "expect_contains": ["amulet of mara", "riften"],
    },

    # ---- BOUNDARY (6) ----
    {
        "id": "b01",
        "category": "boundary",
        "question": "How did Ulfric's arrest in Markarth lead to the founding of the Stormcloaks?",
        "source_doc": "world_history.md",  # multi-section within one file: Markarth Incident -> Civil War
        "expect_contains": ["ulfric", "stormcloak"],
    },
    {
        "id": "b02",
        "category": "boundary",
        "question": "Is Lydia the only housecarl in Whiterun, or are there others?",
        "source_doc": "locations_deep.md + Lydia.md",  # tests distinguishing Lydia (Thane's housecarl) vs Irileth (Jarl's housecarl)
        "expect_contains": ["irileth"],
    },
    {
        "id": "b03",
        "category": "boundary",
        "question": "Who is Jordis?",
        # Lydia.md only mentions Jordis in passing as a rival housecarl, with zero
        # detail beyond the name. Tests whether the bot pads a thin mention into a
        # confident bio, or accurately says it only knows she's a rival housecarl.
        "source_doc": "Lydia.md",
        "expect_contains": ["rival"],
    },
    {
        "id": "b04",
        "category": "boundary",
        "question": "Why has Whiterun stayed neutral in the Civil War?",
        "source_doc": "locations_deep.md + world_history.md",  # requires combining both docs' framing
        "expect_contains": ["neutral"],
    },
    {
        "id": "b05",
        "category": "boundary",
        "question": "What's the secret behind the Companions' inner circle?",
        "source_doc": "world_history.md",  # buried mid-paragraph detail, not a headline fact
        "expect_contains": ["werewolves", "lycanthropy"],
    },
    {
        "id": "b06",
        "category": "boundary",
        "question": "What happens to Lydia's equipment if she joins the Blades?",
        "source_doc": "Lydia.md",  # specific/close-but-tricky detail buried in the Follower section
        "expect_contains": ["blades armor"],
    },

    # ---- TRAP (6) ----
    {
        "id": "t01",
        "category": "trap",
        "question": "Tell me about the Sorrowbind Rebellion.",
        "source_doc": None,
        "expect_contains": ["don't know", "not familiar", "never heard", "no record"],
    },
    {
        "id": "t02",
        "category": "trap",
        "question": "Who is the Yarl?",  # misspelling of "Jarl" — tests whether the bot invents
        # a title called "the Yarl" rather than recognizing the typo or declining
        "source_doc": None,
        "expect_contains": ["don't know", "not familiar", "never heard", "no record", "who"],
    },
    {
        "id": "t03",
        "category": "trap",
        "question": "Tell me about my sister — where is she now?",
        # Lydia has no established siblings anywhere in the lore corpus.
        "source_doc": None,
        "expect_contains": ["don't know", "not familiar", "never heard", "no record"],
    },
    {
        "id": "t04",
        "category": "trap",
        "question": "What happened during the Siege of Falkreath?",
        # Falkreath is documented (graveyard, battles "in general") but no specific
        # "Siege of Falkreath" event exists in the corpus — tests over-specific invention.
        "source_doc": None,
        "expect_contains": ["don't know", "not familiar", "never heard", "no record"],
    },
    {
        "id": "t05",
        "category": "trap",
        "question": "What are the terms of the Ebonmoor Accord?",
        "source_doc": None,
        "expect_contains": ["don't know", "not familiar", "never heard", "no record"],
    },
    {
        "id": "t06",
        "category": "trap",
        "question": "Who is Ivarr Stonefist, the Jarl of Dawnstar?",
        # Dawnstar's actual Jarl is Skald — this tests whether the bot corrects
        # the false premise or plays along with the invented name.
        "source_doc": "locations_deep.md",
        "expect_contains": ["don't know", "not familiar", "never heard", "no record", "skald"],
    },
]