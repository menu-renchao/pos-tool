FROM python:3.11-slim

# Install nmap for network scanning
RUN apt-get update && apt-get install -y nmap && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads/mobile_devices

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
