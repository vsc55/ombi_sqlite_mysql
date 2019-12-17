#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Migration tool from SQLite to MySql/MariaDB for ombi
#
# Copyright © 2019  Javier Pastor (aka VSC55)
# <jpastor at cerebelum dot net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "VSC55"
__copyright__ = "Copyright © 2019, Javier Pastor"
__credits__ = "Javier Pastor"
__license__ = "GPL"
__version__ = "3.0.2"
__maintainer__ = 'Javier Pastor'
__email__ = "python@cerebelum.net"
__status__ = "Development"

import sys
import os
import time
import datetime
import codecs
import json
import sqlite3
import copy
import MySQLdb
from optparse import OptionParser

opts = None

global_progressbar_size = 60

json_file_migration = "migration.json"
json_file_database = "database.json"
json_db_file = ""
json_db_data = None
list_db = {'OmbiDatabase':'Ombi.db', 'SettingsDatabase':'OmbiSettings.db', 'ExternalDatabase':'OmbiExternal.db'}
list_db_process = None

check_count_data = {}

mysql_db_file = "data_ombi.mysql"
mysql_log_err = "insert_error.log"
mysql_cfg = None
mysql_conn = None
mysql_list_tables_save_backup = ['__EFMigrationsHistory']
mysql_list_tables_skip_clean = ['__EFMigrationsHistory']
mysql_list_error = []

fix_insert = {
    "__EFMigrationsHistory": {
        "id": "MigrationId",
        "required":{
            "20191103213915_Inital": {
                "data": {
                    "MigrationId": "20191103213915_Inital",
                    "ProductVersion": "2.2.6-servicing-10079"
                },
                "AcctionIsExistSQLite": "del",
                "isExistSQLite": False,
                "isExistMySQL": False
            },
            "20191103205915_Inital": {
                "data": {
                    "MigrationId": "20191103205915_Inital",
                    "ProductVersion": "2.2.6-servicing-10079"
                },
                "AcctionIsExistSQLite": "del",
                "isExistSQLite": False,
                "isExistMySQL": False
            },
            "20191102235852_Inital": {
                "data": {
                    "MigrationId": "20191102235852_Inital",
                    "ProductVersion": "2.2.6-servicing-10079"
                },
                "AcctionIsExistSQLite": "del",
                "isExistSQLite": False,
                "isExistMySQL": False,
            }
        },
        "mysql": {
            "ls_column": [],
            "ls_data": [],
            "ls_id": [],
            "data": []
        }
    }
}

# obsolete tables
sqlite_table_ignore = ['Logs', 'HangFire.AggregatedCounter', 'HangFire.Counter', 'HangFire.Hash', 'HangFire.Job', 'HangFire.JobParameter', 'HangFire.JobQueue', 'HangFire.List', 'HangFire.Schema', 'HangFire.Server', 'HangFire.Set', 'HangFire.State']



def dump(obj):
  for attr in dir(obj):
    print("obj.%s = %r" % (attr, getattr(obj, attr)))


# https://stackoverflow.com/questions/3160699/python-progress-bar
def progressbar(it, prefix="", size=60, file=sys.stdout):
    count = len(it)

    #def size_console():
    #    rows, columns = os.popen('stty size', 'r').read().split()
    #    return int(columns), int(rows)

    def show(j):
        # Not work in Windows!
        #if str(size).lower() == "auto".lower():
        #    size_fix = int(size_console()[0]) - len(prefix) - (len(str(count))*2) - 4 - 5
        #else:
        #    size_fix = size
        size_fix = size

        x = int(size_fix*j/count)
        file.write("%s[%s%s] %i/%i\r" % (prefix, "#"*x, "."*(size_fix-x), j, count))
        file.flush()        
    show(0)
    for i, item in enumerate(it):
        yield item
        show(i+1)
    file.write("\n")
    file.flush()



def _save_file(file_name, data, show_msg=True):
    if show_msg:
        sys.stdout.write("- Keeping in ({0})... ".format(file_name))

    try:
        with open(file_name, 'w') as f:
            for line in data:
                f.write('%s\n' % line)
        
    except IOError as ex:
        if show_msg:
            print("[!!]")
            print("I/O error({0}): {1}".format(ex.errno, ex.strerror))
        return False
    except Exception as e:
        if show_msg:
            print("[!!]")
            print("Unexpected error:", e)
            #print("Unexpected error:", sys.exc_info()[0])

        return False
    else:
        if show_msg:
            print("[✓]")
        return True

def _read_json(file_json, def_return=None, show_msg=True):
    return_date = def_return
    if os.path.isfile(file_json):
        try:
            f = codecs.open(file_json, 'r', 'utf-8')
            return_date = json.loads(f.read())
            f.close()
        except Exception as e:
            if show_msg:
                print("Exception read json ({0}):".format(file_json), e)
    return return_date

def _save_json(file_json, data, overwrite=False, show_msg=True):
    if show_msg:
        sys.stdout.write("- Saving in ({0})... ".format(file_json))

    if not overwrite:
        if os.path.isfile(file_json):
            if show_msg:
                print("[SKIP, ALREADY EXISTS!]")
            return True

    try:
        f = codecs.open(file_json, 'w', 'utf-8')
        f.write(json.dumps(data))
        f.close()
    except Exception as e:
        if show_msg:
            print("[!!]")
            print("Exception save json ({0}):".format(file_json), e)
        return False
    if show_msg:
        print("[✓]")
    return True


def _get_path_file_in_conf(file_name):
    if opts is not None and opts.config and file_name:
        return os.path.join(opts.config, file_name)
    else:
        return ""

def _find_in_json(json_data, find, def_return="", ignorecase=True):
    data_return = def_return
    if json_data and find:
        work_dict = json_data

        keys = []
        if isinstance(find, str):
            keys = find.split()
        elif isinstance(find, list):
            keys = copy.copy(find)
        elif isinstance(find, tuple):
            keys = list(find)
        else:
            return data_return
        
        while keys:
            target = keys.pop(0)
            if isinstance(work_dict, dict):
                key_exist = False
                new_value = None
                for (key, value) in work_dict.items():
                    if (key.lower() if ignorecase else key) == (target.lower() if ignorecase else target):
                        key_exist = True
                        new_value = value

                if key_exist:
                    if not keys:    # this is the last element in the find_key, and it is in the data_dict
                        data_return = new_value
                        break
                    else:   # not the last element of find_key, change the temp var
                        work_dict = new_value
                else:
                    continue
            else:
                continue

    return data_return



def _check_read_config():
    global json_db_data
    global list_db_process

    print("Check {0}:".format(json_file_migration))

    if opts is None:
        print("Error: Args is Null!!")
        return False

    elif not opts.config:
        print("Error: Not select config path!!")
        return False

    elif not os.path.isdir(opts.config):
        print ("Error: The config path does not exist or is not a directory !!")
        return False
    
    json_db = _get_path_file_in_conf(json_file_migration)
    if not os.path.isfile(json_db):
        print("Error: File {0} not exist!!!".format(json_db))
        return False
        
    json_db_data = _read_json(json_db)
    if json_db_data is None:
        print ("Error: No data has been read from the json ({0}) file, please review it.!!!!".format(json_db))
        return False
    
    list_db_process = []
    
    for db_name in list_db:
        #if db_name not in json_db_data:
        if db_name.lower() not in map(lambda name: name.lower(), json_db_data):
            print("- {0} [No Config >> Skip]".format(db_name))
            continue

        type_db = _find_in_json(json_db_data, [db_name, 'type'])
        if type_db.lower() == "SQLite".lower():
            list_db_process.append(db_name)
            print("- {0} [SQLite >> Migrate]".format(db_name))
        elif type_db.lower() == "MySQL".lower():
            print("- {0} [MySQL >> Skip]".format(db_name))
        else:
            print("- {0} [{1} >> Unknown]".format(db_name, type_db))
    
    print ("")
    if len(list_db_process) == 0:
        print ("Error: It is not necessary to update all databases are migrated.")
        return False

    return True



def _check_config_mysql():
    # TODO: pendiente leer config de database.json
    global mysql_cfg
    mysql_cfg = None
    if opts.host:
        mysql_cfg = {
            'host': opts.host,
            'port': opts.port,
            'db': opts.db,
            'user': opts.user,
            'passwd': opts.passwd,
            'connect_timeout': 2,
            'use_unicode': True,
            'charset': 'utf8'
        }

def _mysql_IsConnect():
    if mysql_conn is None:
        return False
    else:
        # TODO: Pendiente mirar mas info .open.real
        if mysql_conn.open.real == 1:
            return True
        else:
            return False

def _mysql_connect(show_msg=True):
    global mysql_conn
    msg_err = None

    if mysql_cfg is None:
        if show_msg:
            print("MySQL > No Config!")
        return False

    if _mysql_IsConnect:
        _mysql_disconnect()

    if show_msg:
        #print("MySQL > Connecting...")
        sys.stdout.write("MySQL > Connecting... ")
    try:
        mysql_conn = MySQLdb.connect(**mysql_cfg)
        
    except MySQLdb.Error as e:
        try:
            msg_err = "* MySQL Error [{0}]: {1}".format(e.args[0], e.args[1])
            
        except IndexError as e:
            msg_err = "* MySQL IndexError: {0}".format(str(e))
            
    except TypeError as e:
        msg_err = "* MySQL TypeError: {0}".format(str(e))
        
    except ValueError as e:
        msg_err =  "* MySQL ValueError: {0}".format(str(e))
        
    if msg_err:
        if show_msg:
            print("[!!]")
            print(msg_err)
        sys.exit()
    
    if show_msg:
        print("[✓]")

    return True
 
def _mysql_disconnect(show_msg=True):
    global mysql_conn

    if mysql_conn is not None:
        if show_msg:
            sys.stdout.write("MySQL > Disconnecting... ")
        mysql_conn.close()
        mysql_conn = None
        if show_msg:
            print("[✓]")

def _mysql_execute_querys(list_insert, progressbar_text, progressbar_size, run_commit=250, ignorer_error=[], DISABLE_FOREIGN_KEY_CHECKS=True, show_msg=True):
    global mysql_conn
    global mysql_list_error

    if not _mysql_IsConnect:
        #controlar si no hay conexion con mysql return false o sys.exit()
        return False
    
    if list_insert is None or len(list_insert) == 0:
        return True

    cur = mysql_conn.cursor()
    if DISABLE_FOREIGN_KEY_CHECKS:
        # Desactivamos la comprobacion de tablas relacionadas.
        cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
    
    count_commit = 0
    for i in progressbar(list_insert, progressbar_text, progressbar_size):
        exit_is_error = False
        show_msg_err = True
        str_msg_err = None
        try:
            cur.execute(i)
            if count_commit == run_commit:
                mysql_conn.commit()
                count_commit = 0
            else:
                count_commit += 1
            
        except MySQLdb.Error as e:
            try:
                str_msg_err = "* MySQL Error [{0}]: {1}".format(e.args[0], e.args[1])
                if e.args[0] in ignorer_error:
                    show_msg_err = False

            except IndexError as e:
                str_msg_err = "* MySQL IndexError: {0}".format(str(e))

            #exit_is_error = True

        except TypeError as e:
            exit_is_error = True
            str_msg_err = "* MySQL TypeError: {0}".format(str(e))

        except ValueError as e:
            exit_is_error = True
            str_msg_err = "* MySQL ValueError: {0}".format(str(e))

        if str_msg_err:
            mysql_list_error.append(str_msg_err)
            mysql_list_error.append(i)
            if show_msg_err:
                print("")
                print(str_msg_err)
                print("* Error Query: {0}".format(i))
                print("")
                time.sleep(0.25)

        if exit_is_error:
            return False

    if count_commit > 0:
        mysql_conn.commit()

    if DISABLE_FOREIGN_KEY_CHECKS:
        # Volvemos a activar la comprobacion de tablas relacionadas.
        cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
        
    mysql_conn.commit()

    cur.close()
    cur = None
    return True

def _mysql_fetchall_querys(query, ignorer_error=[]):
    global mysql_conn
    global mysql_list_error

    if not query or len(query) == 0:
        return None

    if not _mysql_IsConnect:
        return None
    
    data_return = []
    cur = mysql_conn.cursor()
    for q in query:
        str_msg_err = None
        show_msg_err = True
        try:
            cur.execute(q)
            data_return.append(cur.fetchall())

        except MySQLdb.Error as e:
            try:
                str_msg_err = "* MySQL Error [{0}]: {1}".format(e.args[0], e.args[1])
                if e.args[0] in ignorer_error:
                    show_msg_err = False

            except IndexError as e:
                str_msg_err = "* MySQL IndexError: {0}".format(str(e))

        except TypeError as e:
            str_msg_err = "* MySQL TypeError: {0}".format(str(e))

        except ValueError as e:
            str_msg_err = "* MySQL ValueError: {0}".format(str(e))

        if str_msg_err:
            data_return.append(None)
            if show_msg_err:
                print("")
                print(str_msg_err)
                print("* Error Query: {0}".format(q))
                print("")
                time.sleep(0.25)

    cur.close()
    cur = None
    return data_return



def _mysql_migration(data_dump):
    if not _mysql_IsConnect:
        return False

    print ("Start Migration:")
    list_insert = []
    str_insert = "INSERT INTO"
    for i in progressbar(data_dump, "- Preparing ", global_progressbar_size):
        if i is None:
            #print("Ignorer 1:", i)
            continue
        elif len(i) < len(str_insert):
            #print("Ignorer 2:", i)
            continue
        elif i[:len(str_insert)].upper() != str_insert:
            #print("Ignorer 3:", i)
            continue
        else:
            list_insert.append(i)

    # Error 1452 - Cannot add or update a child row: a foreign key constraint fails
    # Error 1062 - Duplicate entry
    isInsertOK = _mysql_execute_querys(list_insert, "- Running   ", global_progressbar_size, 500, [1452, 1062], True)

    if isInsertOK:
        if _mysql_migration_check():
            print("Migration [✓]")
    else:
        print("Migration [!!]")
    print("")

    return isInsertOK

def _mysql_migration_check():

    if not _mysql_IsConnect:
        return False

    arr_query = []

    q = "SET group_concat_max_len = 1024 * 1024 * 100;"
    q += "SELECT CONCAT('SELECT * FROM (',GROUP_CONCAT(CONCAT('SELECT ',QUOTE(tb),' Tables_in_database, COUNT(1) \"Number of Rows\" FROM ',db,'.',tb) SEPARATOR ' UNION '),') A;') "
    q += "INTO @sql FROM (SELECT table_schema db,table_name tb FROM information_schema.tables WHERE table_schema = DATABASE() and table_name not LIKE '%_migration_backup_%') A;"
    q += "PREPARE s FROM @sql;"
    arr_query.append(q)

    # Si se ejecuta todo en el mismo execute no retorna datos!
    q = "EXECUTE s; DEALLOCATE PREPARE s;"
    arr_query.append(q)

    return_query = _mysql_fetchall_querys(arr_query)
    list_tables = return_query[1]

    isOkMigration = True
    for i in progressbar(list_tables, "- Checking  ", global_progressbar_size):
        table = i[0]
        count = i[1]
        count_sqlite = 0
        if check_count_data is not None and table in check_count_data:
            count_sqlite = check_count_data[table]

        if count != count_sqlite:
            isOkMigration = False
            # 80 = size + text ("- Running   "), pongo algo mas
            print('{:<80}'.format("- [!!] -> {0} -> [SQLite ({1}) / MySQL ({2})] = {3}".format(table, count_sqlite, count, count_sqlite - count)))
        else:
            #print("- [OK] -> {0} ({1})".format(table, count))
            pass

    return isOkMigration

def _mysql_tables_clean():
    global check_count_data

    if not _mysql_IsConnect:
        return False

    print ("Start clean tables:")
    arr_query = []

    # TODO: Pendiente ver por que si no se vacia __EFMigrationsHistory no se importan todos los datos correctamente!!!!!!

    #Retorna datos no fiables, en ocasiones dice que hay 0 registros y si tiene registros.
    #q = "SELECT table_name, table_rows FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{0}';".format(mysql_cfg['db'])

    q = "SET group_concat_max_len = 1024 * 1024 * 100;"
    q += "SELECT CONCAT('SELECT * FROM (',GROUP_CONCAT(CONCAT('SELECT ',QUOTE(tb),' `Table`, COUNT(1) `Rows` FROM ',db,'.',tb) SEPARATOR ' UNION '),') A "
    q += "ORDER BY "

    # No hace falta ordenar las tablas ya que usamos DISABLE_FOREIGN_KEY_CHECKS.
    #q += "`Table` = \"__EFMigrationsHistory\" DESC, "
    #q += "`Table` = \"AspNetUsers\" DESC, `Table` = \"ChildRequests\" DESC, `Table` = \"MovieRequests\" DESC, "
    #q += "`Table` = \"Issues\" DESC, `Table` = \"IssueComments\" DESC, `Table` = \"IssueCategory\" DESC, "
    #q += "`Table` = \"EmbyContent\" DESC, `Table` =  \"EmbyEpisode\" DESC, "
    #q += "`Table` = \"PlexServerContent\" DESC, `Table` = \"PlexSeasonsContent\" DESC, `Table` = \"PlexEpisode\" DESC, "

    q += "`Table` ASC "
    q += ";')"
    q += "INTO @sql FROM (SELECT table_schema db,table_name tb FROM information_schema.tables WHERE table_schema = DATABASE() and table_name not LIKE '%_migration_backup_%') A;"
    q += "PREPARE s FROM @sql;"
    arr_query.append(q)
    
    # Si se ejecuta todo en el mismo execute no retorna datos!
    q = "EXECUTE s; DEALLOCATE PREPARE s;"
    arr_query.append(q)

    return_query = _mysql_fetchall_querys(arr_query)

    list_querys = []
    for table, count in return_query[1]:
        if count == 0:
            #print("- [EMPTY] -> {0}".format(table))
            continue
        
        if table in mysql_list_tables_save_backup:
            table_temp = "{0}_migration_backup_{1}".format(table, datetime.datetime.now().strftime("%Y%m%d%H%M%S_%f"))

            #print("- [BACKUP] -> {0} in {1}".format(table, table_temp))
            print("- [BACKUP] -> {0}".format(table))
            
            q = "CREATE TABLE `{0}` LIKE `{1}`;".format(table_temp, table)
            list_querys.append(q)
            q = "INSERT INTO `{0}` SELECT * FROM `{1}`;".format(table_temp, table)
            list_querys.append(q)

        if table in mysql_list_tables_skip_clean:
            if table not in check_count_data:
                check_count_data[table] = 0

            check_count_data[table] += count
            print("- [SKIP  ] -> {0} -> rows: {1}".format(table, count))
            continue
                
        print("- [CLEAN ] -> {0} -> rows: {1}".format(table, count))
        q = "TRUNCATE TABLE `{0}`;".format(table)
        list_querys.append(q)

    print("")
    isAllOk = _mysql_execute_querys(list_querys, "- Running   ", global_progressbar_size, 500, [], True)

    if isAllOk:
        print ("Clean tables [✓]")
    else:
        print ("Clean tables [!!]")
    print("")

    return isAllOk



def _convert_str_sqlite_mysql(str_data):
    str_data = str_data.replace('\\', '\\\\')
    str_data = str_data.replace('"', '\\"')

    #TODO: Lo dejo por si las moscas, pero casi seguro que sobra.
    #str_data = str_data.replace(",'t'", ",'1'")
    #str_data = str_data.replace(",'f'", ",'0'")

    #line = line.replace('"', r'\"')
    #line = line.replace('"', "'")
    #line = re.sub(r"(?<!')'t'(?=.)", r"1", line)
    #line = re.sub(r"(?<!')'f'(?=.)", r"0", line)
    return str_data


def _sqlite_dump():
    global fix_insert
    global check_count_data

    print("Dump SQLite:")
    for db_name in list_db_process:
        #print("- Exporting ({0}):".format(db_name))

        connection_str=_find_in_json(json_db_data, [db_name, 'ConnectionString'])
        if connection_str.split("=")[0].lower() != "Data Source".lower():
            print ("Warning: {0} no location data source, ignorer database!".format(db_name))
            continue
        
        yield('--')
        yield('-- DataBase: %s;' % db_name)
        yield('--')

        sqlite_db_file =  connection_str.split("=")[1]
        con = sqlite3.connect(sqlite_db_file)
        data_get_sqlite = list(_iterdump(con, db_name))

        for line in progressbar(data_get_sqlite, '{:<20}'.format("- {0} ".format(db_name)), global_progressbar_size):
            yield(line)

    #required insert

    # Si no se aNaden da error al arrancar Ombi ya que intenta crear las tablas pero ya existen.
    #INSERT INTO `__EFMigrationsHistory` (`MigrationId`, `ProductVersion`) VALUES ('20191103213915_Inital', '2.2.6-servicing-10079');
    #INSERT INTO `__EFMigrationsHistory` (`MigrationId`, `ProductVersion`) VALUES ('20191103205915_Inital', '2.2.6-servicing-10079');
    #INSERT INTO `__EFMigrationsHistory` (`MigrationId`, `ProductVersion`) VALUES ('20191102235852_Inital', '2.2.6-servicing-10079');

    #yield "INSERT INTO `__EFMigrationsHistory` (`MigrationId`, `ProductVersion`) VALUES ('20191103213915_Inital', '2.2.6-servicing-10079');"
    #yield "INSERT INTO `__EFMigrationsHistory` (`MigrationId`, `ProductVersion`) VALUES ('20191103205915_Inital', '2.2.6-servicing-10079');"
    #yield "INSERT INTO `__EFMigrationsHistory` (`MigrationId`, `ProductVersion`) VALUES ('20191102235852_Inital', '2.2.6-servicing-10079');"
    #check_count_data['__EFMigrationsHistory'] -= 3

    for key, val in fix_insert.items():
        if key not in check_count_data:
                check_count_data[key] = 0

        yield('--')
        yield('-- Required Insert: %s;' % key)
        yield('--')

        
        for _, req_val in val['required'].items():
            if req_val['isExistMySQL']:
                continue

            if len(req_val['data']) > 0:
                q_col = ""
                q_val = ""
                for data_key, data_val in req_val['data'].items():

                    if len(q_col) > 0:
                        q_col += ", "
                    q_col += '`{0}`'.format(data_key)

                    if len(q_val) > 0:
                        q_val += ", "
                    q_val += "'{0}'".format(data_val)

                q = 'INSERT INTO `{0}` ({1}) VALUES({2});'.format(key, q_col, q_val)
                yield q
                check_count_data[key] += 1
    print("")

def _iterdump(connection, db_name):
    global check_count_data

    cu = connection.cursor()

    q = "SELECT name, type FROM sqlite_master WHERE sql NOT NULL AND type == 'table' ORDER BY "

    # We control the order of tables so that the "INSERT" are in order and that there are related tables.
    if db_name.lower() == "OmbiDatabase".lower():
        # SELECT * FROM sqlite_master WHERE sql NOT NULL AND type == 'table' ORDER BY name = 'AspNetUsers' DESC,  name = 'ChildRequests' DESC,  name = 'MovieRequests' DESC, name = 'Issues' DESC, name = 'IssueComments' DESC, name ASC
        q += "name = 'AspNetUsers' DESC,  name = 'ChildRequests' DESC,  name = 'MovieRequests' DESC, name = 'Issues' DESC, name = 'IssueComments' DESC, name ASC"
    elif db_name.lower() == "ExternalDatabase".lower():
        #SELECT * FROM sqlite_master WHERE sql NOT NULL AND type == 'table' ORDER BY name = 'EmbyContent' DESC, name = 'EmbyEpisode' DESC, name = 'PlexServerContent' DESC, name = 'PlexSeasonsContent' DESC, name = 'PlexEpisode' DESC, name ASC
        q += "name = 'EmbyContent' DESC, name =  'EmbyEpisode' DESC, name = 'PlexServerContent' DESC, name = 'PlexSeasonsContent' DESC, name = 'PlexEpisode' DESC, name ASC"
    else:
        q += "name ASC"

    schema_res = cu.execute(q)
    for table_name, _ in schema_res.fetchall():
        if table_name not in check_count_data:
            check_count_data[table_name] = 0

        if table_name in ['sqlite_sequence', 'sqlite_stat1'] or table_name.startswith('sqlite_'):
            continue
        elif table_name in sqlite_table_ignore:
            continue
        elif cu.execute("SELECT COUNT(*) FROM '{0}'".format(table_name)).fetchone()[0] < 1:
            continue

        # TODO: Pendiente agrupar insert para una exportacion mas rapida.

        # Build the insert statement for each row of the current table
        res = cu.execute("PRAGMA table_info('%s')" % table_name)
        column_names = [str(table_info[1]) for table_info in res.fetchall()]

        q_col = ""
        for col_n in column_names:
            if len(q_col) > 0:
                q_col += ", "
            q_col += '`{0}`'.format(col_n)

        yield('--')
        yield('-- Table: %s;' % table_name)
        yield('--')

        q = "SELECT '"
        q += ",".join(["'||quote(" + col + ")||'" for col in column_names])
        q += "' FROM '%(tbl_name)s'"

        query_res = cu.execute(q % {'tbl_name': table_name})

        for row in query_res:
            q_insert = _convert_str_sqlite_mysql(row[0].encode('utf-8'))

            q_insert = _iterdump_fix_insert(q_insert, q_col, table_name)
            if not q_insert:
                continue

            q_insert = 'INSERT INTO `{0}` ({1}) VALUES({2})'.format(table_name, q_col, q_insert)
            check_count_data[table_name] += 1
            yield("%s;" % q_insert)
    
    cu.close()
    cu = None


def _iterdump_fix_insert(q, q_col, table_name):
    global fix_insert
    
    if table_name in fix_insert:
        v = fix_insert[table_name]

        for _, v_sub in v['required'].items():
            isEqual = True
            for _, v_data in v_sub['data'].items():
                if v_data not in q:
                    isEqual = False
                    break

            if isEqual:
                v_sub["isExistSQLite"] = True
                if v_sub["AcctionIsExistSQLite"] == "del":
                    return None
        
        # eliminamos el simbolo ` que tiene cada nombre de columna a los lados.
        ls_col = str(q_col).replace("`","").split(",")
        id_col = str(v['id'])
        
        if id_col in ls_col:
            index_col_id = ls_col.index(id_col)
            val_id = str(q).split(",")[index_col_id]

            # Detecta si tiene comillas simples a los lados y las elimina poder hacer la compracion con mysql->ls_id.
            #val_id = val_id[(1 if val_id[:1] == "'" else None):(-1 if val_id[-1:] == "'" else None)]
            if val_id[:1] == "'" and val_id[-1:] == "'":
                val_id = val_id[1:-1]
            
            #val_id = id del la consulta que nos ha llegado en q.
            if len(val_id) > 0:
                if val_id in v['mysql']['ls_id']:
                    # Si exite en mysql no la necesitamos.
                    return None
        else:
            # No se encuntra columna ID asi que pasamos.
            pass
        
    return q



def _fix_insert_read_mysql():
    global fix_insert

    isAllOk = True
    for k, v in progressbar(fix_insert.items(), "- Reading   ", global_progressbar_size):
        ls_query = []
        q = "SHOW columns FROM `{0}`;".format(k)
        ls_query.append(q)
        q = "SELECT * FROM `{0}`;".format(k)
        ls_query.append(q)
        return_querys = _mysql_fetchall_querys(ls_query, [1146])

        if not return_querys[0]:
            print("")
            print("- Error: Table \"{0}\" requiered is not exist in the server MySQL!!!").format(k)
            isAllOk = False
            break

        ls_column = []
        for i in return_querys[0]:
            ls_column.append(i[0])

        ls_data = return_querys[1]
        ls_ids = []
        data = []
        for i in ls_data:
            line = {}
            n_col = 0
            for ii in i:
                col_name = ls_column[n_col]
                if col_name == v['id']:
                    ls_ids.append(ii)
                    if ii in v['required']:
                        v['required'][ii]['isExistMySQL'] = True
                line[col_name] = ii
                n_col += 1
            data.append(line)

        v['mysql'] = {}
        v['mysql']['ls_column'] = ls_column
        v['mysql']['ls_data'] = ls_data
        v['mysql']['ls_id'] = ls_ids
        v['mysql']['data'] = data

    if isAllOk:
        print ("Read tables [✓]")
    else:
        print ("Read tables [!!]")
    print("")
    return isAllOk


def _save_dump(data, show_msg=True):
    if show_msg:
        print ("Save Dump:")

    dump_db_file =  _get_path_file_in_conf(mysql_db_file)
    data_return = _save_file(dump_db_file, data, show_msg)

    if show_msg:
        print("")

    return data_return

def _save_error_log(data, show_msg=True):
    if not data or len(data) == 0:
        return True

    if show_msg:
        print ("Save Log Error Mysql Insert:")

    log_file =  _get_path_file_in_conf(mysql_log_err)
    data_return = _save_file(log_file, data, show_msg)

    if show_msg:
        print("")

    return data_return

def _mysql_database_json_update(overwrite=False, show_msg=True):
    json_mysql = _get_path_file_in_conf(json_file_database)
    json_data = {}
    for db_name in list_db:
        json_data[db_name] = {
            "Type": "MySQL",
            "ConnectionString": "Server={0};Port={1};Database={2};User={3};Password={4}".format(mysql_cfg['host'], mysql_cfg['port'], mysql_cfg['db'], mysql_cfg['user'], mysql_cfg['passwd'])
        }
    
    if show_msg:
        print("Generate file \"{0}\":".format(json_file_database))
    
    _save_json(json_mysql, json_data, overwrite, show_msg)
    if show_msg:
        print("")

def _manager_json_update(overwrite=False, show_msg=True):
    json_file = _get_path_file_in_conf(json_file_migration)
    json_data = {}
    for db_name in list_db:
        db_file = _get_path_file_in_conf(list_db[db_name])
        if not os.path.isfile(db_file):
            continue
        json_data[db_name] = {
            "Type": "sqlite",
            "ConnectionString": "Data Source={0}".format(db_file)
        }

    if show_msg:
        print("Generate file \"{0}\":".format(json_file_migration))

    _save_json(json_file, json_data, overwrite, show_msg)
    if show_msg:
        print("")



def _OptionParser():
    global opts
    op = OptionParser()
    op.add_option('-c', '--config', default="/etc/Ombi", help="Path folder config ombi, default /etc/Ombi.")
    op.add_option('', '--host', help="Host server MySQL/MariaDB. If not defined, a file is generated with INSERT queries.")
    op.add_option('', '--port', type="int", default=3306, help="Port server MySQL/MariaDB, default 3306.")
    op.add_option('', '--db', default="Ombi", help="Name database, default Ombi.")
    op.add_option('', '--user', default="ombi", help="User with access to MySQL/MariaDB, default ombi.")
    op.add_option('', '--passwd', default="", help="User password for MySQL/MariaDB, defalt empty.")
    op.add_option('', '--no_backup', action="store_true",  default=False, help="Disable the backup of the \"__EFMigrationsHistory\" table.")
    op.add_option('', '--save_dump', action="store_true",  default=False, help="Save all query insert in the file \"{0}\".".format(mysql_db_file))
    op.add_option('', '--force', action="store_true",  default=False, help="Force clear all tables.")
    op.add_option('', '--only_db_json', action="store_true",  default=False, help="Only create or modify the file \"{0}\" with the parameters that we specify.".format(json_file_database))
    op.add_option('', '--only_manager_json', action="store_true",  default=False, help="Only create or modify the file \"{0}\" with the parameters that we specify.".format(json_file_migration))
    opts, _ = op.parse_args()

    return _OptionParser_apply()

def _OptionParser_apply():
    global mysql_list_tables_save_backup
    global mysql_list_tables_skip_clean

    _check_config_mysql()
    if opts.no_backup:
        mysql_list_tables_save_backup = []

    if opts.force:
        mysql_list_tables_skip_clean = []

    if opts.only_db_json or opts.only_manager_json:
        if opts.only_db_json:
            if mysql_cfg:
                _mysql_database_json_update(True, True)
            else:
                print ("Unable to create file \"{0}\" missing required parameters.".format(json_file_database))

        if opts.only_manager_json:
            _manager_json_update(True, True)
        return False

    return True
    


def main():
    global check_count_data
    
    if not _OptionParser():
        return

    _manager_json_update(None, False)
    _mysql_database_json_update(True)

    if mysql_cfg:
        _mysql_connect()
        if not opts.force:
            if not _fix_insert_read_mysql():
                _mysql_disconnect()
                return

    if not _check_read_config():
        _mysql_disconnect()
        return

    data_dump = list(_sqlite_dump())

    if _mysql_IsConnect:
        if _mysql_tables_clean():
            _mysql_migration(data_dump)
        
        _save_error_log(mysql_list_error)
        _mysql_disconnect()
    
    if opts.save_dump:
        _save_dump(data_dump)

if __name__ == "__main__":
    print("Migration tool from SQLite to MySql/MariaDB for ombi ({0}) By {1}".format(__version__, __author__))
    print("")
    main()
