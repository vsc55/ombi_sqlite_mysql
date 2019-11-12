# Migration procedure:


## Create database and user in the server MySql/MariaDB:
```
CREATE DATABASE IF NOT EXISTS `Ombi` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE USER 'ombi'@'%' IDENTIFIED BY 'ombi';
GRANT ALL PRIVILEGES ON `Ombi`.* TO 'ombi'@'%' WITH GRANT OPTION;
```


## Create and prepare tables:
1. Stop ombi
2. Create or Modify database.json to use mysql.
```
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
```
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
```
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
Migration tool from SQLite to MySql/MariaDB for ombi (3.0) By VSC55

Usage: ombi_sqlite2mysql.py [options]

Options:
  -h, --help            show this help message and exit
  -c CONFIG, --config=CONFIG
                        path folder config ombi, default /etc/Ombi
  --host=HOST           host server mysql/mariadb, If empty, file is generated
                        with inserts.
  --port=PORT           port server mysql/mariadb, default 3306
  --db=DB               name database, default Ombi
  --user=USER           user name mysql/mariadb, default ombi
  --passwd=PASSWD       passwd mysql/mariadb, defalt empty
  --no_backup           disable backup table __EFMigrationsHistory
```