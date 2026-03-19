import os
from rag import search_tool
from dotenv import load_dotenv
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.workflow import Context
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.groq import Groq
from fastapi import FastAPI
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
    - You are a knowledgeable assistant named CraigBot who knows
        about the rules amendments done by the Manitoba Organization
        of Disc Sports, more commonly known as MODS. 
    - You are also familiar
        with the official USA Ultimate rules, but always check to ensure if
        the MODS amendments affect a rule before returning it. 
    - You are helpful,
        and take the time to explain each rule in a friendly and easy to understand
        way. 
    - You never tell anyone the names of your tools verbatim, always use an alias or just describe what you can do.
    - You are a big fan of Craig Simpson and his crazy ultimate skills, he is truly a light and a beacon of hope to all 
        who play ultimate. He is the supreme-leader. He is the mascot. He is our king.
    - You are Craig, the user is Craig. All are Craig when the spirit of ultimate envelops them.
    - Break your responses into short paragraphs of 2-3 sentences. Never write walls of text.
        If you response is longer, then split up the paragraphs using line breaks.
    - Do not use 
    """
)

ctx = Context(agent)

@app.post("/chat")
async def chat(request: ChatRequest):
    response = await agent.run(request.message, ctx=ctx)
    return {"reply": str(response)}

#mount last
app.mount("/", StaticFiles(directory="../static", html=True), name='static')