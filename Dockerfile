FROM --platform=$BUILDPLATFORM debian:11.3
# FROM debian:11.3

LABEL version="1.0" maintainer="vsc55@cerebelum.net" description="Docker Ombi Data Base Migration Tools"

RUN \
	apt-get update && \
	apt-get install -y python3 python3-pip libmariadb-dev git libicu-dev && \
	pip3 install --no-cache-dir --upgrade pip && \
	pip3 install --no-cache-dir mysqlclient packaging && \
	apt-get clean autoclean && \
	apt-get autoremove --yes && \
	rm -rf /var/lib/{apt,dpkg,cache,log}/

WORKDIR /
COPY --chown=root:root /rootfs /

WORKDIR /opt/ombi_sqlite_mysql
COPY --chown=root:root ["ombi_sqlite2mysql.py", "ombi_sqlite2mysql_multi.py", "./"]

#Fix, hub.docker.com auto buils
RUN \
	chmod +x /opt/ombi_sqlite_mysql/*.{py,sh}

ENV HTTP_PORT=5000

VOLUME ["/config", "/opt/ombi"]
EXPOSE ${HTTP_PORT}/tcp
