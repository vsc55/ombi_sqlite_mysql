# Migration procedure:

## Create DataBase and User:
```
CREATE DATABASE IF NOT EXISTS `Ombi` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE USER 'ombi'@'%' IDENTIFIED BY 'ombi';
GRANT ALL PRIVILEGES ON `Ombi`.* TO 'ombi'@'%' WITH GRANT OPTION;
```

## Create and prepare tables:
1. Stop ombi
2. Modify database.json to use mysql.
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
4. When you finish creating the tables stop ombi.
5. Empty all tables with data except:
- __EFMigrationsHistory

## We obtain sqlite data and adapt it to mysql.

```
# cd /etc/Ombi
# sudo apt install libsqlite3-mod-impexp
# wget https://raw.githubusercontent.com/vsc55/ombi_sqlite_mysql/master/ombi_sqlite2mysql.py
# chmod +x ombi_sqlite2mysql.py

# sqlite3 Ombi.db -cmd ".load libsqlite3_mod_impexp" "select export_sql('ombi.sql','1')"
# ./ombi_sqlite2mysql.py ombi.sql > ombi.mysql

# sqlite3 OmbiExternal.db -cmd ".load libsqlite3_mod_impexp" "select export_sql('OmbiExternal.sql','1')"
# ./ombi_sqlite2mysql.py OmbiExternal.sql > OmbiExternal.mysql

# sqlite3 OmbiSettings.db -cmd ".load libsqlite3_mod_impexp" "select export_sql('OmbiSettings.sql','1')"
# ./ombi_sqlite2mysql.py OmbiSettings.sql > OmbiSettings.mysql
```


In ombi.mysql, OmbiExternal.mysql and OmbiSettings.mysql are the inserts that must be executed on our mysql server.


NOTE: When importing data from OmbiExternal.db you have to import the tables in this order:
1. PlexServerContent
2. PlexSeasonsContent
3. PlexEpisode


And that seems to me to be everything.
