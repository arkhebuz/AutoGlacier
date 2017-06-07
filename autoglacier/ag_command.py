"""

"""
import argparse
import logging
import os

from autoglacier.ag_init import initialize_ag
from autoglacier.ag_jobs import do_backup_job
from autoglacier.ag_file_management import register_file_list


DEFAULT_DATABASE_PATH = os.path.join(os.path.expanduser('~'), '.autoglacier/AG_database.sqlite')
predefined_args = argparse.Namespace(database=DEFAULT_DATABASE_PATH)



def _construct_argparse_parser():
    parser = argparse.ArgumentParser(prog='AutoGlacier',
                       description="AG")
    subparsers = parser.add_subparsers()

    init = subparsers.add_parser('init', help="Initialize AutoGlacier configuration and database")
    init.set_defaults(func=initialize_ag)
    init.add_argument('config_file', help="Config file in JSON format")
    init.add_argument('--genkeys', help="Generate RSA key pair", action='store_true')

    backup = subparsers.add_parser('job', help="Do backup Job")
    backup.set_defaults(func=do_backup_job)
    
    register = subparsers.add_parser('register', help="register files in AutoGlacier database")
    register.set_defaults(func=register_file_list)
    register.add_argument('--database', help="path to AG database", default=DEFAULT_DATABASE_PATH)
    register.add_argument('--filelist', help="Read files from text file")
    
    return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    parser = _construct_argparse_parser()
    args = parser.parse_args(namespace=predefined_args)
    args.func(args)
