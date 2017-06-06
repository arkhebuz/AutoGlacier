import argparse
import logging

from ag import initialize_ag, do_backup_job



if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(prog='AutoGlacier',
                       description="AG")
    subparsers = parser.add_subparsers()

    init = subparsers.add_parser('init', help="Initialize AutoGlacier configuration and database")
    init.set_defaults(func=initialize_ag)
    init.add_argument('config_file', help="Config file in JSON format")
    init.add_argument('--gen-keys', help="Generate RSA key pair", action='store_true')

    backup = subparsers.add_parser('backup', help="Do backup Job")
    backup.set_defaults(func=do_backup_job)

    args = parser.parse_args()
    args.func(args)
