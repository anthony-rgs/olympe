FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app/artemis

# Install git to be able to clone the repository
RUN apt-get update && apt-get install -y git

# Clone the Artemis repository into the working directory
RUN git clone https://github.com/anthony-rgs/artemis.git .

# Copy the cloned code to the shared volume and keep the container running
CMD cp -r /app/artemis/* /code-artemis && sleep infinity
