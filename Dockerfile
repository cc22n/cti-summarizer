FROM python:3.12-slim

WORKDIR /app

# System deps:
#   libpq-dev + gcc  -> psycopg (non-binary fallback)
#   g++ build-essential -> Prophet/CmdStan compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH=/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install CmdStan 2.33.1 into the exact path prophet 1.1.6 expects:
#   <prophet_package>/stan_model/cmdstan-2.33.1/
RUN python -c "import cmdstanpy, prophet, os; stan_dir = os.path.join(os.path.dirname(prophet.__file__), 'stan_model'); cmdstanpy.install_cmdstan(version='2.33.1', dir=stan_dir, overwrite=True)" 2>&1 | tail -5

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=8).raise_for_status()"

ENTRYPOINT ["sh", "entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
