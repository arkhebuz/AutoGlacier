"""
Defines command line interface for AutoGlacier

"""
import argparse
import logging
import os

from autoglacier.ag_init import initialize_ag
from autoglacier.ag_jobs import do_backup_job
from autoglacier.ag_misc import manage_configs
from autoglacier.ag_file_management import register_file_list


DEFAULT_DATABASE_PATH = os.path.join(os.path.expanduser('~'), '.autoglacier/AG_database.sqlite')
DEFAULT_CONFIG_ID = 0
predefined_args = argparse.Namespace(database=DEFAULT_DATABASE_PATH)



def _construct_argparse_parser():
    """ This routine handles handles argument parser creation
    
    Returns:
        argparse.ArgumentParser instance
    """
    parser = argparse.ArgumentParser(prog='AutoGlacier', description="AG")
    subparsers = parser.add_subparsers()

    init = subparsers.add_parser('init', help="Initialize AutoGlacier configuration and database")
    init.set_defaults(func=initialize_ag)
    init.add_argument('config_file', help="Config file in JSON format")
    init.add_argument('--genkeys', help="Generate RSA key pair", action='store_true')

    backup = subparsers.add_parser('job', help="Do backup Job")
    backup.add_argument('--database', help="path to AG database", default=DEFAULT_DATABASE_PATH)
    backup.add_argument('--configid', help="configuration set ID", default=DEFAULT_CONFIG_ID)
    backup.set_defaults(func=do_backup_job)
    
    register = subparsers.add_parser('register', help="register files in AutoGlacier database")
    register.set_defaults(func=register_file_list)
    register.add_argument('--database', help="path to AG database", default=DEFAULT_DATABASE_PATH)
    register.add_argument('--configid', help="configuration set ID", default=DEFAULT_CONFIG_ID)
    register.add_argument('--filelist', help="read files from text file")
    
    config = subparsers.add_parser('config', help="Show/add/delete AutoGlacier configuration sets")
    config.set_defaults(func=manage_configs)
    config.add_argument('--show', help="show existing configs", action='store_true')
    
    return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    parser = _construct_argparse_parser()
    args = parser.parse_args(namespace=predefined_args)
    args.func(args)
