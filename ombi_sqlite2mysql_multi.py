#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Migration tool from SQLite to Multi MySql/MariaDB for ombi
#
# Copyright © 2020  Javier Pastor (aka VSC55)
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
__copyright__ = "Copyright © 2020, Javier Pastor"
__credits__ = "Javier Pastor"
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = 'Javier Pastor'
__email__ = "python@cerebelum.net"
__status__ = "Development"

import sys
import os
import importlib
import time
import datetime
import json
import ombi_sqlite2mysql
from optparse import OptionParser
from distutils.version import StrictVersion


python_version = None
ombi_sqlite2mysql_version = "3.0.4"
json_file_database_multi = "database_multi.json"
json_file_migration = "migration.json"
json_file_database = "database.json"

list_db = {'OmbiDatabase':'Ombi.db', 'SettingsDatabase':'OmbiSettings.db', 'ExternalDatabase':'OmbiExternal.db'}

opts = None
opt = {
    'config': None,
    'no_backup': False,
    'force': False,
    'save_dump': False
}


class Switch:

    """ Main Class. """

    def __init__(self, value, invariant_culture_ignore_case=False, check_isinstance=False, check_contain=False):
        """ The switch is initialized and configured as it will act.

        :param value: Value against which comparisons will be made.
        :param invariant_culture_ignore_case: If it is set to True and the type of value to be compared is a String,
        the difference between uppercase and lowercase will be ignored when doing the verification.
        :param check_isinstance: If set to True, the check will not be content value but the type of object it is.
        :param check_contain: If it is true, it will check if the value that is specified is part of the text that
        we check.

        """
        self.value = value
        self.invariant_culture_ignore_case = invariant_culture_ignore_case
        self.check_isinstance = check_isinstance
        self.check_contain = check_contain

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        # Allows a traceback to occur
        return False

    def __call__(self, *values):
        """ Check if any of the values passed to you match the value that was defined when the object was created.

        :param values: List of values that are compared to the value specified when creating the switch.
        :return: True if any of the values that have been passed match, False if none matches.

        """
        if self.check_isinstance:
            # Efectúa check isinstance
            for item in values:
                if isinstance(self.value, item):
                    return True
            return False

        elif isinstance(self.value, str):
            for item in values:
                if isinstance(item, str):
                    if self.invariant_culture_ignore_case:
                        # Comparativa ignorando Mayúsculas y Minúsculas.
                        tmp_item = item.lower()
                        tmp_value = self.value.lower()
                    else:
                        tmp_item = item
                        tmp_value = self.value

                    if self.check_contain:
                        # Comprueba si el item esta dentro del valor.
                        if tmp_item in tmp_value:
                            return True
                    else:
                        # Comprueba si el item es igual valor.
                        if tmp_item == tmp_value:
                            return True

        return self.value in values



def _get_path_file_in_conf(file_name):
    if opt['config'] and file_name:
        return os.path.join(opt['config'], file_name)
    else:
        return ""


def _OptionParser():
    global opts
    op = OptionParser()
    op.add_option('-c', '--config', default="/etc/Ombi", help="Path folder config ombi, default /etc/Ombi.")
    op.add_option('', '--no_backup', action="store_true",  default=False, help="Disable the backup of the \"__EFMigrationsHistory\" table.")
    op.add_option('', '--force', action="store_true",  default=False, help="Force clear all tables.")
    op.add_option('', '--save_dump', action="store_true",  default=False, help="Save all query insert in the file.")
    opts, _ = op.parse_args()
    return _OptionParser_apply()

def _OptionParser_apply():
    global opt
    opt['config']       = opts.config
    opt['force']        = opts.force
    opt['no_backup']    = opts.no_backup
    opt['save_dump']    = opts.save_dump
    
    ombi_sqlite2mysql._set_conf('config', opt['config'])
    ombi_sqlite2mysql._set_conf('force', opt['force'])
    ombi_sqlite2mysql._set_conf('no_backup', opt['no_backup'])
    ombi_sqlite2mysql._set_conf('save_dump', opt['save_dump'])
    
    if opt['force']:
        ombi_sqlite2mysql._clean_list_tables_skip_clean()

    if opt['no_backup']:
        ombi_sqlite2mysql._clean_list_tables_backup()

    return True

def main():
    json_db         = _get_path_file_in_conf(json_file_database)
    json_db_multi   = _get_path_file_in_conf(json_file_database_multi)
    json_migration  = _get_path_file_in_conf(json_file_migration)    

    if not os.path.isfile(json_db_multi):
        print("Error: File {0} not exist!!!".format(json_db_multi))
        return False
        
    json_db_multi_data = ombi_sqlite2mysql._read_json(json_db_multi)
    if json_db_multi_data is None:
        print ("Error: No data has been read from the json ({0}) file, please review it.!!!!".format(json_db_multi))
        return False
    

    for key, value in json_db_multi_data.items():
        
        if not key in list_db:
            print("- DataBase ({0}) Skip: Name DataBase is not valid!".format(key))
            print("")
            continue

        opt_type    = None
        opt_connect = None
        opt_skip    = False
        opt_file    = _get_path_file_in_conf(list_db[key])

        mysql_host  = "localhost"
        mysql_port  = "3306"
        mysql_db    = "Ombi"
        mysql_user  = "ombi"
        mysql_pass  = "ombi"

        for subkey, subval in value.items():
            with Switch(subkey, invariant_culture_ignore_case=True) as case:
                if case("Type"):
                    if subval:
                        opt_type = str(subval).lower()

                elif case("ConnectionString"):
                    if subval:
                        opt_connect = str(subval)

                elif case("Skip"):
                    if subval:
                        opt_skip = bool(subval)
        

        if opt_type != "MySQL".lower():
            print("- DataBase ({0}) Skip: Type ({1}) not valid, only support MySQL!".format(key, opt_type))
            print("")
            continue
       
        if opt_skip:
            print("- DataBase ({0}) Skip: User defined Skip!".format(key))
            print("")
            continue

        if opt_connect is None:
            print("- DataBase ({0}) Skip: ConnectionString is null!".format(key))
            print("")
            continue
        else:
            opt_connect_data = opt_connect.split(";")
            for val in opt_connect_data:
                item_data = val.split("=", 1)
                item_key = item_data[0]
                item_val = item_data[1]

                with Switch(item_key, invariant_culture_ignore_case=True) as case:
                    if case("Server"):
                        if item_val:
                            mysql_host = str(item_val)

                    elif case("Port"):
                        if item_val:
                            mysql_port = int(item_val)

                    elif case("Database"):
                        if item_val:
                            mysql_db = str(item_val)

                    elif case("User"):
                        if item_val:
                            mysql_user = str(item_val)

                    elif case("Password"):
                        if item_val:
                            mysql_pass = str(item_val)

        print("- Processing DataBase ({0})...".format(key))
        print("  -------------------")
        print("")
        json_migration_data = {
            key: {  
                "ConnectionString": "Data Source={0}".format(opt_file),
                "Type": "sqlite"
            } 
        }
        
        new_cfg = {
            'host': mysql_host,
            'port': mysql_port,
            'db': mysql_db,
            'user': mysql_user,
            'passwd': mysql_pass,
            'connect_timeout': 2,
            'use_unicode': True,
            'charset': 'utf8'
        }
        ombi_sqlite2mysql._set_mysql_cfg(new_cfg)

        ombi_sqlite2mysql._save_json(json_migration, json_migration_data, True, True)

        # Forzamos a que los datos esten limpios para la siguiente ejecucion.
        ombi_sqlite2mysql._clean_end_process()
        
        ombi_sqlite2mysql.main()
        print("")
        print("----------------------------------------------------------------")
        print("----------------------------------------------------------------")
        print("")
        

    print("> Updating database.json...")
    ombi_sqlite2mysql._save_json(json_db, json_db_multi_data, True, True)
    print("")
    print("")

if __name__ == "__main__":
    print("Migration tool from SQLite to Multi MySql/MariaDB for ombi ({0}) By {1}".format(__version__, __author__))
    print("")

    if (sys.version_info > (3, 0)):
        python_version = 3
        ombi_sqlite2mysql.python_version = 3
    else:
        python_version = 2
        ombi_sqlite2mysql.python_version = 2
    
    if ( StrictVersion(ombi_sqlite2mysql.__version__) > StrictVersion(ombi_sqlite2mysql_version)):
        print("Error: Version ombi_sqlite2mysql is not valid, need {0} or high!!".format(ombi_sqlite2mysql_version))
        print("")
        os._exit(0)

    if not ombi_sqlite2mysql.load_MySQL_lib():
        os._exit(0)

    if not _OptionParser():
        os._exit(0)

    main()
