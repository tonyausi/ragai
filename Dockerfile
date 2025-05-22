FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG USER_ID=10103
ARG GROUP_ID=10103

# Install system dependencies as root
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user/group
RUN groupadd -g ${GROUP_ID} ragai && \
    useradd -u ${USER_ID} -g ragai -m ragai_user

# Create directories and set ownership/permissions
RUN mkdir -p /ragaiapi/logs /ragaiapi/processed_files && \
    chown -R ragai_user:ragai /ragaiapi && \
    chmod -R 775 /ragaiapi/logs /ragaiapi/processed_files

# Install Python dependencies as root
WORKDIR /ragaiapi
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy app files with correct ownership
COPY --chown=ragai_user:ragai ./app ./app
COPY --chown=ragai_user:ragai . .

# Switch to non-root user
USER ragai_user

EXPOSE 10103
ENV PYTHONPATH "${PYTHONPATH}:/ragaiapi"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10103"]