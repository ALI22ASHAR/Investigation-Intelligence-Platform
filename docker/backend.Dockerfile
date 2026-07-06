# docker/backend.Dockerfile
#
# Purpose: build an image that contains everything needed to run the
# FastAPI backend -- the right Python version, system tools (Tesseract,
# Poppler), Python packages, and your actual code.
#
# Every line below runs ONCE at build time (when you build the image),
# not every time the container starts -- this is why installing
# packages here is fast to START later: it's already done.

# FROM: start from an existing, official base image instead of building
# an OS from scratch. "python:3.12-slim" is a minimal Debian Linux with
# Python 3.12 preinstalled -- "slim" means smaller size (fewer
# preinstalled extras) than the default python:3.12 image.
FROM python:3.12-slim

# WORKDIR: sets the "current directory" for every instruction that
# follows, INSIDE the image/container. Similar to running `cd /app`
# once, and every later COPY/RUN happens relative to it.
WORKDIR /app

# RUN: executes a command DURING the build (not when the container
# starts later). Here we use Debian's package manager (apt-get) to
# install Tesseract and Poppler -- the same tools you manually
# installed on Windows, but this time Docker installs them
# automatically, identically, every time this image is built, on any
# machine. This is EXACTLY the class of problem (a tool being in a
# different place on different machines) that Docker eliminates.
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*
# "rm -rf /var/lib/apt/lists/*" cleans up temporary package-list files
# afterward -- a common Docker convention to keep the final image
# smaller, since those files are only needed during installation.

# Copy ONLY the dependency files first (not all your code yet).
# Same caching-optimization reasoning as before.
COPY requirements-docker.txt .

# Install CPU-only PyTorch FIRST, from PyTorch's own CPU-specific index,
# instead of the default PyPI index. On Linux, the DEFAULT torch package
# pulls in the full CUDA/GPU toolkit (multiple GB of nvidia-* packages)
# even when there's no GPU to use -- irrelevant here, since Ollama
# (running on your host machine, not in this container) does all the
# actual LLM inference. This one line avoids downloading several
# unnecessary gigabytes.
RUN pip install --no-cache-dir --timeout 120 torch --index-url https://download.pytorch.org/whl/cpu

# Now install everything else. Since torch is already installed and
# satisfies what sentence-transformers/etc. need, pip won't re-download
# the huge default GPU build.
RUN pip install --no-cache-dir --timeout 120 -r requirements-docker.txt

# NOW copy the actual project code -- every folder the backend needs,
# since main.py reaches into rag/, embeddings/, database/, preprocessing/.
COPY backend/ ./backend/
COPY rag/ ./rag/
COPY embeddings/ ./embeddings/
COPY database/ ./database/
COPY preprocessing/ ./preprocessing/
COPY ingestion/ ./ingestion/

# EXPOSE documents (for humans/tools reading this file) which port the
# app listens on inside the container. It does NOT actually publish the
# port to your host machine -- that happens in docker-compose.yml later.
EXPOSE 8000

# CMD: the command that runs when a CONTAINER STARTS (unlike RUN, which
# only runs during the build). This is the actual "start the server"
# step -- equivalent to you typing `python main.py`, but run
# automatically whenever this container starts.
WORKDIR /app/backend
CMD ["python", "main.py"]
