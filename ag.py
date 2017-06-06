""" AG - AutoGlacier"""
import argparse
import logging
import sqlite3
import json
import os
#~ import datetime
import tarfile
import hashlib
import glob
import time
# Beyond stdlib
import boto3
# pycryptodome package
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP



def initialize_ag(argparse_args):
    # TODO: check if already not initialized
    config_path = argparse_args.config_file
    with open(config_path, 'r') as f:
        CONFIG = json.load(f)
    CONFIG['SET_ID'] = 0
    database_dir = CONFIG['AG_DATABASE_DIR']
    try: 
        os.mkdir(database_dir)
    except FileExistsError:
        pass
    else:
        os.mkdir(os.path.join(database_dir, 'logs'))
    
    initiate_databse(CONFIG)
    
    # Just a handy copy of original config file
    new_config_json = os.path.join(database_dir, 'CONFIG.json')
    if not os.path.isfile(new_config_json):
        with open(new_config_json, 'w') as f:
            json.dump(CONFIG, f, indent=2)
    
    if argparse_args.gen_keys:
        public = os.path.join(database_dir, 'AG_RSA_public.pem')
        private = os.path.join(database_dir, 'AG_RSA_private.pem')
        gen_RSA_keys(public, private)
    
    # TODO: GTEU verification on an empty database


def insert_configuration_set(CONFIG, db_cursor):
    ''' 
    CONFIG - configuration set in JSON representation
    db_cursor - open AC database cursor'''
    try:
        values = (0, 
                  CONFIG['REGION_NAME'], 
                  CONFIG['VAULT_NAME'], 
                  CONFIG['PUBL_RSA_KEY_PATH'], 
                  CONFIG['COMPRESSION_ALGORITHM'], 
                  CONFIG['TEMPORARY_DIR'], 
                  CONFIG['AG_DATABASE_DIR'], 
                  CONFIG['AWS_ACCESS_KEY_ID'], 
                  CONFIG['AWS_SECRET_ACCESS_KEY'])
    except KeyError:
        print('pls fix conf')
        raise
        
    db_cursor.execute( ('INSERT INTO ConfigurationSets ('
                       +'set_id, region_name, vault_name, public_key, compression_algorithm, '
                       +'temporary_dir, ag_database_dir, aws_access_key_id, aws_secret_access_key'
                       +') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'), values)


def initiate_databse(CONFIG):
    """ Initiates Database with CONFIG in config table """
    ag_database = os.path.join(CONFIG['AG_DATABASE_DIR'], 'AG_database.sqlite')
    if not os.path.isfile(ag_database):
        conn = sqlite3.connect(ag_database)
        c = conn.cursor()
        
        c.execute( ('CREATE TABLE Files ('
                   +'file_id            INTEGER PRIMARY KEY NOT NULL, '
                   +'abs_path           TEXT NOT NULL, '
                   +'registration_date  INT NOT NULL, '
                   +'last_backed        INT, '
                   +'registered         INT)') )
        
        c.execute( ('CREATE TABLE Backups ('
                   +'file_id        INTEGER NOT NULL, '
                   +'mod_date       INT NOT NULL, '
                   +'sha512         TEXT NOT NULL, '
                   +'job_id         INT NOT NULL)') )
        
        c.execute( ('CREATE TABLE Jobs ('
                   +'job_id                 INT NOT NULL, '
                   +'arch_size              INT NOT NULL, '
                   +'response               TEXT, '
                   +'location               TEXT NOT NULL, '
                   +'sha512_checksum        TEXT NOT NULL, '
                   +'archive_id             TEXT NOT NULL, '
                   +'description            TEXT NOT NULL, '
                   +'configuration_set_id   INT NOT NULL, '
                   +'timestamp              INT NOT NULL, '
                   +'success                INT NOT NULL, '
                   +'errors_message         TEXT)') )
        
        c.execute( ('CREATE TABLE ConfigurationSets ('
                   +'set_id                 INT NOT NULL, '
                   +'region_name            TEXT NOT NULL, '
                   +'vault_name             TEXT NOT NULL, '
                   +'public_key             TEXT NOT NULL, '
                   +'compression_algorithm  TEXT NOT NULL, '
                   +'temporary_dir          TEXT NOT NULL, '
                   +'ag_database_dir        TEXT NOT NULL, '
                   +'aws_access_key_id      TEXT, '
                   +'aws_secret_access_key  TEXT, '
                   +'regular_runtime_params TEXT )') )
        
        insert_configuration_set(CONFIG, c)
        conn.commit()
    else:
        raise RuntimeError
        # TODO: rethink this



def gen_RSA_keys(PRIV_RSA_KEY_PATH, PUBL_RSA_KEY_PATH, RSA_PASSPHRASE=None):
    ''' Helper function - RSA keys generation '''
    key = RSA.generate(2048)
    encrypted_key = key.exportKey(passphrase=RSA_PASSPHRASE, pkcs=8, protection="scryptAndAES128-CBC")
    with open(PRIV_RSA_KEY_PATH, 'wb') as f:
        f.write(encrypted_key)
    with open(PUBL_RSA_KEY_PATH, 'wb') as f:
        f.write(key.publickey().exportKey())

def decrypt_archive(encrypted_file, PRIV_RSA_KEY_PATH, output_file='decrypted.tar.xz', RSA_PASSPHRASE=None):
    ''' Helper function - file decryption '''
    with open(encrypted_file, 'rb') as fobj:
        private_key = RSA.import_key(open(PRIV_RSA_KEY_PATH).read(), passphrase=RSA_PASSPHRASE)
     
        enc_session_key, nonce, tag, ciphertext = [ fobj.read(x) 
                                                    for x in (private_key.size_in_bytes(), 
                                                    16, 16, -1) ]
        cipher_rsa = PKCS1_OAEP.new(private_key)
        session_key = cipher_rsa.decrypt(enc_session_key)
     
        cipher_aes = AES.new(session_key, AES.MODE_EAX, nonce)
        data = cipher_aes.decrypt_and_verify(ciphertext, tag)
     
    with open(output_file, 'wb') as f:
        f.write(data)

def download_archive():
    # TODO
    pass

def do_backup_job():
    # TODO
    gteu = GTEU()
    gteu.get_files_from_db()
    gteu.archive_files()
    gteu.encrypt_files()
    gteu.glacier_upload()
    gteu.clean_tmp()
    pass


class GTEU(object):
    # Formats supported by stdlib's tarfile:
    _comp = {'gzip': [':gz', '.tar.gz'],
             'lzma': [':xz', '.tar.xz'],
             'bzip2': [':bz2', '.tar.bz2'],
             'none': ['', '.tar'],
             '': ['', '.tar']}
    
    def __init__(self):
        pass
    
    def get_files_from_db(self):
        pass
    
    def archive_files(self):
        pass
    
    def encrypt_archive(self):
        pass
    
    def _generate_description(sef):
        pass
    
    def glacier_upload(self):
        pass
    
    def clean_tmp(self):
        pass


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
