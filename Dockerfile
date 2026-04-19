FROM python:3.10-slim

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY backend/ ./backend/

# Build indexes at image build time
# Embedding API keys are needed here — pass as build args
ARG EMBEDDING_KEY
ARG EMBEDDING_URL
ENV EMBEDDING_KEY=$EMBEDDING_KEY
ENV EMBEDDING_URL=$EMBEDDING_URL

RUN PYTHONPATH=/app python -m backend.data_pipeline.indexers

EXPOSE 8000

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
