# Migration procedure

## Create database and user in the server MySql/MariaDB
```mysql
CREATE DATABASE IF NOT EXISTS `Ombi` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE USER 'ombi'@'%' IDENTIFIED BY 'ombi';
GRANT ALL PRIVILEGES ON `Ombi`.* TO 'ombi'@'%' WITH GRANT OPTION;
```

## Create and prepare tables
1. Stop ombi
2. Create or Modify **database.json** to use mysql.
```json
{
  "OmbiDatabase": {
    "Type": "MySQL",
    "ConnectionString": "Server=IP-MYSQL;Port=3306;Database=Ombi;User=ombi;Password=ombi"
  },
  "SettingsDatabase": {
    "Type": "MySQL",
    "ConnectionString": "Server=IP-MYSQL;Port=3306;Database=Ombi;User=ombi;Password=ombi"
  },
  "ExternalDatabase": {
    "Type": "MySQL",
    "ConnectionString": "Server=IP-MYSQL;Port=3306;Database=Ombi;User=ombi;Password=ombi"
  }
}
```
3. Start ombi and wait for it to create the tables.
4. We access the ombi website to finish generating the missing tables. ExternalDatabase tables are not created until they are first accessed.
   **No need to start the wizard, just access the web.**
5. Stop ombi.

## Data Migration
1. In the directory where the Ombi databases are, we will create the file **"migration.json"**, in this file we will configure the databases that we want to export.
```json
{
    "OmbiDatabase": {
        "Type":"sqlite",
        "ConnectionString":"Data Source=/etc/Ombi/Ombi.db"
    },
    "SettingsDatabase": {
        "Type":"sqlite",
        "ConnectionString":"Data Source=/etc/Ombi/OmbiSettings.db"
    },
    "ExternalDatabase": {
        "Type":"sqlite",
        "ConnectionString":"Data Source=/etc/Ombi/OmbiExternal.db"
    }
}
```
If we do not want to export OmbiExternal.
```json
{
    "OmbiDatabase": {
        "Type":"sqlite",
        "ConnectionString":"Data Source=/etc/Ombi/Ombi.db"
    },
    "SettingsDatabase": {
        "Type":"sqlite",
        "ConnectionString":"Data Source=/etc/Ombi/OmbiSettings.db"
    }
}
```

2. Download the script and install the dependencies.
```
$ cd /etc/Ombi
$ wget https://raw.githubusercontent.com/vsc55/ombi_sqlite_mysql/master/ombi_sqlite2mysql.py
$ chmod +x ombi_sqlite2mysql.py

$ apt-get install python-mysqldb    # Debian/Ubuntu
$ emerge -va mysqlclient            # Gentoo
```

3. Start data migration.
The script will empty the tables from the MySQL/MariaDB database and automatically migrate the data from SQLite to MySQL/MariaDB.
```
$ python2 ombi_sqlite2mysql.py -c /etc/Ombi --host 192.168.1.100 --db Ombi --user ombi --passwd ombi
```

4. Start ombi and test if everything works fine.

## Help
```
$ python2 ombi_sqlite2mysql.py -h
Migration tool from SQLite to MySql/MariaDB for ombi (3.0.1) By Javier Pastor

Usage: ombi_sqlite2mysql.py [options]

Options:
  -h, --help            show this help message and exit
  -c CONFIG, --config=CONFIG
                        Path folder config ombi, default /etc/Ombi.
  --host=HOST           Host server MySQL/MariaDB. If not defined, a file is
                        generated with INSERT queries.
  --port=PORT           Port server MySQL/MariaDB, default 3306.
  --db=DB               Name database, default Ombi.
  --user=USER           User with access to MySQL/MariaDB, default ombi.
  --passwd=PASSWD       User password for MySQL/MariaDB, defalt empty.
  --no_backup           Disable the backup of the "__EFMigrationsHistory"
                        table.
  --save_dump           Save all query insert in the file (data_ombi.mysql).
  --force               Force clear all tables.
```