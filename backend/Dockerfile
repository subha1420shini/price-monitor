# Base image: lightweight Python 3.12
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first (Docker caches this layer if requirements.txt
# doesn't change, so rebuilds are faster)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY . .

# The port FastAPI/uvicorn will run on inside the container
EXPOSE 8000

# Command to run when the container starts
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]