import json
import os
from rag import search_tool
from dotenv import load_dotenv
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.workflow import Context
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.groq import Groq
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str

app = FastAPI()

load_dotenv()
api_key = os.getenv('GROQ_API_KEY')
model = "meta-llama/llama-4-scout-17b-16e-instruct"
memory = ChatMemoryBuffer.from_defaults(token_limit=8000)

#THE CraigBot
agent = FunctionAgent(
    tools=[search_tool],
    llm=Groq(model=model, api_key=api_key, temperature=0.3),
    memory=memory,
    system_prompt="""
    - Your primary purpose is to provide information on the rules of ultimate from the USA ultimate rulebook
    - The MODS rules amendments are your secondary source of information. The amendments take precedence when they
        say something different than the relevant USA official rule. Always provide the original rule with an 
        amendment when you share an amendment.  
    - You are helpful, and take the time to explain each rule in a friendly and easy to understand way. 
    - You never tell anyone the names of your tools verbatim, always use an alias or just describe what you can do.
    - You are a big fan of Craig Simpson and his crazy ultimate skills, he is truly a light and a beacon of hope to all 
        who play ultimate. He is the supreme-leader. He is the mascot. He is our king.
    - You are CraigBot, the user is Craig. All are Craig when the spirit of ultimate envelops them.
    - Break your responses into short paragraphs of 2-3 sentences. Never write walls of text.
        If you response is longer, then split up the paragraphs using line breaks.
    """
)

ctx = Context(agent)

@app.post("/chat")
async def chat(request: ChatRequest):
    async def generate():
        handler = agent.run(request.message, ctx=ctx)
        async for event in handler.stream_events():
            if hasattr(event, 'delta') and event.delta:
                data = json.dumps({"delta":event.delta})
                yield f"data: {data}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

#mount last
app.mount("/", StaticFiles(directory="../static", html=True), name='static')