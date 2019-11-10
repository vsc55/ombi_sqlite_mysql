#! /usr/bin/env python
# Source https://github.com/tutorialpython/sqlite2mysql
# Fix Ombi
import sys
import os
import codecs
import json
import subprocess
import sqlite3
from optparse import OptionParser


IGNOREDPREFIXES = [
    'PRAGMA',
    'BEGIN TRANSACTION;',
    'COMMIT;',
    'DELETE FROM sqlite_sequence;',
    'INSERT INTO "sqlite_sequence"',
    'INSERT OR REPLACE INTO "sqlite_sequence"',
]

json_db_file = ""
json_db_data = []
list_db = ['OmbiDatabase', 'SettingsDatabase', 'ExternalDatabase']
list_db_process = []

def _replace(line):
    if any(line.startswith(prefix) for prefix in IGNOREDPREFIXES):
        return
    line = line.replace("INTEGER PRIMARY KEY", "INTEGER AUTO_INCREMENT PRIMARY KEY")
    line = line.replace("AUTOINCREMENT", "AUTO_INCREMENT")
    line = line.replace("DEFAULT 't'", "DEFAULT '1'")
    line = line.replace("DEFAULT 'f'", "DEFAULT '0'")
    line = line.replace(",'t'", ",'1'")
    line = line.replace(",'f'", ",'0'")
    line = line.replace("INSERT OR REPLACE INTO", "INSERT INTO")
    return line

def _backticks(line, in_string):
    """Replace double quotes by backticks outside (multiline) strings

    >>> _backticks('''INSERT INTO "table" VALUES ('"string"');''', False)
    ('INSERT INTO `table` VALUES (\\'"string"\\');', False)

    >>> _backticks('''INSERT INTO "table" VALUES ('"Heading''', False)
    ('INSERT INTO `table` VALUES (\\'"Heading', True)

    >>> _backticks('''* "text":http://link.com''', True)
    ('* "text":http://link.com', True)

    >>> _backticks(" ');", True)
    (" ');", False)

    """
    new = ''
    for c in line:
        if not in_string:
            if c == "'":
                in_string = True
            elif c == '"':
                new = new + '`'
                continue
        elif c == "'":
            in_string = False
        new = new + c
    return new, in_string

def _process(opts, lines):
    in_string = False
    for line in lines:
        if not in_string:
            line = _replace(line)
            if line is None:
                continue
        line, in_string = _backticks(line, in_string)
        yield line

def _read_json(file_json, def_return=None):
    return_date = def_return
    if os.path.isfile(file_json):
        try:
            f = codecs.open(file_json, 'r', 'utf-8')
            return_date = json.loads(f.read())
            f.close()
        except Exception as e:
            print("Exception read json ({$1}):".format(file_json), e)
    return return_date

def _save_json(file_json, data):
    try:
        f = codecs.open(file_json, 'w', 'utf-8')
        f.write(json.dumps(data))
        f.close()
    except Exception as e:
        print("Exception save json ({$1}):".format(file_json), e)
        return False
    return True

def _check_read_config(opts):
    global json_db_data
    global list_db_process

    if not opts.config:
        print("Not select config path!!")
        sys.exit()
    elif not os.path.isdir(opts.config):
        print ("The config path does not exist or is not a directory !!")
        sys.exit()
    
    json_db = os.path.join(opts.config, "database.json")
    if not os.path.isfile(json_db):
        print("File {0} not exist!!!".format(json_db))
        sys.exit()
        
    json_db_data = _read_json(json_db)
    if json_db_data is None:
        print ("Not data json read!!!!")
        sys.exit()
    
    list_db_process = []
    print("Check database.json:")
    for db_name in list_db:
        if json_db_data[db_name]['Type'].lower() == "sqlite":
            list_db_process.append(db_name)
            print("- {0} [SQLite]".format(db_name))
        else:
            pass
            #print("- {0} [MYSQL]".format(db_name))
    
    if len(list_db_process) == 0:
        print ("")
        print ("It is not necessary to update all databases are migrated.")
        sys.exit()

def _sqlite_dump(opts):
    print("Dump SQLite:")
    for db_name in list_db_process:
        sys.stdout.write("- Exporting ({0})... ".format(db_name))
        connection_str=json_db_data[db_name]['ConnectionString']
        if connection_str.split("=")[0].lower() != "data source":
            print ("Warning: {0} no location data source, ignorer database!".format(db_name))
            continue

        sqlite_db_file =  connection_str.split("=")[1]
        con = sqlite3.connect(sqlite_db_file)
        for line in _process(opts, _iterdump(con)):
            yield line
        print ("OK!")

def _iterdump(connection):
    cu = connection.cursor()

    q = """
       SELECT name, type, sql
        FROM sqlite_master
            WHERE sql NOT NULL AND
            type == 'table'
            ORDER BY "name"
        """
    
    schema_res = cu.execute(q)
    for table_name, type, sql in schema_res.fetchall():
        if table_name in ['sqlite_sequence', 'sqlite_stat1'] or table_name.startswith('sqlite_'):
            continue
        else:
            pass
            #Ignorer CREATE TABLE
            #yield('%s;' % sql)


        # TODO: Pendiente agrupar insert para una exportacion mas rapida.

        # Build the insert statement for each row of the current table
        res = cu.execute("PRAGMA table_info('%s')" % table_name)
        column_names = [str(table_info[1]) for table_info in res.fetchall()]

        q_col = ""
        for col_n in column_names:
            if len(q_col) > 0:
                q_col += ", "
            q_col += '`{0}`'.format(col_n)

        q = "SELECT 'INSERT INTO `%(tbl_name)s` (%(col_name)s) VALUES("
        q += ",".join(["'||quote(" + col + ")||'" for col in column_names])
        q += ")' FROM '%(tbl_name)s'"
        query_res = cu.execute(q % {'tbl_name': table_name, 'col_name':q_col })

        for row in query_res:
            yield("%s;" % row[0])

def _save_dump(opts, data):
    print ("Save dump:")
    dump_db_file =  os.path.join(opts.config, "data_ombi.mysql")
    sys.stdout.write("- Keeping in ({0})... ".format(dump_db_file))
    try:
        with open(dump_db_file, 'w') as f:
            for line in data:
                f.write('%s\n' % line.encode('utf-8').strip())
        
    except IOError as ex:
        print(" ERROR!")
        print("I/O error({0}): {1}".format(ex.errno, ex.strerror))
    except:
        print(" ERROR!")
        print("Unexpected error:", sys.exc_info()[0])
    else:
        print("OK!")


def dump(obj):
  for attr in dir(obj):
    print("obj.%s = %r" % (attr, getattr(obj, attr)))


def main():
    op = OptionParser()
    op.add_option('-c', '--config')
    op.add_option('-d', '--database')
    op.add_option('-u', '--username')
    op.add_option('-p', '--password')
    opts, args = op.parse_args()

    _check_read_config(opts)
    
    data_dump = []
    for line in _sqlite_dump(opts):
        data_dump.append(line)

    if 1 == 1:
        _save_dump(opts, data_dump)
    else:
        for line in data_dump:
            print (line)

if __name__ == "__main__":
    main()
