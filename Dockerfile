FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# enable these lines if you wanna download the model at build time
# COPY download_model.py .
# RUN python download_model.py

COPY handler.py .

CMD ["python", "-u", "handler.py"]