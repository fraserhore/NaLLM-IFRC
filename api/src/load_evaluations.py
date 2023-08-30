import requests
from requests.auth import HTTPBasicAuth
import json
from PyPDF2 import PdfReader
from io import BytesIO
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
import openai
import os
import tiktoken
from neo4j import GraphDatabase

openai.api_key  = os.environ.get('OPENAI_API_KEY')

# Connect to Neo4j database
host = os.environ.get("NEO4J_URL")
user = os.environ.get("NEO4J_USER", "neo4j")
password = os.environ.get("NEO4J_PASS")
database = os.environ.get("NEO4J_DATABASE", "neo4j")
driver = GraphDatabase.driver(host, auth=(user, password))

# Get the number of tokens for a text string
def num_tokens_from_string(string: str, encoding_name = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

# Create chunk nodes for text
def create_chunk_nodes(parent_url, title, author, page_num, num_pages, summary, text):

    # We need to split the text that we read into smaller chunks so that during information retreival we don't hit the token size limits. 
    text_splitter = CharacterTextSplitter(        
        separator = "\n",
        chunk_size = 1000,
        chunk_overlap  = 0,
        length_function = len,
    )

    chunks = text_splitter.split_text(text)
    num_chunks = len(chunks)

    # Delete any existing child chunk nodes and use UNWIND to iterate through each chunk and create a new child chunk node
    driver.execute_query("""
        MATCH (parent:WebResource {url: $parent_url})
        OPTIONAL MATCH (parent)-[r:HAS_CHUNK]->(existing_chunk:Chunk)
        DETACH DELETE existing_chunk
        WITH parent
        UNWIND range(0, size($chunks)-1) as chunk_index
        CREATE (new_chunk:Chunk {uuid: randomUUID(), text: $chunks[chunk_index], chars: size($chunks[chunk_index]), url: $url, title: $title, author: $author, page: $page_num, pages: $num_pages, chunk: chunk_index+1, chunks: $num_chunks, updated: datetime()})
        CREATE (parent)-[r:HAS_CHUNK]->(new_chunk)
        """,
        parent_url=parent_url,
        url=parent_url,
        chunks=chunks,
        title=title,
        author=author,
        page_num=page_num,
        num_pages=num_pages,
        num_chunks=num_chunks,
        database_="neo4j"
    )

    print(f"{num_chunks} chunks created")

# Define the URL and authentication credentials
url = os.environ.get("GOAPI_URL")
username = os.environ.get("GOAPI_USER")
password = os.environ.get("GOAPI_PASS")

# Make a GET request to the URL with basic authentication
response = requests.get(url, auth=HTTPBasicAuth(username, password))

# Parse the JSON data from the response
data = json.loads(response.content)

for item in data:
    #print('EVA_Hidden:', item['EVA_Hidden'])
    #print('EVA_Id:', item['EVA_Id'])
    #print('EVA_IsManagementResponse:', item['EVA_IsManagementResponse'])
    #print('EVA_MOD_Id:', item['EVA_MOD_Id'])
    #print('EVA_author:', item['EVA_author'])
    #print('EVA_commissionedBY:', item['EVA_commissionedBY'])
    #print('EVA_date:', item['EVA_date'])
    #print('EVA_document:', item['EVA_document'])
    #print('EVA_title:', item['EVA_title'])
    #print()

    errors = []
    url = item['EVA_document']
    doc_response = requests.get(url)

    # Read the content of the PDF file into a BytesIO object
    pdf_file = BytesIO(doc_response.content)

    try:
        # Create a PDF reader object
        pdf_reader = PdfReader(pdf_file)

        metadata = pdf_reader.metadata
        pages = pdf_reader.pages
        num_pages = len(pages)

        print(num_pages)
        #print(metadata)

        title = metadata.title if metadata is not None and metadata.title is not None else ""
        author = metadata.author if metadata is not None and metadata.author is not None else ""
        creation_date = metadata.creation_date if metadata is not None and metadata.creation_date is not None else ""
        modification_date = metadata.modification_date if metadata is not None and metadata.modification_date is not None else ""

        # Extract text from PDF
        text = ""
        for page in range(num_pages):
            text += pages[page].extract_text()

        chars = len(text)
        words = len(text.split())
        tokens = num_tokens_from_string(text)
        summary = "" # get_summary(text, math.floor(words/3))

        # Create a "WebResource" node
        driver.execute_query("""
            MATCH (parent:WebResource) WHERE parent.url = $parent_url
            SET parent.processed_urls = $processed_urls, parent.processed_urls_count = $processed_urls_count, parent.urls_to_process = $urls_to_process, parent.urls_to_process = $urls_to_process, parent.updated = datetime()
            MERGE (p:WebResource:Pdf {url: $url})
                ON CREATE SET p.uuid = randomUUID()
                SET p.canonical_url = $canonical_url, p.hostname = $hostname, p.contenttype = $content_type, p.title = $title, p.author = $author, p.summary = $summary, p.text = $text, p.words = $words, p.chars = $chars, p.tokens = $tokens, p.pages = $numpages, p.creation_date = $creation_date, p.modification_date = $modification_date, p.updated = datetime()
            MERGE (parent)-[r:LINKS_TO]->(p)
            RETURN id(p) as id
            """,
            parent_url=parent_url,
            processed_urls=processed_urls,
            processed_urls_count=len(processed_urls),
            urls_to_process=urls_to_process,
            urls_to_process_count=len(urls_to_process),
            url=url,
            canonical_url=canonical_url,
            hostname=hostname,
            content_type=content_type,
            title=title,
            author=author,
            summary=summary,
            text=text,
            words=words,
            chars=chars,
            tokens=tokens,
            numpages=num_pages,
            creation_date=creation_date,
            modification_date=modification_date
        )
        
        print(f"PDF WebResource node created with url: {url}, title: {title} and {chars} characters of text")

        # For each page, split the text into chunks and create a child node for each chunk
        for page in range(num_pages):
            # Split the page text into chunks
            create_chunk_nodes(url, title, author, page, num_pages, pages[page].extract_text())

    except Exception as e:
        errors.append(e)
        print('Error:', e)
        print('URL:', url)

# Count the total number of items
total_items = len(data)

# Print the total number of items
print('Total items:', total_items)

# Print the total number of errors
print('Total errors:', len(errors))

# Print the error messages
for error in errors:
    print(error)
