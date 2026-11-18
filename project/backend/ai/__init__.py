"""BudgetIt AI layer: Gemini wrapper, tool calling, memory, chat and insights.

Every entry point degrades gracefully when GEMINI_API_KEY is missing or the
LLM call fails, so the Flask routes never 500 because the model is down.
"""
