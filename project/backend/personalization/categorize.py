"""Expense auto-categorisation from the description (merchant/keyword dictionary)."""
import re

from . import CATEGORIES

# Known merchants/brands: strong signal.
MERCHANTS = {
    "food": ["zomato", "swiggy", "dominos", "domino", "pizza hut", "mcdonalds", "mcd", "kfc",
             "burger king", "subway", "starbucks", "chaayos", "haldiram", "blinkit", "zepto",
             "instamart", "bigbasket", "dmart", "d mart", "eatsure", "faasos", "box8", "dunzo"],
    "transport": ["uber", "ola", "rapido", "metro", "irctc", "redbus", "namma yatri", "yulu",
                  "indigo", "air india", "akasa", "spicejet", "fastag", "bmtc", "best bus", "dtc"],
    "rent": ["nestaway", "zolo", "stanza", "colive", "nobroker"],
    "entertainment": ["netflix", "spotify", "prime video", "amazon prime", "hotstar", "jiocinema",
                      "jio cinema", "sonyliv", "zee5", "youtube premium", "bookmyshow", "pvr",
                      "inox", "steam", "playstation", "district", "paytm insider"],
    "utilities": ["jio", "airtel", "vodafone", "vi recharge", "bsnl", "act fibernet", "tata play",
                  "bescom", "tneb", "msedcl", "adani electricity", "tata power", "indane", "hp gas",
                  "bharat gas", "mahanagar gas"],
    "other": ["amazon", "flipkart", "myntra", "meesho", "ajio", "nykaa", "decathlon"],
}

# Generic words: weaker signal.
KEYWORDS = {
    "food": ["food", "lunch", "dinner", "breakfast", "snack", "snacks", "canteen", "mess", "tiffin",
             "restaurant", "cafe", "coffee", "tea", "chai", "grocery", "groceries", "vegetables",
             "fruits", "milk", "biryani", "pizza", "burger", "dhaba", "maggi", "juice", "bakery"],
    "transport": ["cab", "taxi", "auto", "rickshaw", "bus", "train", "flight", "petrol", "diesel",
                  "fuel", "parking", "toll", "travel", "commute", "ride", "bike"],
    "rent": ["rent", "pg", "hostel", "room", "flat", "landlord", "deposit", "accommodation",
             "lease", "maintenance"],
    "entertainment": ["movie", "movies", "cinema", "concert", "party", "game", "games", "gaming",
                      "subscription", "ott", "outing", "club", "bowling", "trip", "fest"],
    "utilities": ["electricity", "electric", "power", "water", "gas", "wifi", "wi fi", "internet",
                  "broadband", "recharge", "mobile", "phone", "bill", "postpaid", "prepaid",
                  "lpg", "cylinder", "dth"],
    "other": ["clothes", "shopping", "books", "stationery", "medicine", "pharmacy", "doctor",
              "gift", "laundry", "haircut", "salon", "fees", "course"],
}

MERCHANT_WEIGHT = 2.0
KEYWORD_WEIGHT = 1.0


def normalize(text):
    """Lowercase, strip punctuation/digits, collapse spaces."""
    text = (text or "").lower().replace("'", "").replace("&", " and ")
    text = re.sub(r"[^a-z]+", " ", text)
    return " ".join(text.split())


def _contains(padded, term):
    return f" {term} " in padded


def suggest_category(description, llm_fallback=None):
    """Guess the category for an expense description.

    Keyword/merchant match first; `llm_fallback(description)` is only called when
    nothing matches and must return one of CATEGORIES (anything else is ignored).
    """
    text = normalize(description)
    if text:
        padded = f" {text} "
        scores = {}
        best_merchant = set()
        for cat in CATEGORIES:
            s = 0.0
            for term in MERCHANTS.get(cat, []):
                if _contains(padded, term):
                    s += MERCHANT_WEIGHT
                    best_merchant.add(cat)
            for term in KEYWORDS.get(cat, []):
                if _contains(padded, term):
                    s += KEYWORD_WEIGHT
            if s:
                scores[cat] = s
        if scores:
            # Ties resolved by CATEGORIES order (dict insertion order + stable max).
            cat = max(scores, key=lambda c: scores[c])
            total = sum(scores.values())
            share = scores[cat] / total
            base = 0.9 if cat in best_merchant else 0.75
            confidence = round(base * (0.6 + 0.4 * share), 2)
            return {"category": cat, "confidence": confidence, "method": "keyword"}

    if llm_fallback is not None and text:
        try:
            guess = llm_fallback(description)
        except Exception:
            guess = None
        guess = normalize(guess) if isinstance(guess, str) else ""
        if guess in CATEGORIES:
            return {"category": guess, "confidence": 0.6, "method": "llm"}

    return {"category": "other", "confidence": 0.2, "method": "default"}
