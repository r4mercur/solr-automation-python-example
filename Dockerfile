
FROM python:3.12-bookworm

# Install any additional dependencies
RUN apt-get update && apt-get install -y \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /workspace

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set environment variables if needed
ENV PYTHONUNBUFFERED=1

# Run the automatation & make sure the right values in .env are configured
CMD [ "python", "solr" ]