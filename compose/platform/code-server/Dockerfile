FROM codercom/code-server:latest@sha256:bfe06d7f36273d84a61d6bf2f9656b9f612f9c5c6fbb45ba5e19a29b42ded6f4

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
