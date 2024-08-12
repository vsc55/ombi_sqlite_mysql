FROM --platform=$BUILDPLATFORM debian:12.6
# FROM debian:12.6

LABEL version="1.0" maintainer="vsc55@cerebelum.net" description="Docker Ombi Data Base Migration Tools"

RUN \
    apt-get update && \
    apt-get install -y python3 python3-pip libmariadb-dev git libicu-dev python3-venv pkg-config && \
    apt-get clean autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/{apt,dpkg,cache,log}/

# Create a virtual environment
RUN python3 -m venv /opt/venv

# Activate the virtual environment and install Python packages
RUN /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir mysqlclient packaging

# Ensure the virtual environment is activated for subsequent commands
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /
COPY --chown=root:root /rootfs /

WORKDIR /opt/ombi_sqlite_mysql
COPY --chown=root:root ["ombi_sqlite2mysql.py", "ombi_sqlite2mysql_multi.py", "./"]

# Fix, hub.docker.com auto builds
RUN chmod +x /opt/ombi_sqlite_mysql/*.py /opt/ombi_sqlite_mysql/*.sh

ENV HTTP_PORT=5000