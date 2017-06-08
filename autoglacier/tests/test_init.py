import pytest
import json
import os
#~ import autoglacier


# Problem: test cases are highly coupled
#~ Possible test scenarios often depend on the AG_database state,
#~ which is created and altered by executing actions/test cases
#~ earlier. They also simultaniusly depend on the files (i.e.
#~ backed_files -> archive -> encryped_archive). This could be mitigated
#~ by enfocing execution order or by preparing entire state from scratch, 
#~ either by reusing autoglacier funcionality or by writing custom
#~ straight-to-the-state setups.
class TestInitialization(object):
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
                  "aws_access_key_id": " ",
                  "aws_secret_access_key": " "
                }
        cls.sample_conf_file = os.path.join(cls.database_dir, '_init_conf.json')
        with open(cls.sample_conf_file, 'w') as f:
            json.dump(cls._cnf, f, indent=2)
        
        from autoglacier.ag_misc import _create_test_backup_files_and_dirs
        cls.tbd_backup_files_list = _create_test_backup_files_and_dirs(cls.database_dir)
    
    @classmethod
    def teardown_class(cls):
        import shutil
        shutil.rmtree(cls.database_dir)
        
    def test_ag_import(self):
        import autoglacier.ag_init
         
    def test_initialization_from_cmd_args(self):
        from autoglacier.ag_command import _construct_argparse_parser
        parser = _construct_argparse_parser()
        args = parser.parse_args(['init', '--genkeys', self.sample_conf_file])
        args.func(args)
        
        from autoglacier.ag_misc import read_config_from_db
        CONFIG = read_config_from_db(os.path.join(self.database_dir, 'AG_database.sqlite'))
        
        assert CONFIG['vault_name'] == self._cnf['vault_name']
        assert CONFIG['ag_database_dir'] == self._cnf['ag_database_dir']
        assert CONFIG['temporary_dir'] == self._cnf['temporary_dir']
        assert len(CONFIG['public_key']) > 100      # Should do better...
        assert os.path.isfile(os.path.join(self.database_dir, 'AG_RSA_private.pem'))
        
    def test_registering_files_by_file_list(self):
        from autoglacier.ag_command import _construct_argparse_parser
        parser = _construct_argparse_parser()
        args = parser.parse_args(['init', '--genkeys', self.sample_conf_file])
        args.func(args)

        database_path = os.path.join(self.database_dir, 'AG_database.sqlite')
        parser = _construct_argparse_parser()
        args = parser.parse_args(['register', '--database', database_path,
                                  '--filelist', self.tbd_backup_files_list])
        args.func(args)
        
        import sqlite3
        conn = sqlite3.connect(database_path)
        c = conn.cursor()
        c.execute('SELECT * FROM FILES')
        files_in_db = c.fetchall()
        conn.close()
        
        assert len(files_in_db) == 6




class TestJobs(object):
    @classmethod
    def setup_class(cls):
        # Startup config
        cls.database_dir = os.path.join(os.path.expanduser('~'), '.autoglacier/__TESTS')
        tmp_dir = os.path.join(cls.database_dir, 'TMP')
        try:
            os.makedirs(tmp_dir)
        except FileExistsError:
            pass
        with open("__keys.json", 'r') as f:
            __keys = json.load(f)
        cls._cnf =  {
                  "set_id" : 0,
                  "compression_algorithm" : "lzma",
                  "temporary_dir": tmp_dir,
                  "ag_database_dir": cls.database_dir,
                  "public_key": "None",
                  "region_name": "eu-west-1",
                  "vault_name": "TestVault1",
                  "aws_access_key_id": __keys["aws_access_key_id"],
                  "aws_secret_access_key": __keys["aws_secret_access_key"]
                }
        cls.sample_conf_file = os.path.join(cls.database_dir, '_init_conf.json')
        with open(cls.sample_conf_file, 'w') as f:
            json.dump(cls._cnf, f, indent=2)
        
        from autoglacier.ag_misc import _create_test_backup_files_and_dirs
        cls.tbd_backup_files_list = _create_test_backup_files_and_dirs(cls.database_dir)
        
        from autoglacier.ag_command import _construct_argparse_parser
        parser = _construct_argparse_parser()
        args = parser.parse_args(['init', '--genkeys', cls.sample_conf_file])
        args.func(args)
        
        database_path = os.path.join(cls.database_dir, 'AG_database.sqlite')
        parser = _construct_argparse_parser()
        args = parser.parse_args(['register', '--database', database_path,
                                  '--filelist', cls.tbd_backup_files_list])
        args.func(args)

    #~ @classmethod
    #~ def teardown_class(cls):
        #~ import shutil
        #~ shutil.rmtree(cls.database_dir)

    def test_g(self):
        from autoglacier.ag_jobs import GTEU
        from autoglacier.ag_misc import read_config_from_db
        CONFIG = read_config_from_db(os.path.join(self.database_dir, 'AG_database.sqlite'))
        
        database_path = os.path.join(self.database_dir, 'AG_database.sqlite')
        gteu = GTEU(CONFIG, database_path, 'asdf')
        gteu.get_files_from_db()
        gteu.archive_files()
        gteu.encrypt_archive()
        
        tmpdir = os.path.join(self.database_dir, 'TMP')
        files = os.listdir(tmpdir)
        for f in files:
            f = os.path.join(tmpdir, f)
            print(f, os.stat(f).st_size)

        gteu.glacier_upload()
        #~ tests:
            #~ verify Jobs entry (before and after fina update)
            #~ verify tar file contents
            #~ verify decryption
            #~ verify backups list update
            
            #~ verify job id handling (w/ failed jobs)
