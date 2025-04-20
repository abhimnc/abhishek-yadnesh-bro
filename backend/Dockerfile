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

# Install Real-ESRGAN
RUN git clone https://github.com/xinntao/Real-ESRGAN.git /Real-ESRGAN && \
    pip install basicsr facexlib gfpgan && \
    pip install -r /Real-ESRGAN/requirements.txt && \
    cd /Real-ESRGAN && python setup.py develop



# Copy application
COPY . .
RUN pip install flask
# After installing basicsr and torchvision
RUN sed -i 's/from torchvision\.transforms\.functional_tensor/from torchvision.transforms.functional/' \
    /usr/local/lib/python3.10/site-packages/basicsr/data/degradations.py

RUN rm -rf /root/.cache/whisper/*
EXPOSE 5000
CMD ["python", "app.py"]
