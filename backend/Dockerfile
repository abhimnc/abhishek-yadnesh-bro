FROM nvidia/cuda:11.7.1-cudnn8-runtime-ubuntu20.04

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (required for tokenizers)
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install Python core libraries first
RUN pip3 install --upgrade "pip<24.1" setuptools wheel

# Preinstall numpy and pandas explicitly to avoid metadata build errors
RUN pip3 install numpy pandas

# Copy and install main requirements
COPY backend/requirements.txt .
RUN pip3 install --prefer-binary --no-cache-dir -r requirements.txt

# Clone and install Real-ESRGAN and dependencies
RUN git clone https://github.com/xinntao/Real-ESRGAN.git /app/Real-ESRGAN && \
    pip3 install basicsr facexlib gfpgan && \
    pip3 install -r /app/Real-ESRGAN/requirements.txt && \
    cd /app/Real-ESRGAN && python3 setup.py develop

# Copy app source
COPY . .

EXPOSE 5000

CMD ["python3", "app.py"]
