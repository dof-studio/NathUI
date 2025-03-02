# strlang.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

import re

def is_english(text: str, threshold: float = 0.20) -> (float, bool):
    """
    Determine if the provided text is likely English by calculating the ratio 
    of common English words present in the text.

    The function converts the text to lowercase and extracts words using regex. 
    It then compares the proportion of words that appear in a predefined set of 
    common English words against a threshold.

    Args:
        text: The string to analyze.
        threshold: The minimum ratio of common words required to classify the text as English.
                   Default is 0.2 (i.e., 20%).

    Returns:
        Ratio (Float),
        True if the ratio of common words meets or exceeds the threshold, otherwise False.
    """
    # A set of common English words
    common_words = {
 "the", "be", "of", "and", "a", "to", "in", "he", "have", "it",
    "that", "for", "they", "I", "with", "as", "not", "on", "she", "at",
    "by", "this", "we", "you", "do", "but", "from", "or", "which", "one",
    "would", "all", "will", "there", "say", "who", "make", "when", "can",
    "more", "if", "no", "man", "out", "other", "so", "what", "time",
    "up", "go", "about", "than", "into", "could", "state", "only",
    "new", "year", "some", "take", "come", "these", "know", "see",
    "use", "get", "like", "then", "first", "any", "work", "now",
    "may", "such", "give", "over", "think", "most", "even", "find",
    "day", "also", "after", "way", "many", "must", "look", "before",
    "great", "back", "through", "long", "where", "much", "should",
    "well", "people", "down", "own", "just", "because", "good",
    "each", "those", "feel", "seem", "how", "high", "too", "place",
    "little", "world", "very", "still", "nation", "hand", "old",
    "life", "tell", "write", "become", "here", "show", "house",
    "both", "between", "need", "mean", "call", "develop", "under",
    "last", "right", "move", "thing", "general", "school", "never",
    "same", "another", "begin", "while", "number", "part", "turn",
    "real", "leave", "might", "want", "point", "form", "off", "child",
    "few", "small", "since", "against", "ask", "late", "home",
    "interest", "large", "person", "end", "open", "public", "follow",
    "during", "present", "without", "again", "hold", "govern",
    "around", "possible", "head", "consider", "word", "program",
    "problem", "however", "lead", "system", "set", "order", "eye",
    "plan", "run", "keep", "face", "fact", "group", "play", "stand",
    "increase", "early", "course", "change", "help", "line", "city",
    "put", "close", "case", "force", "meet", "once", "water", "upon",
    "war", "build", "hear", "light", "unite", "live", "every",
    "country", "bring", "center", "let", "side", "try", "provide",
    "continue", "name", "certain", "power", "pay", "result",
    "question", "study", "woman", "member", "until", "far", "night",
    "always", "service", "away", "report", "something", "company",
    "week", "church", "toward", "start", "social", "room", "figure",
    "nature", "though", "young", "less", "enough", "almost", "read",
    "include", "president", "nothing", "yet", "better", "big", "boy",
    "cost", "business", "value", "second", "why", "clear", "expect",
    "family", "complete", "act", "sense", "mind", "experience",
    "art", "next", "near", "direct", "car", "law", "industry",
    "important", "girl", "god", "several", "matter", "usual",
    "rather", "per", "often", "kind", "among", "white", "reason",
    "action", "return", "foot", "care", "simple", "within", "love",
    "human", "along", "appear", "doctor", "believe", "speak",
    "active", "student", "month", "drive", "concern", "best",
    "door", "hope", "example", "inform", "body", "ever", "least",
    "probable", "understand", "reach", "effect", "different",
    "idea", "whole", "control", "condition", "field", "pass",
    "fall", "note", "special", "talk", "particular", "today",
    "measure", "walk", "teach", "low", "hour", "type", "carry",
    "rate", "remain", "full", "street", "easy", "although",
    "record", "sit", "determine", "level", "local", "sure",
    "receive", "thus", "moment", "spirit", "train", "college",
    "religion", "perhaps", "music", "grow", "free", "cause",
    "serve", "age", "book", "board", "recent", "sound", "office",
    "cut", "step", "class", "true", "history", "position",
    "above", "strong", "friend", "necessary", "add", "court",
    "deal", "tax", "support", "party", "whether", "either",
    "land", "material", "happen", "education", "death",
    "agree", "arm", "mother", "across", "quite", "anything",
    "town", "past", "view", "society", "manage", "answer",
    "break", "organize", "half", "fire", "lose", "money",
    "stop", "actual", "already", "effort", "wait",
    "department", "able", "political", "learn", "voice",
    "air", "together", "shall", "cover", "common", "subject",
    "draw", "short", "wife", "treat", "limit", "road",
    "letter", "color", "behind", "produce", "send", "term",
    "total", "university", "rise", "century", "success",
    "minute", "remember", "purpose", "test", "fight",
    "watch", "situation", "south", "ago", "difference",
    "stage", "father", "table", "rest", "bear", "entire",
    "market", "prepare", "explain", "offer", "plant",
    "charge", "ground", "west", "picture", "hard", "front",
    "lie", "modern", "dark", "surface", "rule", "regard",
    "dance", "peace", "observe", "future", "wall", "farm",
    "claim", "firm", "operation", "further", "pressure",
    "property", "morning", "amount", "top", "outside",
    "accept", "achieve", "admit", "advise", "affect", "allow", "announce",
    "apologize", "approve", "argue", "arrange", "arrest", "attend", "avoid", "bake", "beg", "behave", 
    "borrow", "breathe", "calculate", "celebrate", "complain", "confirm", "connect", 
    "contribute", "convince", "criticize", "deliver", "depend", "design", "deserve", 
    "develop", "disagree", "discover", "doubt", "encourage", "entertain", "establish", 
    "evaluate", "examine", "exist", "expand", "expect", "explain", "explore", "express", 
    "forgive", "handle", "hesitate", "identify", "ignore", "imagine", "impress", "improve", 
    "insist", "introduce", "invest", "invite", "joke", "judge", "lend", "maintain", "manufacture", 
    "measure", "mention", "notice", "observe", "obtain", "organize", "permit", "persuade", 
    "postpone", "predict", "pretend", "prevent", "protect", "realize", "recommend", 
    "recover", "reduce", "reflect", "refuse", "regret", "relax", "remind", "rescue", 
    "retire", "satisfy", "scream", "select", "separate", "shout", "shrink", "signal", 
    "sneeze", "solve", "struggle", "succeed", "suggest", "support", "surround", "suspect", 
    "translate", "whisper", "worry", 
    "ability", "accident", "achievement", "advantage", "adventure", "agreement", 
    "ambition", "analysis", "anger", "apartment", "appearance", "appointment", 
    "arrival", "assistance", "atmosphere", "attraction", "authority", "background", 
    "barrier", "benefit", "budget", "celebration", "ceremony", "challenge", "characteristic", 
    "circumstance", "colleague", "combination", "competition", "conclusion", "condition", 
    "consequence", "construction", "criticism", "curiosity", "customer", "decision", 
    "description", "determination", "device", "difficulty", "direction", "disaster", 
    "discovery", "discussion", "education", "election", "employment", "energy", 
    "environment", "equipment", "evidence", "experience", "experiment", "expression", 
    "failure", "familiarity", "feature", "foundation", "friendship", "function", 
    "generation", "goal", "growth", "guidance", "hospitality", "imagination", "importance", 
    "impression", "independence", "influence", "initiative", "inspiration", "instruction", 
    "intelligence", "intention", "interaction", "investment", "leadership", "lifestyle", 
    "limitation", "literature", "management", "marketing", "medication", "motivation", 
    "necessity", "negotiation", "obligation", "opportunity", "organization", "participant", 
    "participation", "partnership", "perception", "performance", "permission", "phenomenon", 
    "philosophy", "population", "possession", "possibility", "preparation", "presentation", 
    "priority", "procedure", "productivity", "profession", "progress", "promotion", 
    "property", "proportion", "prospect", "protection", "qualification", "recognition", 
    "recommendation", "reputation", "requirement", "resource", "responsibility", "retirement", 
    "satisfaction", "sensitivity", "significance", "solution", "strategy", "structure", 
    "suggestion", "supervision", "survival", "technology", "tendency", "tradition", 
    "transformation", "transportation", "variation", "venture", "violence", "welfare",
    "abundant", "accurate", "active", "adaptable", "adorable", "adventurous", 
    "aggressive", "alert", "amazing", "ambitious", "amused", "appreciative", 
    "authentic", "balanced", "beneficial", "brave", "brilliant", "calm", "carefree", 
    "charismatic", "cheerful", "clever", "collaborative", "comfortable", "committed", 
    "compassionate", "competitive", "confident", "conscientious", "considerate", 
    "consistent", "constructive", "cooperative", "courageous", "creative", "curious", 
    "decisive", "dedicated", "delightful", "determined", "diligent", "diplomatic", 
    "disciplined", "dynamic", "eager", "efficient", "elegant", "eloquent", "energetic", 
    "enthusiastic", "ethical", "exceptional", "experienced", "expressive", "extraordinary", 
    "fascinating", "fearless", "flexible", "focused", "forgiving", "friendly", "fun-loving", 
    "generous", "gentle", "graceful", "grateful", "hardworking", "helpful", "honest", 
    "humble", "imaginative", "independent", "industrious", "ingenious", "insightful", 
    "inspiring", "intelligent", "intuitive", "inventive", "joyful", "kindhearted", 
    "knowledgeable", "lively", "logical", "lovable", "loyal", "meticulous", "motivated", 
    "observant", "optimistic", "organized", "outgoing", "passionate", "patient", 
    "perceptive", "persistent", "persuasive", "playful", "positive", "practical", 
    "proactive", "productive", "rational", "realistic", "reliable", "resilient", 
    "resourceful", "respected", "responsible", "self-assured", "self-disciplined", 
    "sensible", "sincere", "sociable", "strategic", "strong-willed", "supportive", 
    "thoughtful", "trustworthy", "understanding", "unique", "versatile", "vibrant", 
    "warmhearted", "witty", "wise"
    }
    
    # Extract words composed only of letters and convert them to lowercase
    words = re.findall(r'\b[a-z]+\b', text.lower())
    if not words:
        return 0.0, False
    common_count = sum(1 for word in words if word in common_words)
    ratio = common_count / len(words)
    return ratio, ratio >= threshold

# Test cases
if __name__ == "__main__":
    english_text = "FLUX.1 Redux [pro] is available in our API bfl.ml. In addition to the [dev] adapter, the API endpoint allows users to modify an image given a textual description. The feature is supported in our latest model FLUX1.1 [pro] Ultra, allowing for combining input images and text prompts to create high-quality 4-megapixel outputs with flexible aspect ratios."
    non_english_text = "これは英語ではなく、日本語の文章です。"
    print("English text is English:", is_english(english_text))  # Expected: True
    print("Non-English text is English:", is_english(non_english_text))  # Expected: False
