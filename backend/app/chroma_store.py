import chromadb
from pathlib import Path
from app.models import Chunk
from app.database import DATA_DIR
client = chromadb.PersistentClient(path=str(DATA_DIR / "chroma_data"))
chroma_vector_store = client.get_or_create_collection(name="chroma_vector_store") #this wont create a collection if already present

def add_chunks_to_db(chunks:list[Chunk]):
    #this function is used to add a list of chunks and its IDs
    
    chroma_vector_store.add(
        ids=[str(chunk.id) for chunk in chunks],
        documents= [chunk.text for chunk in chunks]
    )