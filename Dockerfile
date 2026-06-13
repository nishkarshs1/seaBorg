FROM python:3.11-slim

# Install system dependencies required for netCDF4 and HDF5
RUN apt-get update && apt-get install -y \
    build-essential \
    libhdf5-dev \
    libnetcdf-dev \
    netcdf-bin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install CPU-only PyTorch to drastically reduce Docker image size (from 2.8GB down to ~800MB)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.2.2+cpu --extra-index-url https://download.pytorch.org/whl/cpu

# Install the rest of the requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose ports for backend and frontend
EXPOSE 8001
EXPOSE 8501

# Start FastAPI backend using the Python entrypoint to safely handle the PORT
CMD ["python", "start_server.py"]