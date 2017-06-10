import pytest
import json
import os
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from autoglacier.ag_command import _construct_argparse_parser
from autoglacier.jobs import BackupJob
from autoglacier.database import AGDatabase, AGDatabaseError



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
        cls.database_dir = os.path.join(os.path.expanduser('~'), '.autoglacier/__TESTS')
        tmp_dir = os.path.join(cls.database_dir, 'TMP')
        try:
            os.makedirs(tmp_dir)
        except FileExistsError:
            pass
        cls._cnf =  {
                  "set_id" : 0,
                  "compression_algorithm" : "lzma",
                  "temporary_dir": tmp_dir,
                  "ag_database_dir": cls.database_dir,
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


class TestAGDatabase(TemplateSetupTeardown):
    with open("__keys.json", 'r') as f:
        keys = json.load(f)
    
    def test_operation_protection_on_disconnected_database(self):
        DB = AGDatabase(os.path.join(self.database_dir, 'AG_database.sqlite'))
        with pytest.raises(AGDatabaseError):
            DB.change('Select * from Jobs')
        
    def test_database_initialization(self):
        DB = AGDatabase(os.path.join(self.database_dir, 'AG_database.sqlite'))
        DB.initialize(self._cnf)
        with pytest.raises(AGDatabaseError):
            CONFIG = DB.read_config_from_db(set_id=0)
        
        DB.connect()
        CONFIG = DB.read_config_from_db(set_id=0)
        for k in self._cnf.keys():
            assert CONFIG[k] == self._cnf[k]



@pytest.mark.incremental
class TestsFunctional(TemplateSetupTeardown):
    """Possible test scenarios often depend on the AG Database state,
    which is created and altered by executing actions/test cases
    earlier. They also simultaniusly depend on the files (i.e.
    backed_files -> archive -> encryped_archive). This could be mitigated
    by preparing entire state from scratch, independently from autoglacier
    funcionality, by writing custom straight-to-the-state setups or state
    injection. However it would require substantial effort at the very 
    early stage of development when things are mostly in flux, so a fixed 
    sequence of rather functional than strictly unit tests is used for now.
    
    Note that the test order below roughly mimics how autoglacier would
    be used from CLI. """
    with open("__keys.json", 'r') as f:
        keys = json.load(f)
        
    def test_initialization_from_cmd_args(self):
        parser = _construct_argparse_parser()
        args = parser.parse_args(['init', '--genkeys', self.sample_conf_file])
        args.func(args)
        
        DB = AGDatabase(os.path.join(self.database_dir, 'AG_database.sqlite'))
        DB.connect()
        CONFIG = DB.read_config_from_db()
        
        assert CONFIG['vault_name'] == self._cnf['vault_name']
        assert CONFIG['ag_database_dir'] == self._cnf['ag_database_dir']
        assert CONFIG['temporary_dir'] == self._cnf['temporary_dir']
        assert len(CONFIG['public_key']) > 100      # TODO: Should do better...
        assert os.path.isfile(os.path.join(self.database_dir, 'AG_RSA_private.pem'))
        
    def test_registering_files_by_file_list(self):
        database_path = os.path.join(self.database_dir, 'AG_database.sqlite')
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
        database_path = os.path.join(self.database_dir, 'AG_database.sqlite')
        self.__class__.DB = AGDatabase(database_path)
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
        self.__class__.BJ.archive_files()
        
    def test_archive_decryption(self):
        pass
        
    def test_backup_job_upload_into_glacier(self):
        database_path = os.path.join(self.database_dir, 'AG_database.sqlite')
        parser = _construct_argparse_parser()
        args = parser.parse_args(['job', '--database', database_path])
        #~ args.func(args)
