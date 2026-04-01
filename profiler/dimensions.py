"""
Each dimension has keywords and a weight.
Add a new dimension = add a new key here. The engine picks it up automatically.
"""

PROFILE_DIMENSIONS: dict[str, dict] = {
    "political": {
        "keywords": [
            "government", "election", "president", "vote", "democrat",
            "republican", "congress", "parliament", "policy", "legislation",
            "political", "liberal", "conservative", "campaign", "protest",
            "activist", "rights", "freedom", "democracy", "authoritarian",
            "corruption", "reform", "senator", "minister",
        ],
    },
    "education": {
        "keywords": [
            "study", "university", "school", "research", "academic",
            "professor", "lecture", "exam", "degree", "thesis",
            "scholarship", "course", "homework", "science", "mathematics",
            "literature", "curriculum", "student", "teacher", "learning",
            "tutorial", "textbook", "phd", "graduate",
        ],
    },
    "spirituality": {
        "keywords": [
            "god", "prayer", "church", "mosque", "temple", "faith",
            "spiritual", "meditation", "soul", "divine", "holy",
            "religion", "worship", "scripture", "bible", "quran",
            "torah", "karma", "enlightenment", "blessing", "heaven",
            "mindfulness", "yoga", "buddhism",
        ],
    },
    "aggression": {
        "keywords": [
            "kill", "fight", "destroy", "hate", "anger", "rage",
            "threat", "punch", "attack", "hurt", "violent", "revenge",
            "beat", "smash", "crush", "war", "enemy", "hostile",
            "furious", "strangle",
        ],
    },
    "financial": {
        "keywords": [
            "money", "bank", "invest", "stock", "crypto", "bitcoin",
            "trading", "payment", "salary", "budget", "loan", "mortgage",
            "profit", "revenue", "tax", "insurance", "finance", "economy",
            "market", "portfolio", "dividend",
        ],
    },
    "social": {
        "keywords": [
            "friend", "family", "party", "wedding", "birthday", "hangout",
            "dinner", "group", "community", "relationship", "dating",
            "love", "together", "meet", "social", "gathering", "reunion",
            "colleague", "neighbor",
        ],
    },
    "emotional_positive": {
        "keywords": [
            "happy", "joy", "love", "excited", "grateful", "wonderful",
            "amazing", "great", "fantastic", "beautiful", "hope", "blessed",
            "thankful", "proud", "celebrate", "laugh", "smile", "fun",
            "cheerful", "optimistic",
        ],
    },
    "emotional_negative": {
        "keywords": [
            "sad", "depressed", "lonely", "anxious", "worried", "afraid",
            "scared", "hopeless", "miserable", "crying", "suffering",
            "pain", "lost", "empty", "numb", "overwhelmed", "stressed",
            "frustrated", "grief", "despair",
        ],
    },
    "criminal": {
        "keywords": [
            "drug", "cocaine", "heroin", "meth", "steal", "rob", "hack",
            "forge", "counterfeit", "smuggle", "trafficking", "illegal",
            "launder", "bribe", "blackmail", "extort", "fraud", "cartel",
        ],
    },
    "sexual": {
        "keywords": [
            "sex", "nude", "explicit", "porn", "naked", "intimate",
            "hookup", "erotic", "fetish", "adult content", "onlyfans",
        ],
    },
    "technical": {
        "keywords": [
            "code", "programming", "software", "algorithm", "database",
            "server", "api", "python", "javascript", "engineering",
            "machine learning", "artificial intelligence", "computer",
            "network", "developer", "debug", "deploy", "git", "framework",
            "linux", "docker",
        ],
    },
    "health": {
        "keywords": [
            "doctor", "hospital", "medicine", "health", "workout", "gym",
            "diet", "nutrition", "exercise", "therapy", "mental health",
            "wellness", "vitamin", "symptom", "diagnosis", "treatment",
            "surgery", "prescription",
        ],
    },
}