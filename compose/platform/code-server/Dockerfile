FROM codercom/code-server:latest@sha256:992796b850b8b7ec6f7393b8dd2295840a65cf5071981990ff41ef52dd566c43

USER root

RUN if ! command -v curl >/dev/null 2>&1 || ! dpkg-query -W -f='${Status}' ca-certificates 2>/dev/null | grep -q "install ok installed"; then \
      apt-get update && \
      DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends curl ca-certificates && \
      rm -rf /var/lib/apt/lists/*; \
    fi

RUN mkdir -p /home/coder/.local/bin /home/coder/.codex && \
    chown -R 1000:1000 /home/coder/.local /home/coder/.codex

ENV HOME=/home/coder
ENV PATH=/home/coder/.local/bin:${PATH}

USER coder

RUN curl -fsSL https://chatgpt.com/codex/install.sh | sh

WORKDIR /home/coder/projects
