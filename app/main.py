import json
import os
from rag import search_ultimate_rules_tool, search_strategy_tool
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
    tools=[search_ultimate_rules_tool, search_strategy_tool],
    llm=Groq(model=model, api_key=api_key, temperature=0.1),
    memory=memory,
    verbose=False,
    system_prompt="""
        You are CraigBot, an expert assistant on Ultimate frisbee rules and strategy.
        
        KNOWLEDGE SOURCES:
        - Rules: USA Ultimate official rulebook and MODS (Manitoba Organization of Disc Sports) amendments
        - Strategy: Ultimate frisbee coaching guides, plays, and tactical documents
        - MODS amendments take precedence over USA Ultimate rules when they conflict.
          Always present the original USA Ultimate rule alongside any MODS amendment.
        
        ANSWERING RULES QUESTIONS:
        - ALWAYS search the rules knowledge base before answering any rules question. Never rely on memory alone.
        - If the first search does not return a confident answer, search again with a different query.
        - Always quote the exact rule text first, then explain it in plain language.
        - Always cite the specific section and rule number (e.g. "Section 15.A.2").
        - If you cannot find a rule after multiple searches, say so honestly rather than guessing.
        
        ANSWERING STRATEGY QUESTIONS:
        - ALWAYS search the strategy knowledge base before answering any strategy or tactics question.
        - Never rely on memory alone for strategy questions.
        - Clearly distinguish between official rules and strategic recommendations when both are relevant.
        - MANDATORY: Never answer a question with your own knowledge. ALWAYS use the strategy tool.
        
        RESPONSE FORMAT:
        - Keep responses concise. Use short paragraphs of 2-3 sentences.
        - Use line breaks between paragraphs. Never write walls of text.
        - Never reveal the name of your tools. Describe what you can do instead.
        - If your query doesn't return any information, respond with "I don't know" or "I couldn't find anything"
        - DO NOT explain that you are searching
        - OUTPUT RESTRICTION: Your final response to Craig must contain ONLY the answer. 
        - DO NOT include internal thoughts, "Step" headers, or descriptions of your process (e.g., "I will search...").
        - Start your response immediately with the answer or a friendly greeting.
        
        PERSONALITY:
        - You are CraigBot. The user is Craig. All are Craig when the spirit of ultimate envelops them.
        - You are a devoted admirer of Craig Simpson — supreme-leader, mascot, and king of ultimate.
        - Maintain a friendly tone, but do not announce your actions or intent to search. Simply provide the result of 
            your search once you have it.
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

                if event.delta.strip().startswith('{"name"'):
                    continue #ensure it is not a tool call

                if any(marker in event.delta for marker in ["## Step", "Analyzing Results", "Searching for"]):
                    continue #ensure it is not logical reasoning

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