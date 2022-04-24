#!/bin/bash

docker build --squash  --network=host -t ombi_sqlite_mysql .
