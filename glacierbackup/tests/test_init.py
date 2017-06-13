import pytest
import json
import os
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from glacierbackup.command import _construct_argparse_parser
from glacierbackup.jobs import BackupJob
from glacierbackup.database import GBDatabase, GBDatabaseError



def _create_test_backup_files_and_dirs(parent_dir):
    root_test_dir = os.path.join(parent_dir, '__test_backup_structure')
    os.mkdir(root_test_dir)
    
    dir1 = os.path.join(root_test_dir, 'dir1')
    os.mkdir(dir1)
    dir2 = os.path.join(root_test_dir, 'dir2')
    os.mkdir(dir2)
    for char in 'a10':
        for adir in (dir1, dir2):
            with open(os.path.join(adir, char), 'w') as f:
                f.write(char*10**5)
    
    file_list_loc = os.path.join(root_test_dir, '__test_backup_file_list.txt')
    paths = [root_test_dir+'/dir1/'+char for char in 'a10']
    paths += [root_test_dir+'/dir2/'+char for char in 'a10']
    with open(file_list_loc, 'w') as f:
        for p in paths:
            f.write(p)
            f.write('\n')
    return file_list_loc


class TemplateSetupTeardown(object):
    @classmethod
    def setup_class(cls):
        # Startup config
        cls.database_dir = os.path.join(os.path.expanduser('~'), '.glacierbackup/__TESTS')
        cls.database_path = os.path.join(cls.database_dir, 'GB_database.sqlite')
        tmp_dir = os.path.join(cls.database_dir, 'TMP')
        try:
            os.makedirs(tmp_dir)
        except FileExistsError:
            pass
        cls._cnf =  {
                  "set_id" : 0,
                  "compression_algorithm" : "lzma",
                  "temporary_dir": tmp_dir,
                  "database_dir": cls.database_dir,
                  "public_key": "None",
                  "region_name": "eu-west-1",
                  "vault_name": "TestVault1",
                  "aws_access_key_id": cls.keys["aws_access_key_id"],
                  "aws_secret_access_key": cls.keys["aws_secret_access_key"]
                }
        cls.sample_conf_file = os.path.join(cls.database_dir, '_init_conf.json')
        with open(cls.sample_conf_file, 'w') as f:
            json.dump(cls._cnf, f, indent=2)
        
        cls.list_of_files_path = _create_test_backup_files_and_dirs(cls.database_dir)
        
    @classmethod
    def teardown_class(cls):
        import shutil
        shutil.rmtree(cls.database_dir)


class TestGBDatabase(TemplateSetupTeardown):
    """ Tests directly glacierbackup.database.GBDatabase """
    with open("__keys.json", 'r') as f:
        keys = json.load(f)
    
    def teardown_method(self, method):
        if os.path.isfile(self.database_path):
            os.remove(self.database_path)
    
    def test_operation_protection_on_disconnected_database(self):
        DB = GBDatabase(self.database_path)
        with pytest.raises(GBDatabaseError):
            DB.change('Select * from Jobs')
        
    def test_database_initialization(self):
        DB = GBDatabase(self.database_path)
        DB.initialize(self._cnf)
        with pytest.raises(GBDatabaseError):
            CONFIG = DB.read_config_from_db(set_id=0)
        
        DB.connect()
        CONFIG = DB.read_config_from_db(set_id=0)
        for k in self._cnf.keys():
            assert CONFIG[k] == self._cnf[k]
        
    def test_multiple_close_calls(self):
        DB = GBDatabase(self.database_path)
        DB.initialize(self._cnf)
        # Should rise no errors
        DB.close()
        DB.connect()
        DB.close()
        DB.close()
        DB.close()
        del DB
    
    def test_writing_to_Files(self):
        DB = GBDatabase(self.database_path)
        DB.initialize(self._cnf)
        with DB:
            v = ('abs', 1, 0, 1)
            DB.change('INSERT INTO Files (abs_path, registration_date, file_exists, registered) VALUES (?,?,?,?)', v)
            
        with GBDatabase(self.database_path) as DB:
            row = DB.fetch_row('SELECT * FROM Files WHERE abs_path=?', (v[0],))
            for i, val in enumerate(row):
                assert v[i] == val

    def test_writing_two_identical_abs_path_to_Files(self):
        DB = GBDatabase(self.database_path)
        DB.initialize(self._cnf)
        with DB:
            v = ('abs', 1, 0, 1)
            DB.change('INSERT INTO Files (abs_path, registration_date, file_exists, registered) VALUES (?,?,?,?)', v)
            import sqlite3
            with pytest.raises(sqlite3.IntegrityError):
                DB.change('INSERT INTO Files (abs_path, registration_date, file_exists, registered) VALUES (?,?,?,?)', v)
        
    def test_writing_to_Backups(self):
        DB = GBDatabase(self.database_path)
        DB.initialize(self._cnf)
        with DB:
            vs = [('abs', 1, 'abc', 1),
                  ('abs', 2, 'ccc', 2),
                  ('abs', 3, 'ddd', 3),]
            DB.change_many('INSERT INTO Backups (abs_path, mod_date, sha256, job_id) VALUES (?,?,?,?)', vs)
            
        with GBDatabase(self.database_path) as DB:
            rows = DB.fetch_all('SELECT * FROM Backups')
            for written, read in zip(vs, rows):
                for v1, v2 in zip(written, read):
                    assert v1 == v2

    def test_writing_duplicates_to_Backups(self):
        DB = GBDatabase(self.database_path)
        DB.initialize(self._cnf)
        with DB:
            vs = [('abs', 1, 'abc', 1),
                  ('abs', 1, 'abc', 1),
                  ('abs', 1, 'abc', 1),]
            import sqlite3
            with pytest.raises(sqlite3.IntegrityError):
                DB.change_many('INSERT INTO Backups (abs_path, mod_date, sha256, job_id) VALUES (?,?,?,?)', vs)

    def test_writing_nonsense_to_Backups(self):
        DB = GBDatabase(self.database_path)
        DB.initialize(self._cnf)
        with DB:
            vs = [('abs', 1, 'abc', 1),
                  ('abs', 1, 'cba', 1),
                  ('abs', 3, 'abc', 1),]
            import sqlite3
            with pytest.raises(sqlite3.IntegrityError):
                DB.change_many('INSERT INTO Backups (abs_path, mod_date, sha256, job_id) VALUES (?,?,?,?)', vs)


@pytest.mark.incremental
class TestsFunctional(TemplateSetupTeardown):
    """Possible test scenarios often depend on the AG Database state,
    which is created and altered by executing actions/test cases
    earlier. They also simultaniusly depend on the files (i.e.
    backed_files -> archive -> encryped_archive). This could be mitigated
    by preparing entire state from scratch, independently from glacierbackup
    funcionality, by writing custom straight-to-the-state setups or state
    injection. However it would require substantial effort at the very 
    early stage of development when things are mostly in flux, so a fixed 
    sequence of rather functional than strictly unit tests is used for now.
    It still has the benefit of automated execution and can better pin down
    a faillure location.
    
    Note that the test order below roughly mimics how glacierbackup would
    be used from CLI. """
    with open("__keys.json", 'r') as f:
        keys = json.load(f)
        
    def test_initialization_from_cmd_args(self):
        parser = _construct_argparse_parser()
        args = parser.parse_args(['init', '--genkeys', self.sample_conf_file])
        args.func(args)
        
        DB = GBDatabase(os.path.join(self.database_dir, 'GB_database.sqlite'))
        DB.connect()
        CONFIG = DB.read_config_from_db()
        
        assert CONFIG['vault_name'] == self._cnf['vault_name']
        assert CONFIG['database_dir'] == self._cnf['database_dir']
        assert CONFIG['temporary_dir'] == self._cnf['temporary_dir']
        assert len(CONFIG['public_key']) > 100      # TODO: Should do better...
        assert os.path.isfile(os.path.join(self.database_dir, 'GB_RSA_private.pem'))
        
    def test_registering_files_by_file_list(self):
        database_path = os.path.join(self.database_dir, 'GB_database.sqlite')
        parser = _construct_argparse_parser()
        args = parser.parse_args(['register', '--database', database_path,
                                  '--filelist', self.list_of_files_path])
        args.func(args)
        
        import sqlite3
        conn = sqlite3.connect(database_path)
        c = conn.cursor()
        c.execute('SELECT * FROM FILES')
        files_in_db = c.fetchall()
        conn.close()
        
        assert len(files_in_db) == 6
        
    def test_backup_job_initialization(self):
        database_path = os.path.join(self.database_dir, 'GB_database.sqlite')
        self.__class__.DB = GBDatabase(database_path)
        self.__class__.DB.connect()
        self.__class__.BJ = BackupJob(self.__class__.DB, 'asdf')
                
    def test_backup_job_checkout_files(self):
        self.__class__.BJ.checkout_files()
        
    def test_backup_job_archive_packing(self):
        self.__class__.BJ.archive_files()
        assert os.path.isfile(self.__class__.BJ.archive)
        
    def test_backup_job_archive_contents(self):
        import tarfile
        tarf = tarfile.open(self.__class__.BJ.archive, 'r')
        with open(self.list_of_files_path, 'r') as f:
            paths1 = [s.strip() for s in f.readlines()]
            paths2 = ['/'+t for t in tarf.getnames()]
            for p in paths1:
                assert p in paths2
        
    def test_backup_job_encrypt_archive(self):
        self.__class__.BJ.encrypt_archive()
        assert os.path.isfile(self.__class__.BJ.encrypted_archive)
        
    def test_archive_decryption(self):
        pass
        
    def test_backup_job_upload_into_glacier(self):
        #~ self.__class__.BJ.upload_into_glacier()
        pass
