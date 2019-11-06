Migration procedure:



Stop ombi
Modify database.json to use mysql.
Start ombi and wait for it to create the tables.
When you finish creating the tables stop ombi.

In the mysql server we will have to empty the tables:
- AspNetUsers
- NotificationTemplates
- GlobalSettings

We obtain sqlite data and adapt it to mysql.

```
# sudo apt install libsqlite3-mod-impexp
# wget https://raw.githubusercontent.com/vsc55/ombi_sqlite_mysql/master/ombi_sqlite2mysql.py
# chmod +x ombi_sqlite2mysql.py
# sqlite3 Ombi.db
.load libsqlite3_mod_impexp
select export_sql('ombi.sql','1');

# ./ombi_sqlite2mysql.py ombi.sql > ombi.mysql
```


In ombi.mysql are the inserts that must be executed on our mysql server.
The same must be done with OmbiExternal.db and OmbiSettings.db


NOTE: When importing data from OmbiExternal.db you have to import the tables in this order:
1. PlexServerContent
2. PlexSeasonsContent
3. PlexEpisode


And that seems to me to be everything.
