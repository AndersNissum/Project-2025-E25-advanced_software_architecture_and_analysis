# Use a base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt . 

# Install required packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire source code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Set Python path to include the app directory
ENV PYTHONPATH=/app

# Command to run the application
CMD ["python", "-m", "simulationEngine.app"]