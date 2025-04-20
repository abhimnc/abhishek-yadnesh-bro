FROM nvidia/cuda:11.7.1-cudnn8-runtime-ubuntu20.04

# Set working directory
WORKDIR /app

# Install OS-level dependencies (Python, Git, Rust, etc.)
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (for tokenizers)
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Upgrade pip
RUN pip3 install --upgrade pip

# Copy requirements and install them
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Clone and install Real-ESRGAN
RUN git clone https://github.com/xinntao/Real-ESRGAN.git /app/Real-ESRGAN && \
    pip3 install basicsr facexlib gfpgan && \
    pip3 install -r /app/Real-ESRGAN/requirements.txt && \
    cd /app/Real-ESRGAN && python3 setup.py develop

# Copy backend source code
COPY . .

# Expose Flask port
EXPOSE 5000

# Start the app
CMD ["python3", "app.py"]
