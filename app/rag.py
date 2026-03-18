import os
from dotenv import load_dotenv
from llama_index.core import Settings, Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage
from llama_index.llms.groq import Groq
from llama_index.core.tools import FunctionTool
import requests
from bs4 import BeautifulSoup

#Pulls the rules section from the official usa ultimate website
def scrape_rules():
    url = requests.get("https://usaultimate.org/rules/")
    soup = BeautifulSoup(url.text, "html.parser")
    text = soup.find("div", id="rules-of-ultimate").get_text(strip=True, separator="\n")
    return text

load_dotenv()
api_key = os.getenv('GROQ_API_KEY')
model = "llama-3.3-70b-versatile"

Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.llm = Groq(model=model, api_key=api_key)

#where to store the vectors
STORAGE = "../storage"


if os.path.exists(STORAGE): #if we already stored the vectors
    storage_context = StorageContext.from_defaults(persist_dir=STORAGE)
    print("loading indexes from storage...")
    index = load_index_from_storage(storage_context)
else: #if we haven't stored them yet, build them
    documents = SimpleDirectoryReader("../documents").load_data()
    web_rules = Document(text=scrape_rules(), metadata={"source":"https://usaultimate.org/rules/", "section":"Ultimate Rules"})
    documents.append(web_rules)
    index = VectorStoreIndex.from_documents(documents, show_progress=True)
    index.storage_context.persist(persist_dir=STORAGE)

query_engine = index.as_query_engine()

async def search_documents(query: str) -> str:
    response = await query_engine.aquery(query)
    return str(response)

search_tool = FunctionTool.from_defaults(
    fn=search_documents,
    name="search_documents",
    description="Search the MODS rules documents for information about Ultimate rules and amendments."
)


