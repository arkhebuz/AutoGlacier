import os
import time
import glob
import sqlite3



class FileManager(object):
    ''' some prototype'''
    def __init__(self, CONFIG):
        self.files = []
        self.CONFIG = CONFIG
        self.TIMESTAMP = time.time()

    def _glob_dirs(self, list_of_globs):
        # TODO: nested dirs? - cannot hash folder
        for adir in list_of_globs:
            self.files = self.files + list(glob.iglob(adir))
    
    def _register_files(self):
        ag_database = os.path.join(self.CONFIG['AG_DATABASE_DIR'], 'AG_database.sqlite')
        conn = sqlite3.connect(ag_database)
        c = conn.cursor()
        
        values2d = []
        for afile in self.files:
            values2d.append((os.path.abspath(afile), self.TIMESTAMP, 1, -1, 1))
            #~ modtime = os.path.getmtime(afile)
            # calculate hash - memory inefficient method
            #~ with open(afile, 'rb') as f:
                #~ filehash = hashlib.sha512(f.read()).hexdigest()
            #~ SHA512=filehash
        
        c.executemany( ('INSERT OR IGNORE INTO Files ('
                       +'abs_path, registration_date, file_exists, last_backed, registered'
                       +') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'), values2d)
        conn.commit()
