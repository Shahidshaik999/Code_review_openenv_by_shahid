FROM python:3.11-slim

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

COPY --chown=user requirements.txt .
COPY --chown=user pyproject.toml .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user app.py .
COPY --chown=user env.py .
COPY --chown=user models.py .
COPY --chown=user tasks.py .
COPY --chown=user openenv.yaml .
COPY --chown=user inference.py .
COPY --chown=user README.md .
COPY --chown=user server/ ./server/

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
