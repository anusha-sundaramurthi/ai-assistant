# AI Travel Assistant – Project Instruction Guide

# Project Title
End-to-End AI Travel Assistant: Production-Ready RAG System using FastAPI and Qdrant

## 1. Project Overview

The AI Travel Assistant is a web-based application that helps users get travel-related information from uploaded PDF documents.
It uses AI to understand queries, retrieve relevant information, and generate accurate answers.


## 2. Technologies Used

* Frontend: Streamlit
* Backend: FastAPI
* AI Model: GPT-3.5-turbo
* Vector Database: Qdrant
* Embedding model:  text-embedding-ada-002  
* Memory: ConversationBufferMemory
* PDF parsing: PyMuPDF (fitz)
* Text splitting: RecursiveCharacterTextSplitter  


## 3. How the System Works

### Step-by-Step Flow:

1. User enters a query in the Streamlit app
2. The query is sent to the FastAPI backend
3. The system loads previous conversation using session_id
4. If the query is vague, it is rewritten using GPT-3.5
5. The query is converted into embeddings (vector form)
6. The retriever searches relevant data from Qdrant
7. The system filters the best matching chunks
8. The LLM generates the final answer using context
9. The response is saved in memory
10. The answer is displayed to the user


## 4. Installation and Setup

### Step 1. Project Setup

1. Extract the provided ZIP file
2. Open the project folder in terminal


### Step 2: Prerequisites — install these before anything else

1. Python version : Python 3.10 or 3.11 required. Check: 
```bash
python --version
```
2. Get OpenAI API key : Go to platform.openai.com → API Keys → Create new key. Copy and save it.

3. Get Qdrant Cloud credentials : Go to cloud.qdrant.io → Create cluster → Copy the URL and API key

### step 3: Local installation

Create virtual environment : 
```bash
python -m venv venv 
# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

```

### Step 4: Install dependencies

```bash
pip install -r requirements.txt
```
Installs required packages

### Step 5: Configure environment variables

Create a `.env` file and add:

```
OPENAI_API_KEY=your_api_key
QDRANT_HOST=your_host
QDRANT_API_KEY=your_key
COLLECTION_NAME=your_collection
EMBEDDING_MODEL=your_model
```

## 5. Running the Project

### Start Backend (FastAPI)

```bash
uvicorn main:app --reload
```
Backend now running at: http://localhost:8000

### Start Frontend (Streamlit)

```bash
streamlit run app.py
```

## 6. How to Use

1. Open the Streamlit interface
2. Click "Upload Guides" in sidebar 
3. Select PDF files
4. Click "Process Guides"
    • PDFs are stored permanently : You do NOT need to re-upload next time. The PDF is stored in Qdrant Cloud. Just open the app and ask questions
5. Select response language (default: English)
6. Type your question in the chat box
7. Ask follow-up questions
8. When AI says "no PDF guide"
If no matching PDF is uploaded, AI asks: "Would you like me to answer from general knowledge? (yes/no)"
    • Type yes → AI answers from GPT general knowledge
    • Type no → AI says upload a PDF for this destination

### Buttons in sidebar
🗑️ Clear Chat	-> Clears only the chat messages on screen. Your uploaded PDFs remain safely in Qdrant. Use this to start a fresh conversation
🗄️ Clear DB -> Deletes ALL uploaded PDFs from Qdrant permanently. Use only when you want a completely fresh start. You must re-upload PDFs after this
❓ How to Use -> Opens/closes the help panel in the main chat area
Uploading PDF guides
