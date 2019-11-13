# Migration procedure

## Create database and user in the server MySql/MariaDB
On the MySQL/MariaDB server we will create the database and the user that we will use later.
```mysql
CREATE DATABASE IF NOT EXISTS `Ombi` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE USER 'ombi'@'%' IDENTIFIED BY 'ombi';
GRANT ALL PRIVILEGES ON `Ombi`.* TO 'ombi'@'%' WITH GRANT OPTION;
```

## Download Script and install dependencies
1. Download the script.
```
$ wget https://raw.githubusercontent.com/vsc55/ombi_sqlite_mysql/master/ombi_sqlite2mysql.py
$ chmod +x ombi_sqlite2mysql.py
```
2. Install the dependencies according to the operating system we use.
```
$ apt-get install python-mysqldb    # Debian/Ubuntu
$ emerge -va mysqlclient            # Gentoo
$ pip install mysqlclient           # Python Pip
```

## Create and prepare tables
1. Update to the latest version of ombi.
2. Stop ombi
3. Create or Modify **database.json** to use mysql.
```
$ python2 ombi_sqlite2mysql.py -c /etc/Ombi --only_db_json --host 192.168.1.100 --db Ombi --user ombi --passwd ombi 
```
4. Start ombi and wait for it to create the tables.
5. We access the ombi website to finish generating the missing tables. ExternalDatabase tables are not created until they are first accessed. 
   > **No need to start the wizard, just access the web.**
6. Stop ombi.

## Data Migration
> For data migration we will need the file **"migration.json"** that contains the locations of the SQLite databases.
> 
> If this file does not exist, it will be created and will search the databases in the folder specified with the parameter **"--config"**.
>
>If we don't want to migrate all the data, we can generate the file **"migration.json"** with the parameter **"--only_manager_json"** and then edit it by deleting the databases we don't want to migrate.

If we do not want to export OmbiExternal.
```
$ python2 ombi_sqlite2mysql.py -c /etc/Ombi --only_manager_json
$ vi /etc/Ombi/migration.json
```
Content "migration.json":
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

1. Start data migration.
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
  --save_dump           Save all query insert in the file "data_ombi.mysql".
  --force               Force clear all tables.
  --only_db_json        Only create or modify the file "database.json" with
                        the parameters that we specify.
  --only_manager_json   Only create or modify the file "migration.json" with
                        the parameters that we specify.
```
