FROM python:3.13-slim

LABEL org.opencontainers.image.title="urihandler v8 demo tool"
LABEL org.opencontainers.image.source="https://github.com/tellmesh/urihandler"
LABEL io.tellmesh.urihandler.manifest="urihandler.manifest.json"

WORKDIR /app
COPY urihandler.manifest.json /usr/share/urihandler/manifest.json
CMD ["python3", "-V"]
