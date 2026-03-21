import json
import os
from rag import search_tool
from dotenv import load_dotenv
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.workflow import Context
from llama_index.core.memory import Memory
from llama_index.llms.groq import Groq
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from utils import _load_session, _save_session, _get_history

#the blueprint for the frontend user message JSON
class ChatRequest(BaseModel):
    message: str
    session_id: str

#set the api
app = FastAPI()

#grab the model info
load_dotenv()
api_key = os.getenv('GROQ_API_KEY')
model = "meta-llama/llama-4-scout-17b-16e-instruct"
memory = Memory.from_defaults(token_limit=8000)

#THE CraigBot
agent = FunctionAgent(
    tools=[search_tool],
    llm=Groq(model=model, api_key=api_key, temperature=0.3),
    memory=memory,
    system_prompt="""
    - Your primary purpose is to provide information on the rules of ultimate from the USA ultimate rulebook
        and additional context from the MODS Amendments 
    - ALWAYS use your search tool when asked about ultimate or its rules to provide an answer.
        NEVER rely on memory alone when answering ultimate questions. 
        When possible, cite the section and rule you got your answer from.
        ALWAYS quote the relevant rule text before explaining it.
    - You are helpful, and take the time to explain each rule in a friendly and easy to understand way. 
    - You never tell anyone the names of your tools verbatim, always use an alias or just describe what you can do.
    - You are a big fan of Craig Simpson and his crazy ultimate skills, he is truly a light and a beacon of hope to all 
        who play ultimate. He is the supreme-leader. He is the mascot. He is our king.
    - You are CraigBot, the user is Craig. All are Craig when the spirit of ultimate envelops them.
    - Break your responses into short paragraphs of 2-3 sentences. Never write walls of text.
        If you response is longer, then split up the paragraphs using line breaks.
    """
)


#create the session memory
sessions = {}

@app.post("/chat")
async def _chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """The API POST for the main cbot conversation"""
    loaded = await _load_session(request.session_id, agent) #try to load the session
    session = loaded if loaded else { #if no session history then create new session
        "ctx" : Context(agent),
        "memory" : Memory.from_defaults(token_limit=8000)
    }
    async def generate(): #creates the content of the token stream
        handler = agent.run(request.message, ctx=session["ctx"], memory=session["memory"]) #send msg and get response stream
        async for event in handler.stream_events(): #for every token in response stream

            if hasattr(event, 'delta') and event.delta: #if it is a text token and the text is not empty

                if not event.delta.strip().startswith('{"name"'): #ensure its not a tool call

                    data = json.dumps({"delta":event.delta}) #serialize it into a JSON object
                    yield f"data: {data}\n\n" #send each back

        yield "data: [DONE]\n\n" #once the stream is complete send [DONE] to signify

    background_tasks.add_task(_save_session, request.session_id, session) #save the session after stream completes

    return StreamingResponse(generate(), media_type="text/event-stream") #send the tokens from generate, as a stream

@app.get("/history")
async def get_history(session_id: str):
    """The API GET method for a users message history"""
    history = _get_history(session_id)
    return {"history" : history}

#mount last
app.mount("/", StaticFiles(directory="../static", html=True), name='static')