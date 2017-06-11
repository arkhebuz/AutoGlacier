"""
Defines command line interface for AutoGlacier

"""
import argparse
import logging
import os

from autoglacier.init import initialize_ag
from autoglacier.jobs import do_backup_job
from autoglacier.misc import manage_configs
from autoglacier.file_management import register_file_list


DEFAULT_DATABASE_PATH = os.path.join(os.path.expanduser('~'), '.autoglacier/AG_database.sqlite')
DEFAULT_CONFIG_ID = 0
predefined_args = argparse.Namespace(database=DEFAULT_DATABASE_PATH, 
                                     configid=DEFAULT_CONFIG_ID)



def _construct_argparse_parser(return_all_parsers=0):
    """ This routine handles handles creation of argument parser, defining the CLI
    
    Returns:
        argparse.ArgumentParser instance
    """
    
    autoglacier_epoligdesc = """
This Amazon Glacier backup script is aimed at the case when one needs to 
back-up a considerable number of small files into cold-storage, i.e. to 
prevent data loss caused by ransomware attack. AutoGlacier keeps track 
of files: checks if their contents changed, backs them up if so, and notes 
which version of which file was backed up into which archive and when.
This information comes very handy as every uploaded backup is 
AES-encrypted LZMA-compressed tar archive

The script is aimed at simplicity, portability and extendability, featuring
file tracking, local metadata logging, data compression, encryption and 
(some) file-picking functionality. Alpha at the moment (although it works!).
"""
    parser = argparse.ArgumentParser(prog='AutoGlacier', 
                                     description="AutoGlacier tracks and backs-up small files into Amazon Glacier",
                                     epilog=autoglacier_epoligdesc,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers()

    init_epidesc = """
The init command creates database directory, set-ups the required local
SQLite database and saves initial config into it. The initial config 
will be always written to the database with id=0. If --genkeys flag 
is activated an RSA key pair will be generated (no passphrase) and 
saved as plain files in the database directory, the public key will
be also saved in the configuration set ID=0.

The config_file should be a proper JSON file storing 
the following parameters:
    {
      "set_id" : 0,
      "ag_database_dir": database_directory,
      "compression_algorithm" : "lzma",
      "temporary_dir": tmp_dir,
      "public_key": "key",
      "region_name": "eu-west-1",
      "vault_name": "MyVault",
      "aws_access_key_id": "key",
      "aws_secret_access_key": "key"
    }"""
    init = subparsers.add_parser('init', help="Initialize AutoGlacier configuration and database",
                                 epilog=init_epidesc,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    init.set_defaults(func=initialize_ag)
    init.add_argument('config_file', help="Config file in JSON format")
    init.add_argument('--genkeys', help="generate RSA key pair", action='store_true')
    #~ init.add_argument('--autotest', help="", action='store_true')    # This should fire up some tests from the suite

    job_epidesc = """
AutoGlacier backup job is launched against a database and proceeds in an
automated fashion. AutoGlacier checks if any new files were registered 
and if any old registered files were changed, then gathers them, packs,
encrypts and uploads into Glacier using credentials from a given 
configuration set (default 0).
"""
    backup = subparsers.add_parser('job', help="Do backup Job - gathers and uploads files into Glacier",
                                   epilog=job_epidesc,
                                   formatter_class=argparse.RawDescriptionHelpFormatter)
    backup.add_argument('--database', help="path to AG database", default=DEFAULT_DATABASE_PATH)
    backup.add_argument('--configid', help="configuration set ID", default=DEFAULT_CONFIG_ID)
    #~ backup.add_argument('--description', help="", default=)
    backup.set_defaults(func=do_backup_job)
    
    register = subparsers.add_parser('register', help="Register files in AutoGlacier database")
    register.set_defaults(func=register_file_list)
    register.add_argument('--database', help="path to AG database", default=DEFAULT_DATABASE_PATH)
    register.add_argument('--configid', help="configuration set ID", default=DEFAULT_CONFIG_ID)
    register.add_argument('--filelist', help="read files from text file, one absolute path per line")
    
    config = subparsers.add_parser('config', help="Show/add/delete AutoGlacier configuration sets")
    config.set_defaults(func=manage_configs)
    config.add_argument('--show', help="show existing configs", action='store_true')

    #~ download = subparsers.add_parser('download', help="Download archived files")
    #~ download.set_defaults(func=)
    #~ download.add_argument('job_id', help="ID of a job which made the archive to be downloaded")
    #~ download.add_argument('--privkey', help="private key (for decryption)")

    if return_all_parsers:
        return parser, init, backup, register, config
    else:
        return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    parser = _construct_argparse_parser()
    args = parser.parse_args(namespace=predefined_args)
    args.func(args)
