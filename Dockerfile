FROM python:3.13-alpine
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY src/substrate.py src/fixtures.py src/conventional.py /opt/lab/
RUN mkdir /state && chown 65532:65532 /state
USER 65532:65532
WORKDIR /state
ENTRYPOINT ["/usr/bin/env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE=1", "python", "/opt/lab/substrate.py"]
