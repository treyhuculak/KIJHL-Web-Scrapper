# The API, as Cloud Run wants it.
#
# The backend only. The frontend is static files and belongs on a CDN in front
# of this, which is also what keeps a cold start from delaying the first paint —
# see the README. Nothing here builds or serves JavaScript.
#
# The same image is both things we run: the server by default, and the nightly
# ingest by overriding the command with `python -m app.ingest --recent`. One
# image means the job and the service can never disagree about how to read the
# feed.

FROM python:3.14-slim

# Unbuffered above all: Cloud Logging reads stdout, and block-buffered output
# means a container that dies takes its last words with it.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

# Dependencies first, so editing the app doesn't reinstall them. psycopg is
# asked for as [binary], so there is no libpq to apt-get and no compiler needed.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Nothing here needs to be root, so nothing here is.
RUN useradd --create-home --uid 10001 zebra
USER zebra

# Cloud Run picks the port and passes it in; 8080 is its default and ours.
ENV PORT=8080
EXPOSE 8080

# Shell form for ${PORT}, `exec` so uvicorn is PID 1 and hears the SIGTERM that
# Cloud Run sends it — otherwise shutdown is a ten-second wait and a kill.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
