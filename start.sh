#!/bin/bash

# Start Streamlit in background on port 8501 (internal only)
streamlit run app.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true &

# Start FastAPI on the public PORT (Render sets $PORT)
uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}