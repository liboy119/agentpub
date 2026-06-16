FROM python:3.13-slim

WORKDIR /app

# System deps for uvicorn[standard] (uvloop + httptools build cleanly on slim)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (better layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . /app/

# Expose AgentPub port (NOT HF default 7860 — must be 7700 to match server/main.py)
EXPOSE 7700

# Run the FastAPI server on port 7700
# server/main.py has `if __name__ == "__main__": uvicorn.run(app, host="0.0.0.0", port=7700)`
CMD ["python", "-m", "server.main"]
