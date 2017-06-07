"""
# Dodawanie plików

`autoglacier register --database=/path/to/database.sqlite --filelist /path/to/list`

"""
import os
import time
import glob
import sqlite3

import pandas as pd # REQUIRES SQLALCHEMY for direct SQLite read?

from autoglacier.ag_misc import read_config_from_db


def register_file_list(argparse_args):
    CONFIG = read_config_from_db(argparse_args.database)
    fm = FileManager(CONFIG, argparse_args.database)
    fm.read_file_list(argparse_args.filelist)
    
    #~ fm._register_files()
    
    #~ dat = sqlite3.connect(argparse_args.database)
    #~ df = pd.DataFrame.from_records(dat, index=None, exclude=None, columns=None, coerce_float=False, nrows=None)
    # df = pd.read_sql_query("select * from Files;", dat)
    #~ print(df)
    #~ dat.close()



class FileManager(object):
    ''' some prototype '''
    def __init__(self, CONFIG, database_path):
        self.files = []
        self.CONFIG = CONFIG
        self.TIMESTAMP = time.time()
        self.DATABASE_PATH = database_path

    def _glob_dirs(self, list_of_globs):
        # TODO: nested dirs? - cannot hash folder
        for adir in list_of_globs:
            self.files = self.files + list(glob.iglob(adir))
            
    def read_file_list(self, list_path):
        with open(list_path, 'r') as f:
            for line in f.readlines():
                self.files.append(line.strip())
    
    def _register_files(self):
        conn = sqlite3.connect(self.DATABASE_PATH)
        c = conn.cursor()
        
        values2d = []
        for afile in self.files:
            values2d.append((os.path.abspath(afile), self.TIMESTAMP, 1, 1))
            #~ modtime = os.path.getmtime(afile)
            # calculate hash - memory inefficient method
            #~ with open(afile, 'rb') as f:
                #~ filehash = hashlib.sha512(f.read()).hexdigest()
            #~ SHA512=filehash
        
        c.executemany( ('INSERT OR IGNORE INTO Files ('
                       +'abs_path, registration_date, file_exists, registered'
                       +') VALUES (?, ?, ?, ?)'), values2d)
        conn.commit()
        conn.close()


