#!/bin/bash

# Start Streamlit on fixed internal port 8501
streamlit run app.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false &

# Start FastAPI on Render's assigned port
uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-10000}