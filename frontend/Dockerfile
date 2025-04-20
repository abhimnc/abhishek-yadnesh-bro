# Use the official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements (just Streamlit and requests for now)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app into the container
COPY streamlit_ui1.py .

# Expose the port Streamlit will run on
EXPOSE 8501

# Run the Streamlit app
CMD ["streamlit", "run", "streamlit_ui1.py", "--server.port=8501", "--server.address=0.0.0.0", "-server.enableCORS=false"]
