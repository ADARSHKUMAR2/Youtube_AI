# Use a lightweight version of Python 3.12
FROM python:3.12-slim

# Copy the uv installer from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory inside the container
WORKDIR /app

# Copy all your files into the container
COPY . /app

# Use uv to install all dependencies from your pyproject.toml
RUN uv sync --frozen

# Tell the container to use the virtual environment created by uv
ENV PATH="/app/.venv/bin:$PATH"