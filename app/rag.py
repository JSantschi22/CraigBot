import os
from dotenv import load_dotenv
from llama_index.core import Settings, Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage
from llama_index.llms.groq import Groq
from llama_index.core.tools import FunctionTool
import requests
from bs4 import BeautifulSoup

def _table_extractor(table):
    """A helper function that formats HTML table elements into bot readable strings"""
    rows = table.find_all("tr") #grab all rows

    #Scrape the text from each row and separate the cells with |
    lines = []
    for row in rows:
        cells = row.find_all(["td", "th"])
        line = " | ".join(cell.get_text(strip=True) for cell in cells)
        lines.append(line)

    #join them into a single string with each row on its own line
    table_text = "\n".join(lines)

    return table_text


def _usa_ultimate_rules_scraper():
    """Scrapes all the documentation from 'usaultimate.org' into Documents for vector indexing"""
    url = requests.get("https://usaultimate.org/rules/")
    soup = BeautifulSoup(url.text, "html.parser")

    main_rules = soup.find_all("ul", class_="main-rules") #grab the rules sections only
    rule_documents = [] #the list of rules Documents

    for mainSection in main_rules: #for each rules section
        sections = mainSection.find_all("li", recursive=False) #Find only the first layer of list items
        for section in sections: #For each section of the rules (e.g. SECTION #: SECTION NAME)

            #strips out the section name for the metadata
            section_name = section.find("a").get_text(strip=True) + " " + section.find("a").next_sibling.strip()

            rules = ""

            #a section that contains only an image, so replaces that with a pre-generated description of it
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
                if section.find("div"): #find each div, if they exist, and add their content
                    divs = section.find_all("div")
                    for div in divs:
                        rules = rules + div.get_text(strip=True)
                if section.find("table"): #find each table, send them to get formatted, and add the string
                    tables = section.find_all("table")
                    for table in tables:
                        rules = rules + _table_extractor(table)
                if section.find("ul"): #find all the ul, strip the text, and add the content
                    uls = section.find_all("ul")
                    for ul in uls:
                        rules = rules + ul.get_text(strip=True, separator="\n")

            #Creates a new document for each rules section for better RAG performance
            doc = Document(text=rules, metadata={"source":"https://usaultimate.org/rules/", "section":section_name})
            rule_documents.append(doc)

    return rule_documents

def _load_indexes(storage):
    """Loads the indexes from the storage"""
    storage_context = StorageContext.from_defaults(persist_dir=storage)
    print("loading indexes from storage...")
    _index = load_index_from_storage(storage_context)
    return _index

def _build_indexes(storage):
    """Builds the vector indexes"""
    documents = SimpleDirectoryReader("../documents").load_data()
    documents.extend(_usa_ultimate_rules_scraper())
    print("building indexes...")
    _index = VectorStoreIndex.from_documents(documents, show_progress=True)
    _index.storage_context.persist(persist_dir=STORAGE)
    return _index

#grab the bot info
load_dotenv()
api_key = os.getenv('GROQ_API_KEY')
model = "llama-3.3-70b-versatile"

#Sets Llama to use huggingface and groq instead of the default
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.llm = Groq(model=model, api_key=api_key)

#where to store the vectors
STORAGE = "../storage"

if os.path.exists(STORAGE): #if we already stored the vectors
    index = _load_indexes(STORAGE)
else: #if we haven't stored them yet, build them
    index = _build_indexes(STORAGE)

#Create the query engine from the indexes
query_engine = index.as_query_engine()

#the base function that searches our indexes
async def search_documents(query: str) -> str:
    response = await query_engine.aquery(query)
    return str(response)

#the tool wrapper for the query function
search_tool = FunctionTool.from_defaults(
    fn=search_documents,
    name="search_documents",
    description="Searches through the indexes for information."
)