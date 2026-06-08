from fastapi import UploadFile
import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from src.config import COLLECTION_NAME
from src.embeddings import get_embeddings
from src.vectorstores import get_qdrant_client

async def ingest_pdf(file: UploadFile):
    print(f"📄 Processing PDF file: {file.filename}")
    content = await file.read()
    
    # Load PDF directly from memory
    docs = []
    pdf = fitz.open(stream=content, filetype="pdf")
    page_count = len(pdf)
    print(f"📑 PDF loaded successfully. Found {page_count} pages")
    
    try:
        for page_num in range(page_count):
            page = pdf[page_num]
            text = page.get_text()
            docs.append(Document(
                page_content=text,
                metadata={"page": page_num, "source": file.filename}
            ))
    finally:
        pdf.close()
    
    print("✂️ Splitting document into chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = splitter.split_documents(docs)
    print(f"📚 Created {len(chunks)} text chunks")
    print(chunks)
    
    print("🧮 Generating embeddings...")
    texts = [chunk.page_content for chunk in chunks]
    embeddings = get_embeddings(texts)

     # Get the Qdrant client
    client = get_qdrant_client()

    # Prepare payloads
    payloads = [{"text": chunk.page_content, **chunk.metadata} for chunk in chunks]

    # Upload points
    print(f"⬆️ Uploading {len(chunks)} documents to collection '{COLLECTION_NAME}'...")
    client.upload_collection(
        collection_name=COLLECTION_NAME,
        vectors=embeddings,
        payload=payloads,
    )
    print(f"✅ Upload complete! Added {len(chunks)} chunks from {page_count} pages")
