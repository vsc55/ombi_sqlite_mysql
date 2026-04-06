#!/bin/sh
set -e

# Check required environment variables
if [ -z "$MYSQL_HOST" ] || [ -z "$MYSQL_USER" ] || [ -z "$MYSQL_DB" ]; then
  echo "[ERROR] You must set MYSQL_HOST, MYSQL_USER, and MYSQL_DB environment variables."
  exit 1
fi

# Use root credentials for DB/user creation if provided, else use app user
MYSQL_ADMIN_USER="${MYSQL_ROOT_USER:-$MYSQL_USER}"
MYSQL_ADMIN_PASSWD="${MYSQL_ROOT_PASSWORD:-$MYSQL_PASSWD}"

# Try to create the database and user if needed
if command -v mysql >/dev/null 2>&1; then
  echo "[INFO] Checking if database $MYSQL_DB exists on $MYSQL_HOST..."
  if ! mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_ADMIN_USER" -p"$MYSQL_ADMIN_PASSWD" -e "CREATE DATABASE IF NOT EXISTS \\\`$MYSQL_DB\\\` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;"; then
    echo "[ERROR] Could not create database '$MYSQL_DB'. Check admin user permissions or connection."
    exit 2
  fi
  # Check if user exists, create and grant if not
  USER_EXISTS=$(mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_ADMIN_USER" -p"$MYSQL_ADMIN_PASSWD" -sse "SELECT EXISTS(SELECT 1 FROM mysql.user WHERE user = '$MYSQL_USER')")
  if [ "$USER_EXISTS" != "1" ]; then
    echo "[INFO] Creating user $MYSQL_USER and granting privileges on $MYSQL_DB..."
    if ! mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_ADMIN_USER" -p"$MYSQL_ADMIN_PASSWD" -e "CREATE USER '$MYSQL_USER'@'%' IDENTIFIED BY '$MYSQL_PASSWD'; GRANT ALL PRIVILEGES ON \\\`$MYSQL_DB\\\`.* TO '$MYSQL_USER'@'%'; FLUSH PRIVILEGES;"; then
      echo "[ERROR] Could not create user '$MYSQL_USER' or grant privileges."
      exit 3
    fi
  else
    echo "[INFO] User $MYSQL_USER already exists. Skipping user creation."
  fi
else
  echo "[WARN] The mysql client is not installed in the image. Assuming the database and user already exist."
fi

# Run migration
exec python3 ombi_sqlite2mysql.py \
    --config /config \
    --host "$MYSQL_HOST" \
    --port "$MYSQL_PORT" \
    --db "$MYSQL_DB" \
    --user "$MYSQL_USER" \
    --passwd "$MYSQL_PASSWD"
