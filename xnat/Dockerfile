# NLmCED filter - XNAT Container Service version
# Built on the SHARED minimal MATLAB Runtime image used by all XNAT tools (IQA, CEST, ...).
# Same core code (src/nlmced.py) as the EUCAIM image + XNAT wrapper (upload + dashboard files).
#
# Build from the repository root:  docker build -f xnat/Dockerfile -t nlmced-xnat:1.1.0 .
ARG MCR_BASE=mcr-riciannoiselevel:r2024b
FROM ${MCR_BASE}

LABEL maintainer="feriel.ramdhane@eurobioimaging.eu, ferielramdhane@cnr.it"
LABEL version="1.1.0"
LABEL description="NLmCED filter - XNAT version (denoising + upload to XNAT + dashboard outputs)."
LABEL image.source="https://github.com/FerielRamdhane/NLmCED-Filter"
LABEL image.version="1.1.0"

ENV PYTHONUNBUFFERED=1
ENV MCR_CACHE_ROOT=/tmp/mcr_cache
ENV MPLCONFIGDIR=/tmp/matplotlib

# Python 3.10 (supported by NLmCEDPkg R2024b); the base also has the system Python 3.12
RUN apt-get update && apt-get install -y --no-install-recommends \
        software-properties-common gnupg curl \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
        python3.10 python3.10-venv python3.10-distutils libpython3.10 \
        libx11-6 libxrender1 libxext6 libbsd0 \
    && rm -rf /var/lib/apt/lists/* \
    && ldconfig

ENV LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/usr/lib/x86_64-linux-gnu"

RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10

COPY src/requirements.txt xnat/requirements-xnat.txt /tmp/
RUN python3.10 -m pip install --no-cache-dir -r /tmp/requirements.txt -r /tmp/requirements-xnat.txt

COPY src/NLmCEDPkg_R2024b-24.2-py3-none-any.whl /tmp/
RUN python3.10 -m pip install --no-cache-dir /tmp/NLmCEDPkg_R2024b-24.2-py3-none-any.whl \
    && rm /tmp/*.whl /tmp/*.txt

WORKDIR /app
COPY src/nlmced.py xnat/nlmced_xnat.py xnat/command.json /app/

# Runs as root, like the v1.0 XNAT image: the Container Service mounts are owned by
# the XNAT (tomcat) user. To run unprivileged: USER <uid from `id tomcat` on the server>

CMD ["python3.10", "/app/nlmced_xnat.py"]
