# ── Base Image ─────────────────────────────────────────────────────────────────
# We start from an official Python image — like a clean OS with Python installed
FROM python:3.10-slim

# ── Working Directory ──────────────────────────────────────────────────────────
# All commands from here run inside /app folder inside the container
WORKDIR /app

# ── Copy Requirements ──────────────────────────────────────────────────────────
# Copy requirements first — Docker caches this layer
# If requirements don't change, Docker skips reinstalling packages (faster builds)
COPY requirements.txt .

# ── Install Dependencies ───────────────────────────────────────────────────────
RUN pip install --no-cache-dir --timeout=120 --retries=5 -r requirements.txt

# ── Copy Code ──────────────────────────────────────────────────────────────────
# Copy entire project into container
COPY . .

# ── Expose Port ────────────────────────────────────────────────────────────────
# Tell Docker this container listens on port 8000
EXPOSE 8000

# ── Start Command ──────────────────────────────────────────────────────────────
# Command that runs when container starts
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]