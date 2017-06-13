import sqlite3
import logging
import os



class GBDatabaseError(Exception):
    pass

class GBDatabase(object):
    """ Object handling GlacierBackup SQLite database creation and interaction with."""
    class _ConnectionStub(object):
        """ This class provides a default shim for internal GBDatabase variables 
        (GBDatabase_db_connection and GBDatabase._db_cursor) allowing for a gentle
        GBDatabase instance destruction if no database connection was ever 
        established, or established connection was closed manually.
        """
        def __getattribute__(self, attr):
            if attr == 'close':
                def f(): pass
                return f
            else:
                raise GBDatabaseError("Database Connection Not Initialized")
        
    def __init__(self, database_path):
        self.database_path = database_path
        self._logger = logging.getLogger("DatabaseLogger")
        self._db_cursor = self._ConnectionStub()
        self._db_connection = self._ConnectionStub()
    
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, *args):
        self.close()

    def connect(self):
        self._db_connection = sqlite3.connect(self.database_path)
        self._db_cursor = self._db_connection.cursor()
        try:
            # TODO: better checks
            self._db_cursor.execute('SELECT job_id FROM BackupJobs')
            self._db_cursor.execute('SELECT abs_path FROM Backups')
            self._db_cursor.execute('SELECT abs_path FROM Files')
        except sqlite3.OperationalError:
            self._logger.exception( ("Wrong path to database or database structure "
                                    +"was corrupted (path: %s)"), self.database_path)
            raise
        
    def initialize(self, config):
        """ Initiates empty database with `config` in ConfigurationSets table 
        
        Database structure is not altered in other places of the program.
        This method code can serve as a database structure specification.
        """
        if not os.path.isfile(self.database_path):
            self._db_connection = sqlite3.connect(self.database_path)
            self._db_cursor = self._db_connection.cursor()
            c = self._db_cursor
            
            c.execute( ('CREATE TABLE Files ('
                       +'abs_path           TEXT PRIMARY KEY NOT NULL, '
                       +'registration_date  INT NOT NULL, '
                       +'file_exists        INT NOT NULL, '
                       +'registered         INT)') )
            #~ c.execute( 'CREATE INDEX abs_path_index ON Files (abs_path)' )
            
            c.execute( ('CREATE TABLE Backups ('
                       +'abs_path       TEXT NOT NULL, '
                       +'mod_date       INT NOT NULL, '
                       +'sha256         TEXT NOT NULL, '
                       +'job_id         INT NOT NULL, '
                       +'unique (abs_path, mod_date, sha256, job_id) )') )
            
            c.execute( ('CREATE TABLE BackupJobs ('
                       +'job_id                 INT PRIMARY KEY NOT NULL, '
                       +'configuration_set_id   INT NOT NULL, '
                       +'timestamp              INT NOT NULL, '
                       +'description            TEXT NOT NULL, '
                       +'archive_size           INT NOT NULL, '
                       +'archive_checksum       TEXT NOT NULL, '
                       +'location               TEXT NOT NULL, '
                       +'response               TEXT, '
                       +'archive_id             TEXT NOT NULL, '
                       +'success                INT NOT NULL, '
                       +'errors_message         TEXT)') )
            
            c.execute( ('CREATE TABLE ConfigurationSets ('
                       +'set_id                 INT PRIMARY KEY NOT NULL, '
                       +'region_name            TEXT NOT NULL, '
                       +'vault_name             TEXT NOT NULL, '
                       +'public_key             TEXT NOT NULL, '
                       +'compression_algorithm  TEXT NOT NULL, '
                       +'temporary_dir          TEXT NOT NULL, '
                       +'database_dir           TEXT NOT NULL, '
                       +'aws_access_key_id      TEXT, '
                       +'aws_secret_access_key  TEXT, '
                       +'regular_runtime_params TEXT )') )
            
            self.insert_configuration_set(config)
            self._db_connection.commit()
            self._db_connection.close()
            self._db_cursor = self._ConnectionStub()
            self._db_connection = self._ConnectionStub()
        else:
            self._logger.warning("DATABASE FILE ALREADY EXISTS UNDER %s, ABORTING INITIALIZATION", self.database_path)
            # TODO: rethink this

    def insert_configuration_set(self, config):
        ''' 
        config - configuration set in JSON representation
        db_cursor - open GB database cursor'''
        try:
            values = (config['set_id'], 
                      config['region_name'], 
                      config['vault_name'], 
                      config['public_key'], 
                      config['compression_algorithm'], 
                      config['temporary_dir'], 
                      config['database_dir'], 
                      config['aws_access_key_id'], 
                      config['aws_secret_access_key'])
        except KeyError:
            self._logger.error('pls fix conf')
            raise
            
        self._db_cursor.execute( ('INSERT INTO ConfigurationSets ('
                                 +'set_id, region_name, vault_name, public_key, compression_algorithm, '
                                 +'temporary_dir, database_dir, aws_access_key_id, aws_secret_access_key'
                                 +') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'), values)

    def read_config_from_db(self, set_id=0):
        self._db_cursor.close()
        self._db_connection.row_factory = sqlite3.Row
        self._db_cursor = self._db_connection.cursor()
        
        self._db_cursor.execute( 'SELECT * FROM ConfigurationSets WHERE set_id=?', (set_id,) )
        CONFIG = self._db_cursor.fetchone()
        
        self._db_cursor.close()
        self._db_connection.row_factory = None
        self._db_cursor = self._db_connection.cursor()
        
        return CONFIG
    
    def fetch_row(self, *args):
        self._db_cursor.execute(*args)
        return self._db_cursor.fetchone()
        
    def fetch_all(self, *args):
        self._db_cursor.execute(*args)
        return self._db_cursor.fetchall()
    
    def change(self, *args):
        self._db_cursor.execute(*args)
        self._db_connection.commit()
        
    def change_many(self, *args):
        self._db_cursor.executemany(*args)
        self._db_connection.commit()
        
    def __del__(self):
        self.close()
        
    def close(self):
        self._db_cursor.close()
        self._db_connection.close()
        self._db_cursor = self._ConnectionStub()
        self._db_connection = self._ConnectionStub()

