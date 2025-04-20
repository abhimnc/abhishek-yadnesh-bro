# Use NVIDIA CUDA base image with cuDNN and Python
FROM nvidia/cuda:11.7.1-cudnn8-runtime-ubuntu20.04

# Set working directory
WORKDIR /app

# Install system packages
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Use pip3 explicitly
RUN pip3 install --upgrade pip

# Copy requirements
COPY backend/requirements.txt .

# Install base Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Clone and install Real-ESRGAN and dependencies
RUN git clone https://github.com/xinntao/Real-ESRGAN.git /app/Real-ESRGAN && \
    pip3 install basicsr facexlib gfpgan && \
    pip3 install -r /app/Real-ESRGAN/requirements.txt && \
    cd /app/Real-ESRGAN && python3 setup.py develop

# Copy app source code
COPY backend/ .

# Expose Flask port
EXPOSE 5000

# Start app
CMD ["python3", "app.py"]
