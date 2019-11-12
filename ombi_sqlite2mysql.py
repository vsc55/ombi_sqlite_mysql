#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Migration tool by SQLite to MySql/MariaDB for ombi
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

import sys
import os
import time
import codecs
import json
import sqlite3
import copy
import MySQLdb

from optparse import OptionParser

opts = None

json_file_migration = "migration.json"
json_file_database = "database.json"
json_db_file = ""
json_db_data = None
list_db = ['OmbiDatabase', 'SettingsDatabase', 'ExternalDatabase']
list_db_process = None

check_count_data = {}

mysql_db_file = "data_ombi.mysql"
mysql_log_err = "insert_error.log"
mysql_cfg = None
mysql_conn = None
mysql_list_tables_no_clean = ['__EFMigrationsHistory']
mysql_list_error = []



def dump(obj):
  for attr in dir(obj):
    print("obj.%s = %r" % (attr, getattr(obj, attr)))


# https://stackoverflow.com/questions/3160699/python-progress-bar
def progressbar(it, prefix="", size=60, file=sys.stdout):
    count = len(it)
    def show(j):
        x = int(size*j/count)
        file.write("%s[%s%s] %i/%i\r" % (prefix, "#"*x, "."*(size-x), j, count))
        file.flush()        
    show(0)
    for i, item in enumerate(it):
        yield item
        show(i+1)
    file.write("\n")
    file.flush()



def _save_file(file_name, data, show_msg=True):
    sys.stdout.write("- Keeping in ({0})... ".format(file_name))
    try:
        with open(file_name, 'w') as f:
            for line in data:
                f.write('%s\n' % line)
        
    except IOError as ex:
        if show_msg:
            print(" ERROR!")
            print("I/O error({0}): {1}".format(ex.errno, ex.strerror))
        return False
    except:
        if show_msg:
            print(" ERROR!")
            print("Unexpected error:", sys.exc_info()[0])
        return False
    else:
        if show_msg:
            print("OK!")
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
                print("Exception read json ({$1}):".format(file_json), e)
    return return_date

def _save_json(file_json, data, show_msg=True):
    try:
        f = codecs.open(file_json, 'w', 'utf-8')
        f.write(json.dumps(data))
        f.close()
    except Exception as e:
        if show_msg:
            print("Exception save json ({$1}):".format(file_json), e)
        return False
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

    if opts is None:
        print("Error: Args is Null!!")
        sys.exit()

    elif not opts.config:
        print("Error: Not select config path!!")
        sys.exit()

    elif not os.path.isdir(opts.config):
        print ("Error: The config path does not exist or is not a directory !!")
        sys.exit()
    
    json_db = _get_path_file_in_conf(json_file_migration)
    if not os.path.isfile(json_db):
        print("Error: File {0} not exist!!!".format(json_db))
        sys.exit()
        
    json_db_data = _read_json(json_db)
    if json_db_data is None:
        print ("Error: No data has been read from the json ({0}) file, please review it.!!!!".format(json_db))
        sys.exit()
    
    list_db_process = []
    print("Check {0}:".format(json_file_migration))
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
    
    if len(list_db_process) == 0:
        print ("")
        print ("Error: It is not necessary to update all databases are migrated.")
        sys.exit()

def _check_config_mysql(opts):
    #TODO: pendiente leer config de database.json
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

def _mysql_connect():
    global mysql_conn

    if mysql_cfg:
        _mysql_disconnect()
        print("Connecting mysql...")
        try:
            mysql_conn = MySQLdb.connect(**mysql_cfg)
            print("Connection OK!")

        except MySQLdb.Error, e:
            try:
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
                sys.exit()
            except IndexError:
                print "MySQL Error: %s" % str(e)
                sys.exit()
        except TypeError, e:
            print(e)
            sys.exit()
        except ValueError, e:
            print(e)
            sys.exit()

def _mysql_disconnect():
    global mysql_conn

    if mysql_conn is not None:
        print("Disconnecting mysql...")
        mysql_conn.close()
        mysql_conn = None
        print("Disconnect OK!")

def _mysql_migration(data_dump):
    global mysql_conn
    global mysql_list_error

    if mysql_conn is not None:
        print ("Start Migration:")
        
        cur = mysql_conn.cursor()
        cur.execute("SET FOREIGN_KEY_CHECKS = 0;")

        count_commit = 0

        str_insert = "INSERT INTO"
        for i in progressbar(data_dump, "- Progress: ", 60):
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
                try:
                    cur.execute(i)
                    if count_commit == 500:
                        mysql_conn.commit()
                        count_commit = 0
                    else:
                        count_commit += 1
                    
                except MySQLdb.Error, e:
                    mysql_conn.rollback()
                    show_msg_err = True
                    try:
                        str_msg = "* MySQL Error [%d]: %s" % (e.args[0], e.args[1])
                        if e.args[0] == 1452:
                            # Cannot add or update a child row: a foreign key constraint fails
                            show_msg_err = False
                        elif e.args[0] == 1062:
                            #  Duplicate entry
                            show_msg_err = False

                    except IndexError:
                        str_msg = "* MySQL Error: %s" % str(e)
                    
                    mysql_list_error.append(str_msg)
                    mysql_list_error.append(i)
                    if show_msg_err:
                        print str_msg
                        print "* Query: {0}".format(i)
                    
                    #sys.exit()
                    #time.sleep(1)
                        
                except TypeError, e:
                    mysql_conn.rollback()
                    print(e)
                    print "Query: {0}".format(i)
                    sys.exit()

                except ValueError, e:
                    mysql_conn.rollback()
                    print(e)
                    print "Query: {0}".format(i)
                    sys.exit()

        if count_commit > 0:
            mysql_conn.commit()
        
        cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
        print ("Migration completed.")

        mysql_conn.commit()

        cur.close()
        cur = None

def _mysql_migration_check():
    global mysql_conn
    global check_count_data
    print("Check Migartion...")
    
    if mysql_conn is None:
        isOkMigration = False
    else:
        isOkMigration = True

        cur = mysql_conn.cursor()

        q = "SET group_concat_max_len = 1024 * 1024 * 100;"
        q += "SELECT CONCAT('SELECT * FROM (',GROUP_CONCAT(CONCAT('SELECT ',QUOTE(tb),' Tables_in_database, COUNT(1) \"Number of Rows\" FROM ',db,'.',tb) SEPARATOR ' UNION '),') A;') INTO @sql FROM (SELECT table_schema db,table_name tb FROM information_schema.tables WHERE table_schema = DATABASE()) A;"
        q += "PREPARE s FROM @sql;"
        cur.execute(q)

        # Si se ejecuta todo en el mismo execute no retorna datos!
        q = "EXECUTE s; DEALLOCATE PREPARE s;"
        cur.execute(q)
        list_tables = cur.fetchall()

        for table, count in list_tables:
            if table in check_count_data and count != check_count_data[table]:
                isOkMigration = False
                print("- [ERR] -> {0} -> [SQLite ({1}) / MySQL ({2})] = {3}".format(table, check_count_data[table], count, check_count_data[table] - count))
            else:
                print("- [OK] -> {0}".format(table))

        cur.close()
        cur = None

        if isOkMigration == True:
            print ("Check Migartion OK! :)")
        else:
            print ("Migartion Failed!!! ;,,(")

def _mysql_tables_clean():
    global mysql_conn
    global check_count_data

    print ("Clean tables...")
    if mysql_conn is not None:
        cur = mysql_conn.cursor()

        # TODO: Pendiente ver por que si no se vacia __EFMigrationsHistory no se importan todos los datos correctamente!!!!!!

        #Retorna datos no fiables, en ocasiones dice que hay 0 registros y si tiene registros.
        #q = "SELECT table_name, table_rows FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{0}';".format(mysql_cfg['db'])

        q = "SET group_concat_max_len = 1024 * 1024 * 100;"
        q += "SELECT CONCAT('SELECT * FROM (',GROUP_CONCAT(CONCAT('SELECT ',QUOTE(tb),' `Table`, COUNT(1) `Rows` FROM ',db,'.',tb) SEPARATOR ' UNION '),') A "
        q += "ORDER BY "
        #q += "`Table` = \"__EFMigrationsHistory\" DESC, "
        #q += "`Table` = \"AspNetUsers\" DESC, `Table` = \"ChildRequests\" DESC, `Table` = \"MovieRequests\" DESC, ";
        #q += "`Table` = \"Issues\" DESC, `Table` = \"IssueComments\" DESC, `Table` = \"IssueCategory\" DESC, ";
        #q += "`Table` = \"EmbyContent\" DESC, `Table` =  \"EmbyEpisode\" DESC, ";
        #q += "`Table` = \"PlexServerContent\" DESC, `Table` = \"PlexSeasonsContent\" DESC, `Table` = \"PlexEpisode\" DESC, ";
        q += "`Table` ASC ";
        q += ";')"
        q += "INTO @sql FROM (SELECT table_schema db,table_name tb FROM information_schema.tables WHERE table_schema = DATABASE()) A;"
        q += "PREPARE s FROM @sql;"
        cur.execute(q)

        # Si se ejecuta todo en el mismo execute no retorna datos!
        q = "EXECUTE s; DEALLOCATE PREPARE s;"
        cur.execute(q)
        list_tables = cur.fetchall()

        # Desactivamos la comprobacion de tablas relacionadas.
        cur.execute("SET FOREIGN_KEY_CHECKS = 0;")

        for table, count in list_tables:
            if table in mysql_list_tables_no_clean:
                print("- [NOT CLEAN] -> {0}".format(table))
                check_count_data[table] = count
                continue
            else:
                if count == 0:
                    print("- [EMPTY] -> {0}".format(table))
                    continue
                else:
                    print("- [CLEANING] -> {0} -> rows: {1}".format(table, count))
                    try:
                        q = "TRUNCATE TABLE `{0}`;".format(table)
                        cur.execute(q)
                        mysql_conn.commit()
                        
                    except MySQLdb.Error, e:
                        #mysql_conn.rollback()
                        show_msg_err = True
                        try:
                            str_msg = "* MySQL Error [%d]: %s" % (e.args[0], e.args[1])
                        except IndexError:
                            str_msg = "* MySQL Error: %s" % str(e)
                        
                        mysql_list_error.append(str_msg)
                        mysql_list_error.append(q)
                        if show_msg_err:
                            print str_msg
                            print "* Query: {0}".format(q)
                

        # Volvemos a activar la comprobacion de tablas relacionadas.
        cur.execute("SET FOREIGN_KEY_CHECKS = 1;")

        mysql_conn.commit()
        cur.close()
        cur = None

def _mysql_database_json_update(opts):
    json_data = {}
    for db_name in list_db:
        json_data[db_name] = {
            "Type": "MySQL",
            "ConnectionString": "Server={0};Port={1};Database={2};User={3};Password={4}".format(mysql_cfg['host'], mysql_cfg['port'], mysql_cfg['db'], mysql_cfg['user'], mysql_cfg['passwd'])
        }
    json_mysql = _get_path_file_in_conf(json_file_database)
    _save_json(json_mysql, json_data)

def _sqlite_dump(opts):
    print("Dump SQLite:")
    for db_name in list_db_process:
        sys.stdout.write("- Exporting ({0})... ".format(db_name))
        connection_str=_find_in_json(json_db_data, [db_name, 'ConnectionString'])
        if connection_str.split("=")[0].lower() != "data source":
            print ("Warning: {0} no location data source, ignorer database!".format(db_name))
            continue

        yield('--')
        yield('-- DataBase: %s;' % db_name)
        yield('--')

        sqlite_db_file =  connection_str.split("=")[1]
        con = sqlite3.connect(sqlite_db_file)
        for line in _iterdump(con, db_name):
            yield line
        print ("OK!")

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
    for table_name, type in schema_res.fetchall():
        if table_name not in check_count_data:
            check_count_data[table_name] = 0

        if table_name in ['sqlite_sequence', 'sqlite_stat1'] or table_name.startswith('sqlite_'):
            continue
        elif cu.execute("SELECT COUNT(*) FROM {0}".format(table_name)).fetchone()[0] < 1:
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
            q_insert = row[0].encode('utf-8')
            q_insert = q_insert.replace('\\', '\\\\')
            q_insert = q_insert.replace('"', '\\"')

            #TODO: Lo dejo por si las moscas, pero casi seguro que sobra.
            #q_insert = q_insert.replace(",'t'", ",'1'")
            #q_insert = q_insert.replace(",'f'", ",'0'")

            q_insert = 'INSERT INTO `{0}` ({1}) VALUES({2})'.format(table_name, q_col, q_insert)
            check_count_data[table_name] += 1
            yield("%s;" % q_insert)

def _save_dump(opts, data):
    print ("Save dump:")
    dump_db_file =  _get_path_file_in_conf(mysql_db_file)
    _save_file(dump_db_file, data)

def _save_error_log(opts, data):
    if data is not None and len(data) > 0:
        print ("Save Log Error Mysql Insert:")
        log_file =  _get_path_file_in_conf(mysql_log_err)
        _save_file(log_file, data)
    


def _OptionParser():
    global opts
    op = OptionParser()
    op.add_option('-c', '--config', default="/etc/Ombi", help="path folder config ombi, default /etc/Ombi")
    op.add_option('', '--host', help="host server mysql/mariadb, If empty, file is generated with inserts.")
    op.add_option('', '--port', type="int", default=3306, help="port server mysql/mariadb, default 3306")
    op.add_option('', '--db', default="Ombi", help="name database, default Ombi")
    op.add_option('', '--user', default="ombi", help="user name mysql/mariadb, default ombi")
    op.add_option('', '--passwd', default="", help="passwd mysql/mariadb, defalt empty")
    op.add_option('-f', '--force', action="store_true",  default=False, help="force to clean all tables")
    opts, args = op.parse_args()
    _OptionParser_apply()

def _OptionParser_apply():
    global mysql_list_tables_no_clean

    if opts.force:
        mysql_list_tables_no_clean = []



def main():
    global opts
    global check_count_data
    
    _OptionParser()
    
    _check_read_config()
    _check_config_mysql(opts)


    data_dump = []
    for line in _sqlite_dump(opts):
        data_dump.append(line)

    # Si no se aNaden da error al arrancar Ombi ya que intenta crear las tablas pero ya existen.
    data_dump.append("INSERT INTO `__EFMigrationsHistory` (`MigrationId`, `ProductVersion`) VALUES ('20191103213915_Inital', '2.2.6-servicing-10079');")
    data_dump.append("INSERT INTO `__EFMigrationsHistory` (`MigrationId`, `ProductVersion`) VALUES ('20191103205915_Inital', '2.2.6-servicing-10079');")
    data_dump.append("INSERT INTO `__EFMigrationsHistory` (`MigrationId`, `ProductVersion`) VALUES ('20191102235852_Inital', '2.2.6-servicing-10079');")
    check_count_data['__EFMigrationsHistory'] += 3

    if 1 == 1:
        _save_dump(opts, data_dump)
    else:
        print (line)

    if mysql_cfg is not None:
        _mysql_connect()
        _mysql_tables_clean()

        
        #time.sleep(5)

        _mysql_migration(data_dump)
        _mysql_migration_check()
        _mysql_disconnect()

        _mysql_database_json_update(opts)
        _save_error_log(opts, mysql_list_error)        


if __name__ == "__main__":
    print("Migration tool by SQLite to MySql/MariaDB for ombi (3.0) By VSC55")
    print("")
    main()
