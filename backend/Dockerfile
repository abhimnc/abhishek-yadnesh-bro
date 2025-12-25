FROM python:3.10-slim

WORKDIR /app
# Install system packages and GPU drivers (via nvidia repo)
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    curl \
    ffmpeg \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# (Optional) Install Rust for tokenizers
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade "pip<24.1" setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .
RUN pip install flask

RUN rm -rf /root/.cache/whisper/*
EXPOSE 5151
CMD ["python", "app.py"]
