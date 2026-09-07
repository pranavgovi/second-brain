**Purpose / Background Info:** While learning different concepts regarding AI/Software Engineering/Frontend / backend, I take notes in documents and bookmark them. I read articles, papers, blogs and save them. But during an interview / while re-collecting them, I often miss most of the scattered docs saved somewhere leading to wastage of time.

**Fix:** I decided to build an application where I can ingest various forms of notes (pdf/docs/text/urls) and a LLM can respond to my questions based on my notes.

I built a RAG pipeline which consists of Ingestion Layer, Preprocessing and Chunking Layer, Embedding Layer, LLM Q&A layer where context is retrieved from my previous notes.

INGESTION LAYER:
**Can ingest and process** 1. PDF with naive /embedded text - Pypdf
                       2. PDF with scanned text/images- Pymupdf (converts an image into a snapshot) + Pytessearct (that OCRs the snapshot)
                       3. Docx
                       4. URL - Network call will be made using httpx and reconstructs the dom tree using beautifulsoup

**Preprocessing Layer** - Where deterministic cleaning like white space removal, unicode removal, word breaks are removed, extra white lines are removed

**Chunking Layer** - Fixed chunking where the extracted text is chunked with a cap of 250 words per chunk

**Embedding Layer**- Used sentence transformers to embed the chunked layers, query

**Storage **- Since this is scoped to my personal notes, I used sqlite for storing ingested items and embeddings. Similarity search is done against all chunk embeddings. 
Once scalability feature we can add is vectordb that can do similarity search without a brute force approach

**LLM** = Used free model Ollama to answer the query based on retrieved chunks.

**Retrieval Layer** - When a user posts a query, it is converted into embeddings , then relevant embeddings are compared and retrieved.
This retrieved chunks is passed to the LLM as context to answer generate the notes

**Frontend Layer:** Vue js is used

Future TO-DOs

1. Current ingestion layer does not support handwritten images. Need Azure Doc Intetlligence to apply OCR on handwritten images
2. As input data grows, we need to switch from sqlite to vector db to store chunks and embeddings because manual cosine search will be inefficient
3. Chunking strategy can be focussed on dividing the extracted text based on layout ie headers, section ,subsection
