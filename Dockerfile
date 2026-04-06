FROM --platform=$BUILDPLATFORM debian:13

LABEL version="1.0" maintainer="vsc55@cerebelum.net" description="Docker Ombi Data Base Migration Tools"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        # Dependencias base
        python3 python3-pip git libicu-dev python3-venv \
        # Dependencias para compilar mysqlclient y soporte MariaDB/MySQL
        libmariadb-dev pkg-config gcc default-libmysqlclient-dev build-essential \
    && apt-get clean autoclean \
    && apt-get autoremove --yes \
    && rm -rf /var/lib/{apt,dpkg,cache,log}/

# Copy rootfs first (less likely to change)
COPY --chown=root:root /rootfs /

# Copy scripts and requirements
COPY --chown=root:root ["requirements.txt", "ombi_sqlite2mysql.py", "ombi_sqlite2mysql_multi.py", "/opt/ombi_sqlite_mysql/"]
RUN chmod +x /opt/ombi_sqlite_mysql/*.py /opt/ombi_sqlite_mysql/*.sh /entrypoint.sh

WORKDIR /opt/ombi_sqlite_mysql

# Create a virtual environment in the working directory
RUN python3 -m venv venv

# Install Python dependencies
RUN venv/bin/pip install --no-cache-dir --upgrade pip \
    && venv/bin/pip install --no-cache-dir -r requirements.txt

ENV PATH="/opt/ombi_sqlite_mysql/venv/bin:$PATH"

ENV HTTP_PORT=5000

ENV MYSQL_HOST="" \
    MYSQL_PORT="3306" \
    MYSQL_DB="Ombi" \
    MYSQL_USER="ombi" \
    MYSQL_PASSWD="" \
    MYSQL_ROOT_USER="" \
    MYSQL_ROOT_PASSWORD=""

# Default command: use entrypoint script
CMD ["/entrypoint.sh"]

VOLUME ["/config"]