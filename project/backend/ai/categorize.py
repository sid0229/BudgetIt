"""Expense auto-categorisation: personalization's keyword matcher first,
Gemini as a fallback only when no keyword matches and the LLM is configured.
"""
from ai import llm, prompts

CATEGORIES = ['food', 'transport', 'rent', 'entertainment', 'utilities', 'other']


def llm_category(description):
    """Return one of CATEGORIES or None. Never raises."""
    if not llm.is_configured() or not (description or '').strip():
        return None
    try:
        result = llm.generate(
            [{'role': 'user', 'text': prompts.CATEGORIZE_PROMPT % description.strip()[:200]}],
            temperature=0.0,
        )
        word = (result.get('text') or '').strip().lower().strip('."\' ')
        for cat in CATEGORIES:
            if word == cat or word.startswith(cat):
                return cat
    except Exception:
        pass
    return None


def categorize(description):
    description = (description or '').strip()
    try:
        from personalization.categorize import suggest_category
        return suggest_category(description, llm_fallback=llm_category)
    except Exception:
        cat = llm_category(description)
        if cat:
            return {'category': cat, 'confidence': 0.6, 'method': 'llm'}
        return {'category': 'other', 'confidence': 0.0, 'method': 'default'}
