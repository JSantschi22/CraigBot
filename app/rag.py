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
def table_extractor(table):
    rows = table.find_all("tr")

    lines = []
    for row in rows:
        cells = row.find_all(["td", "th"])
        line = " | ".join(cell.get_text(strip=True) for cell in cells)
        lines.append(line)

    table_text = "\n".join(lines)

    return table_text

def url_scraper():

    url = requests.get("https://usaultimate.org/rules/")
    soup = BeautifulSoup(url.text, "html.parser")

    main_rules = soup.find_all("ul", class_="main-rules")
    web_documents = []

    for mainSection in main_rules:
        sections = mainSection.find_all("li", recursive=False)
        for section in sections:
            section_name = section.find("a").get_text(strip=True) + " " + section.find("a").next_sibling.strip()
            rules = ""
            print(section_name)
            if "Appendix A:" in section_name:
                print("inside appendix A")
                rules = """
                The ultimate frisbee field consists of a Central Zone and two End Zones.
    
                Overall field dimensions:
                - Total length: 110 yd / 100 m (70 yd central zone + two 20 yd end zones)
                - Total width: 40 yd / 37 m
                - Perimeter line is 5 yd / 4.5 m outside the goal lines on each end, and 3 yd outside the sidelines
                
                End Zones:
                - Each end zone is 20 yd / 18 m deep
                - Brick marks are located 10 yd / 9 m from the goal line inside each end zone
                
                Central Zone:
                - 70 yd / 64 m long
                - Brick marks are located 20 yd / 18 m from each goal line, and at the midfield point
                - The midfield central mark is at 35 yd / 32 m from each goal line
                
                Field Lines:
                - Perimeter Line: the outermost boundary line (dashed)
                - Goal Line: the line separating the end zone from the central zone (solid)
                - Team Line: designates the team area along the sideline
                - Equipment Line: designates where equipment can be placed
                """
            else:
                if section.find("div"):
                    divs = section.find_all("div")
                    for div in divs:
                        rules = rules + div.get_text(strip=True)
                if section.find("table"):
                    tables = section.find_all("table")
                    for table in tables:
                        rules = rules + table_extractor(table)
                if section.find("ul"):
                    uls = section.find_all("ul")
                    for ul in uls:
                        rules = rules + ul.get_text(strip=True, separator="\n")

            doc = Document(text=rules, metadata={"source":"https://usaultimate.org/rules/", "section":section_name})
            documents.append(doc)

    return web_documents

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
    documents.extend(url_scraper())
    print("building indexes...")
    index = VectorStoreIndex.from_documents(documents, show_progress=True)
    index.storage_context.persist(persist_dir=STORAGE)

query_engine = index.as_query_engine()

async def search_documents(query: str) -> str:
    response = await query_engine.aquery(query)
    return str(response)

search_tool = FunctionTool.from_defaults(
    fn=search_documents,
    name="search_documents",
    description="Search through the USA ultimate rules for specific rules, then compare to the MODS amendments for any"
                "Manitoba or league specific amendments to the requested rule"
)


