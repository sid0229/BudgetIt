"""Thin wrapper over the google-genai SDK.

Callers pass a provider-neutral message list and get a plain dict back, which
keeps the rest of the ai package (and the tests) independent of SDK types.

Message dicts accepted by generate():
    {"role": "user",  "text": "..."}
    {"role": "model", "text": "..."}
    {"role": "model", "raw": <types.Content>}        # model turn returned by a previous call
    {"role": "tool",  "responses": [{"name", "response": dict, "id": str|None}]}

Return value of generate():
    {"text": str, "function_calls": [{"name", "args": dict, "id"}], "raw": <types.Content>|None}

Automatic function calling is always disabled: chat.py runs the tool loop
itself so it can inject the session user_id server-side.
"""
import os
import threading

DEFAULT_MODEL = 'gemini-3.5-flash-lite'

_client = None
_client_key = None
_client_lock = threading.Lock()


def is_configured():
    return bool(os.environ.get('GEMINI_API_KEY', '').strip())


def get_model():
    return os.environ.get('GEMINI_MODEL', '').strip() or DEFAULT_MODEL


def _get_client():
    global _client, _client_key
    key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not key:
        raise RuntimeError('GEMINI_API_KEY is not set')
    with _client_lock:
        if _client is None or _client_key != key:
            from google import genai
            _client = genai.Client(api_key=key)
            _client_key = key
    return _client


def _to_contents(messages):
    from google.genai import types

    contents = []
    for msg in messages:
        role = msg.get('role')
        if role == 'tool':
            parts = []
            for r in msg.get('responses', []):
                fr = types.FunctionResponse(
                    name=r['name'],
                    response=r.get('response') or {},
                    id=r.get('id'),
                )
                parts.append(types.Part(function_response=fr))
            contents.append(types.Content(role='user', parts=parts))
        elif msg.get('raw') is not None:
            # Keep the model turn intact (function calls + thought signatures).
            contents.append(msg['raw'])
        else:
            sdk_role = 'model' if role in ('model', 'bot', 'assistant') else 'user'
            contents.append(types.Content(role=sdk_role, parts=[types.Part.from_text(text=msg.get('text', ''))]))
    return contents


def build_function_declarations(declarations):
    """Convert plain dict declarations into SDK FunctionDeclaration objects."""
    from google.genai import types

    return [types.FunctionDeclaration(**d) for d in declarations]


def generate(messages, system_instruction=None, tools=None, response_schema=None,
             temperature=0.4, max_output_tokens=None, tool_mode=None, timeout_ms=30000):
    """Single model call. Raises on any error; callers must fall back.

    tools: list of plain dict function declarations (see ai.tools.TOOL_DECLARATIONS)
    response_schema: dict Schema -> forces application/json output
    tool_mode: None | "AUTO" | "NONE" (NONE = must answer in text)
    """
    from google.genai import types

    client = _get_client()

    config_kwargs = {
        'temperature': temperature,
        'automatic_function_calling': types.AutomaticFunctionCallingConfig(disable=True),
        'http_options': types.HttpOptions(timeout=timeout_ms),
    }
    if system_instruction:
        config_kwargs['system_instruction'] = system_instruction
    if max_output_tokens:
        config_kwargs['max_output_tokens'] = max_output_tokens
    if tools:
        config_kwargs['tools'] = [types.Tool(function_declarations=build_function_declarations(tools))]
        if tool_mode:
            config_kwargs['tool_config'] = types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode=tool_mode)
            )
    if response_schema is not None:
        config_kwargs['response_mime_type'] = 'application/json'
        config_kwargs['response_schema'] = response_schema

    response = client.models.generate_content(
        model=get_model(),
        contents=_to_contents(messages),
        config=types.GenerateContentConfig(**config_kwargs),
    )

    raw = None
    text_parts = []
    calls = []
    candidates = getattr(response, 'candidates', None) or []
    if candidates and candidates[0].content is not None:
        raw = candidates[0].content
        for part in raw.parts or []:
            if getattr(part, 'thought', None):
                continue
            if part.function_call is not None:
                calls.append({
                    'name': part.function_call.name,
                    'args': dict(part.function_call.args or {}),
                    'id': part.function_call.id,
                })
            elif part.text:
                text_parts.append(part.text)

    return {'text': ''.join(text_parts).strip(), 'function_calls': calls, 'raw': raw}
