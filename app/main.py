import os
import asyncio
from rag import search_tool
from dotenv import load_dotenv
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.workflow import Context
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.groq import Groq
import textwrap

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
    - You are a big fan of Craig Simpson and his crazy ultimate skills, he is truly a light and a beacon of hope to all who play ultimate
    """
)

ctx = Context(agent)

async def main():
    #We're online:
    print("CraigBot is online. Type exit to quit.")

    #Chat loop
    while True:
        user_input = input("User: ").strip()
        if user_input.lower() in ["bye", 'exit', 'tata', 'quit']:
            break
        if not user_input:
            print("No prompt received. Try again.")
            continue

        response = await agent.run(user_input, ctx=ctx)

        response = textwrap.fill(str(response), width=80)

        print(f"CraigBot: {response}")


if __name__ == "__main__":
    asyncio.run(main())