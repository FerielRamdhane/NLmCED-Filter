# Use MATLAB Runtime R2024b as base image
FROM python:3.10-bullseye

# Maintainer information
LABEL maintainer="feriel.ramdhane@eurobioimaging.eu , ferielramdhane@cnr.it"
LABEL version="1.0"
LABEL description="NLmCED filter is a Python and Matlab tool for data denoising."
LABEL image.source="https://github.com/FerielRamdhane/NLmCED-Filter"
LABEL image.version="latest"


# Set environment variables
ENV PYTHONUNBUFFERED=1
# Set defaults for build arguments
ARG USER_UID=2323
ARG USER_GID=2323


ENV LD_LIBRARY_PATH=/opt/mcr/R2024b/runtime/glnxa64:/opt/mcr/R2024b/bin/glnxa64:/opt/mcr/R2024b/sys/os/glnxa64:/opt/mcr/R2024b/extern/bin/glnxa64:/usr/lib/x86_64-linux-gnu
ENV XAPPLRESDIR=/etc/X11/app-defaults

# Create non-root user and group, and prevent login
RUN groupadd -g $USER_GID eucaim && \
useradd -r -u $USER_GID -g eucaim -d /home/eucaim -m -s /usr/sbin/nologin eucaim

# Install dependencies required for MATLAB Runtime and Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    unzip wget x11-utils xauth \
    libx11-dev libxrender-dev libxext-dev libbsd0 libglib2.0-0 libgl1-mesa-glx \
    python3-tk build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Download and install MATLAB Runtime R2024b
RUN mkdir /mcr-install && cd /mcr-install && \
    wget --no-check-certificate -q https://ssd.mathworks.com/supportfiles/downloads/R2024b/Release/2/deployment_files/installer/complete/glnxa64/MATLAB_Runtime_R2024b_Update_2_glnxa64.zip && \
    unzip -q MATLAB_Runtime_R2024b_Update_2_glnxa64.zip && \
    chmod +x install && \
    ./install -destinationFolder /opt/mcr -agreeToLicense yes -mode silent && \
    rm -rf /mcr-install MATLAB_Runtime_R2024b_Update_2_glnxa64.zip

COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

COPY NLmCEDPkg_R2024b-24.2-py3-none-any.whl /tmp/
RUN pip3 install /tmp/NLmCEDPkg_R2024b-24.2-py3-none-any.whl

WORKDIR /app

COPY nlmced.py /app/

# CMD ["python", "./nlmced.py"]

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]



