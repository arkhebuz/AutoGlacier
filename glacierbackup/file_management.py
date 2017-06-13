"""
File registration/deregistration routines
"""
import os
import time
import glob
import sqlite3
import logging

from glacierbackup.database import GBDatabase


def register_file_list(argparse_args):
    DB = GBDatabase(argparse_args.database)
    DB.connect()
    fm = FileManager(DB, argparse_args.configid)
    fm.read_file_list(argparse_args.filelist)
    fm.register_files()
    DB.close()



class FileManager(object):
    ''' Registers paths in GlacierBackup database 
    
    Possibe file registration methods:
        [ ] direct path to files
        [x] text file with list of file paths: FileManager.read_file_list
        [ ] single-level glob
        [ ] tree glob
        [ ] directory
        [ ] directory recursively
        [ ] directory with exclusions
        [ ] various find options
        
    TBD functionality:
        [ ] database data viewing and analysis
        [ ] deregistering files
        [ ] missing files handling
    
    ([x] - done / [ ] - future option)
    '''
    def __init__(self, ag_database, configuration_set_id=0):
        self.DB = ag_database
        self.CONFIG = self.DB.read_config_from_db(set_id=configuration_set_id)
        self.DATABASE_PATH = self.DB.database_path
        self.logger = logging.getLogger("FileManagerLogger")
        self.TIMESTAMP = time.time()
        self.files = []

    def _glob_dirs(self, list_of_globs):
        # TODO: nested dirs
        for adir in list_of_globs:
            self.files = self.files + list(glob.iglob(adir))
            
    def read_file_list(self, list_path):
        """ Reads list of files from text file, one absolute path per line
        
        `list_path` - absolute path to file containing path list"""
        with open(list_path, 'r') as f:
            for line in f.readlines():
                line = line.strip()
                if os.path.isfile(line):
                    self.files.append(line)
                else:
                    self.logger.warning("Not a file or file not found: %s", line)
    
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


