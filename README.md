# Migration procedure:

## We obtain sqlite data and adapt it to mysql.

1. Create or modify database.json configured with sqlite databases:
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
2. Download script and extract data from sqlite:

```
# cd /etc/Ombi
# wget https://raw.githubusercontent.com/vsc55/ombi_sqlite_mysql/master/ombi_sqlite2mysql.py
# chmod +x ombi_sqlite2mysql.py

# python2 ombi_sqlite2mysql.py -c /etc/Ombi
```
We will create a data_ombi.mysql file with all the inserts that we will add later to the database.


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

  **NOTE:
  There are times when OmbiExternal tables are not created at startup.
  You have to access the web for Ombi to detect that they are missing and create them.
  You can know if you have created them by seeing if there are tables such as PlexEpisode, PlexSeasonsContent or SonarrCache.**
  
5. Empty all tables with data except:
- __EFMigrationsHistory

## Import data.

Now we import the data into our mysql database with the content of the file we generated before "data_ombi.mysql".

**NOTE: When importing the data, the order of the following keys must be taken into account.**

**Plex:**
1. PlexServerContent
2. PlexSeasonsContent
3. PlexEpisode

**Emby:**
1. EmbyContent
2. EmbyEpisode


And that seems to me to be everything.
