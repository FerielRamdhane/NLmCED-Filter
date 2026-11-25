# NLmCED filter - single self-contained image (EUCAIM / local use)
#
# Same method as the shared XNAT runtime base (mcr-riciannoiselevel:r2024b), merged into ONE Dockerfile:
#   stage 1: MathWorks' runtime installer image installs ONLY the needed runtime products
#   stage 2: Ubuntu + MATLAB Runtime dependencies + that minimal runtime + Python + NLmCED
# No MATLAB installation is needed to build it. Build from the repository root:
#   docker build -f eucaim/Dockerfile -t nlmced:1.1.0 .

############################ Stage 1: minimal MATLAB Runtime ############################
FROM containers.mathworks.com/matlab-runtime-utils/matlab-runtime-installer:r2024b-update-5 AS installer

WORKDIR /opt/matlabruntime/unzippedinstaller

# Same runtime products as the shared XNAT base (mcr-riciannoiselevel:r2024b), on which NLmCED runs.
# (NLmCED's compiled package requires 8 runtime products; with only Numerics/Python/Signal
#  the runtime refuses to start: "The installed MATLAB Runtime is not compatible".)
RUN printf "destinationFolder=/tmp/matlabruntime/runtime\nagreeToLicense=yes\n" > installInputs.txt \
 && for p in "Core" "Graphics" "Non Interactive MATLAB" "Numerics" "Python" \
             "Image Processing Toolbox Addin" "Signal Processing Toolbox Addin" \
             "Curve Fitting Toolbox Addin" "Parallel Computing Toolbox Cluster Addin"; do \
      printf "product.MATLAB Runtime - %s\n" "$p" >> installInputs.txt; \
    done \
 && cat installInputs.txt \
 && ./install -bat true -inputFile ./installInputs.txt

############################ Stage 2: final image ############################
FROM ubuntu:24.04

LABEL maintainer="feriel.ramdhane@eurobioimaging.eu, ferielramdhane@cnr.it"
LABEL version="1.1.0"
LABEL description="NLmCED filter is a Python and Matlab tool for MRI data denoising."
LABEL image.source="https://github.com/FerielRamdhane/NLmCED-Filter"
LABEL image.version="1.1.0"

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
ENV PYTHONUNBUFFERED=1

# MATLAB Runtime dependencies (same list as Dockerfile.deps of the XNAT base)
RUN apt-get update && apt-get install --no-install-recommends -y \
        ca-certificates gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-tools \
        libasound2t64 libatomic1 libc6 libcairo-gobject2 libcairo2 libcap2 libcups2t64 libdrm2 \
        libfontconfig1 libfribidi0 libgbm1 libgdk-pixbuf-2.0-0 libgl1 libglib2.0-0t64 \
        libgstreamer-plugins-base1.0-0 libgstreamer1.0-0 libgtk-3-0t64 libgtk2.0-0t64 libice6 \
        libltdl7 libnettle8t64 libnspr4 libnss3 libpam0g libpango-1.0-0 libpangocairo-1.0-0 \
        libpangoft2-1.0-0 libpixman-1-0 libsndfile1 libtirpc3t64 libuuid1 libwayland-client0 \
        libxcomposite1 libxcursor1 libxdamage1 libxfixes3 libxfont2 libxft2 libxinerama1 \
        libxrandr2 libxt6t64 libxtst6 libxxf86vm1 procps zlib1g \
    && mkdir -p /usr/share/X11/xkb \
    && rm -rf /var/lib/apt/lists/*

# Python 3.10, same as the XNAT image (requirements pinned for 3.10)
RUN apt-get update && apt-get install --no-install-recommends -y software-properties-common gnupg curl \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install --no-install-recommends -y \
        python3.10 python3.10-venv python3.10-distutils libpython3.10 \
    && curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10 \
    && apt-get purge -y software-properties-common gnupg && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Minimal MATLAB Runtime from stage 1
COPY --from=installer /tmp/matlabruntime/runtime /opt/matlabruntime
RUN ln -sf /usr/lib/x86_64-linux-gnu/libstdc++.so.6 /opt/matlabruntime/R2024b/sys/os/glnxa64/libstdc++.so.6

ENV LD_LIBRARY_PATH=/opt/matlabruntime/R2024b/runtime/glnxa64:/opt/matlabruntime/R2024b/bin/glnxa64:/opt/matlabruntime/R2024b/sys/os/glnxa64:/opt/matlabruntime/R2024b/sys/opengl/lib/glnxa64:/opt/matlabruntime/R2024b/extern/bin/glnxa64
ENV MCR_CACHE_ROOT=/tmp/mcr_cache
ENV MPLCONFIGDIR=/tmp/matplotlib

COPY src/requirements.txt /tmp/
RUN python3.10 -m pip install --no-cache-dir -r /tmp/requirements.txt

COPY src/NLmCEDPkg_R2024b-24.2-py3-none-any.whl /tmp/
RUN python3.10 -m pip install --no-cache-dir /tmp/NLmCEDPkg_R2024b-24.2-py3-none-any.whl \
    && rm /tmp/*.whl /tmp/requirements.txt

# EUCAIM requires the container to run as UID/GID 2323
ARG USER_UID=2323
ARG USER_GID=2323
RUN groupadd -g $USER_GID eucaim && \
    useradd -r -u $USER_UID -g eucaim -d /home/eucaim -m -s /usr/sbin/nologin eucaim

WORKDIR /app
COPY src/nlmced.py eucaim/entrypoint.sh /app/
RUN sed -i "s/\r$//" /app/entrypoint.sh && chmod +x /app/entrypoint.sh

USER eucaim

ENTRYPOINT ["/app/entrypoint.sh"]
