from fastapi import UploadFile
import fitz
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from src.embeddings import get_embeddings
from src.vectorstores import get_qdrant_client, init_qdrant

async def ingest_pdf(file: UploadFile, collection_name: str):
    print(f"📄 Processing PDF: {file.filename} into collection: {collection_name}")
    content = await file.read()

    docs = []
    pdf  = fitz.open(stream=content, filetype="pdf")
    page_count = len(pdf)
    print(f"📑 {page_count} pages found")

    try:
        for page_num in range(page_count):
            text = pdf[page_num].get_text()
            docs.append(Document(
                page_content=text,
                metadata={"page": page_num, "source": file.filename}
            ))
    finally:
        pdf.close()

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks   = splitter.split_documents(docs)
    print(f"📚 {len(chunks)} chunks created")

    texts      = [chunk.page_content for chunk in chunks]
    embeddings = get_embeddings(texts)

    # Make sure collection exists
    init_qdrant(collection_name)
    client = get_qdrant_client()

    payloads = [{"text": chunk.page_content, **chunk.metadata} for chunk in chunks]
    client.upload_collection(
        collection_name=collection_name,
        vectors=embeddings,
        payload=payloads,
    )
    print(f"✅ Uploaded {len(chunks)} chunks to '{collection_name}'")