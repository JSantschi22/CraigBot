import os
from dotenv import load_dotenv
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import (VectorStoreIndex,
                              SimpleDirectoryReader,
                              StorageContext,
                              load_index_from_storage,
                              get_response_synthesizer,
                              Settings,
                              Document,
                              PromptTemplate)
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

def _load_rules_index(storage):
    """Loads the rules index from the storage"""
    storage_context = StorageContext.from_defaults(persist_dir=storage)
    print("loading rules index from storage...")
    _index = load_index_from_storage(storage_context)
    return _index

def _load_strategy_index(storage):
    """Loads the strategy index from the storage"""
    storage_context = StorageContext.from_defaults(persist_dir=storage)
    print("loading strategy index from storage...")
    _index = load_index_from_storage(storage_context)
    return _index

def _build_rules_index(storage):
    """Builds the rules vector indexes"""
    #Set the chunking settings
    Settings.chunk_size = 512
    Settings.chunk_overlap = 100

    #Pull data from the documents folder and webpage
    documents = SimpleDirectoryReader("../documents/rules").load_data()
    documents.extend(_usa_ultimate_rules_scraper())

    print("building rules index...")

    #build and store the actual indexes
    _index = VectorStoreIndex.from_documents(documents, show_progress=True)
    _index.storage_context.persist(persist_dir=storage)
    return _index

def _build_strategy_index(storage):
    """Builds the strategy vector index"""
    #Set the chunking settings
    Settings.chunk_size = 256
    Settings.chunk_overlap = 60

    #read the documents from the directory
    documents = SimpleDirectoryReader("../documents/strategy").load_data()

    print("building strategy index...")

    #build and store the indexes
    _index = VectorStoreIndex.from_documents(documents, show_progress=True)
    _index.storage_context.persist(persist_dir=storage)
    return _index

#grab the bot info
load_dotenv()
api_key = os.getenv('GROQ_API_KEY')
model = "llama-3.3-70b-versatile"

#Sets Llama to use huggingface and groq instead of the default
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.llm = Groq(model=model, api_key=api_key)

#where to store the vectors
RULES_STORAGE = "../storage/rules"
STRATEGY_STORAGE = "../storage/strategy"

#Load or build the rules index
if os.path.exists(RULES_STORAGE): #if we already stored the vectors
    rules_index = _load_rules_index(RULES_STORAGE)
else: #if we haven't stored them yet, build them
    rules_index = _build_rules_index(RULES_STORAGE)

#Load or build the strategy index
if os.path.exists(STRATEGY_STORAGE):
    strategy_index = _load_strategy_index(STRATEGY_STORAGE)
else:
    strategy_index = _build_strategy_index(STRATEGY_STORAGE)

#Create the reranking postprocessor
postprocessor = SentenceTransformerRerank(top_n=3)

#Get the response synthesizer
response_synthesizer = get_response_synthesizer(response_mode="compact")

#Create the retrievers from the indexes
rules_retriever = VectorIndexRetriever(index=rules_index, similarity_top_k=3, postprocessor=postprocessor)
strategy_retriever = VectorIndexRetriever(index=strategy_index, similarity_top_k=3, postprocessor=postprocessor)

#Assemble the query functions
rules_vector_query_engine = RetrieverQueryEngine(
    retriever=rules_retriever,
    response_synthesizer=response_synthesizer
)
strategy_vectory_query_engine = RetrieverQueryEngine(
    retriever=strategy_retriever,
    response_synthesizer=response_synthesizer
)

#Create the prompt templates
rules_template = PromptTemplate("""You are CraigBot, an Ultimate frisbee rules expert.

The following are relevant excerpts from the USA Ultimate rulebook and MODS amendments:
------------------------------
{context_str}
------------------------------

Using only the excerpts above, answer the following question.
Follow these guidelines:
- Quote the specific rule text verbatim first, then explain it in plain language.
- Always cite the section and rule number (e.g. "Section 15.A.2").
- If a MODS amendment applies, present the original rule first then the amendment.
- Be as brief as possible. Only elaborate if the rule genuinely requires explanation.
- If the answer is not in the excerpts, say so honestly rather than guessing.

Question: {query_str}
Answer:""")
strategy_template = PromptTemplate("""You are CraigBot, an Ultimate frisbee strategy and coaching expert.

The following are relevant excerpts from the strategy and plays documents:
------------------------------
{context_str}
------------------------------

Using only the excerpts above, answer the following question.
Follow these guidelines:
- Get to the point quickly. Lead with the direct answer before any context.
- Use bullet points for plays, formations, or step-by-step concepts.
- Be as brief as possible. Only elaborate if the concept genuinely requires it.
- Clearly distinguish between strategic recommendations and official rules.
- If the answer is not in the excerpts, say so honestly rather than guessing.

Question: {query_str}
Answer:""")
rules_vector_query_engine.update_prompts({"response_synthesizer:text_qa_template": rules_template})
strategy_vectory_query_engine.update_prompts({"response_synthesizer:text_qa_template": strategy_template})

#the base functions that searches our indexes
async def search_rules_documents(query: str) -> str:
    response = rules_vector_query_engine.query(query)
    print("Search Rules Documents Tool: EXECUTED")
    print(response)
    return str(response)
async def search_strategy_documents(query: str) -> str:
    response = strategy_vectory_query_engine.query(query)
    print("Search Strategy Documents Tool: Executed")
    print(response)
    return str(response)

#the tool wrappers for the query functions
search_ultimate_rules_tool = FunctionTool.from_defaults(
    fn=search_rules_documents,
    name="search_ultimate_rules",
    description="""Search the Ultimate frisbee rules knowledge base. 
    Use this tool for ANY question about Ultimate rules, gameplay, definitions, 
    violations, fouls, scoring, field dimensions, or MODS amendments. 
    Always use this tool before answering rules questions — never rely on general knowledge alone.
    Pass a specific, detailed query for best results (e.g. 'stall count rules section 15' 
    rather than just 'stalling')."""
)

search_strategy_tool = FunctionTool.from_defaults(
    fn=search_strategy_documents,
    name="search_ultimate_strategy",
    description="""Search the Ultimate frisbee strategy and plays knowledge base.
    Use this tool for ANY question about offensive or defensive strategies, plays, 
    formations, cutting patterns, handler resets, end zone plays, force positions, 
    or general team tactics and coaching concepts.
    Do NOT use this tool for questions about official rules or regulations — use the rules tool for those.
    Pass specific descriptive queries for best results (e.g. 'vertical stack cutting patterns' 
    rather than just 'offense')."""
)
#reload