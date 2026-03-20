import json
from pathlib import Path
from llama_index.core.memory import Memory
from llama_index.core.workflow import Context
from llama_index.core.llms import ChatMessage, MessageRole

SESSIONS_DIR = Path("../sessions")
SESSIONS_DIR.mkdir(exist_ok=True)

def _save_session(session_id, session):
    """Saves the users session to a JSON file in the sessions folder"""
    path = SESSIONS_DIR / f"{session_id}.json"
    messages = session["memory"].get_all()
    history = [{"role": m.role.value, "content": m.content} for m in messages]
    with open(path, "w") as f:
        json.dump(history, f)

async def _load_session(session_id, agent):
    """Loads a session JSON from the sessions folder by session ID"""
    path = SESSIONS_DIR / f"{session_id}.json"
    if path.exists():
        with open(path, "r") as f:
            history = json.load(f)

        messages = [ChatMessage(role=MessageRole(m["role"]), content=m["content"]) for m in history]
        memory = Memory.from_defaults(token_limit=8000, session_id=session_id)
        memory.put_messages(messages)
        ctx = Context(agent)
        print(ctx.store)
        await ctx.store.set("memory", memory)
        return {"ctx": Context(agent), "memory": memory}
    return None

def _get_history(session_id):
    """Gets the message history of a users session by id"""
    path = SESSIONS_DIR / f"{session_id}.json"
    if path.exists():
        with open(path, "r") as f:
            history = json.load(f)
        if history:
            return history
    return None