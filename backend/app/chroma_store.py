import chromadb
from pathlib import Path
from app.models import Chunk
from app.database import DATA_DIR
client = chromadb.PersistentClient(path=str(DATA_DIR / "chroma_data"))
chroma_vector_store = client.get_or_create_collection(name="chroma_vector_store") #this wont create a collection if already present

def add_chunks_to_db(chunks:list[Chunk], item_id:int,title:str):
    #this function is used to add a list of chunks and its IDs
    
    ids, metadatas, documents = [], [],[]
    for chunk in chunks:
        ids.append(str(chunk.id))
        metadatas.append({
            "title": title, "ingested_id": chunk.ingested_item_id
        })
        documents.append(chunk.text)
    chroma_vector_store.add(
        ids=ids,
        documents= documents,
        metadatas= metadatas
    )