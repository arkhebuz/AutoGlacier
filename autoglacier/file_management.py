"""
# Dodawanie plików

`autoglacier register --database=/path/to/database.sqlite --filelist /path/to/list`

"""
import os
import time
import glob
import sqlite3

import pandas as pd # REQUIRES SQLALCHEMY for direct SQLite read?

from autoglacier.database import AGDatabase


def register_file_list(argparse_args):
    DB = AGDatabase(argparse_args.database)
    DB.connect()
    fm = FileManager(DB, argparse_args.configid)
    fm.read_file_list(argparse_args.filelist)
    fm.register_files()
    DB.close()
    


class FileManager(object):
    ''' Registers/deregisters paths in AutoGlacier database '''
    def __init__(self, ag_database, configuration_set_id=0):
        self.DB = ag_database
        self.CONFIG = self.DB.read_config_from_db(set_id=configuration_set_id)
        self.DATABASE_PATH = self.DB.database_path
        self.TIMESTAMP = time.time()
        self.files = []

    def _glob_dirs(self, list_of_globs):
        # TODO: nested dirs? - cannot hash folder
        for adir in list_of_globs:
            self.files = self.files + list(glob.iglob(adir))
            
    def read_file_list(self, list_path):
        """ Reads list of files from text file, one absolute path per line
        
        `list_path` - absolute path to file containing path list"""
        with open(list_path, 'r') as f:
            for line in f.readlines():
                self.files.append(line.strip())
    
    def register_files(self):
        """ Registers files stored in FileManager.files list
        
        FileManager.files will be prepared by execution of following methods:
            `FileManager.read_file_list`
        
        The effect of method execution is additive.
        """
        values2d = []
        for afile in self.files:
            values2d.append((os.path.abspath(afile), self.TIMESTAMP, 1, 1))
        
        sql = 'INSERT OR IGNORE INTO Files (abs_path, registration_date, file_exists, registered) VALUES (?, ?, ?, ?)'
        self.DB.change_many(sql, values2d)


