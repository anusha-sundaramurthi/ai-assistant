#!/bin/bash

# Start FastAPI FIRST on Render's assigned port
uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-10000} &

# Wait for FastAPI to bind the port
sleep 5

# Start Streamlit on internal port 8501
streamlit run app.py \
  --server.port 8501 \
  --server.address 127.0.0.1 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false