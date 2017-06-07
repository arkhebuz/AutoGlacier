""" AG - AutoGlacier

# program installation initialization
`autoglacier init /path/to/cfg.file --gen-keys [--autotest]`

"""
import argparse
import logging
import sqlite3
import tarfile
import hashlib
import json
import glob
import time
import os
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
    CONFIG['set_id'] = 0
    database_dir = CONFIG['ag_database_dir']
    try: 
        os.mkdir(database_dir)
    except FileExistsError:
        pass
    try:
        os.mkdir(os.path.join(database_dir, 'logs'))
    except FileExistsError:
        pass
    
    if argparse_args.gen_keys:
        public = os.path.join(database_dir, 'AG_RSA_public.pem')
        private = os.path.join(database_dir, 'AG_RSA_private.pem')
        public_key = gen_RSA_keys(public, private)
        CONFIG['public_key'] = str(public_key)

    initiate_databse(CONFIG)
    
    # Just a handy copy of original config file
    new_config_json = os.path.join(database_dir, 'CONFIG.json')
    if not os.path.isfile(new_config_json):
        with open(new_config_json, 'w') as f:
            json.dump(CONFIG, f, indent=2)
    
    # TODO: GTEU verification on an empty database

def insert_configuration_set(CONFIG, db_cursor):
    ''' 
    CONFIG - configuration set in JSON representation
    db_cursor - open AC database cursor'''
    try:
        values = (0, 
                  CONFIG['region_name'], 
                  CONFIG['vault_name'], 
                  CONFIG['public_key'], 
                  CONFIG['compression_algorithm'], 
                  CONFIG['temporary_dir'], 
                  CONFIG['ag_database_dir'], 
                  CONFIG['aws_access_key_id'], 
                  CONFIG['aws_secret_access_key'])
    except KeyError:
        print('pls fix conf')
        raise
        
    db_cursor.execute( ('INSERT INTO ConfigurationSets ('
                       +'set_id, region_name, vault_name, public_key, compression_algorithm, '
                       +'temporary_dir, ag_database_dir, aws_access_key_id, aws_secret_access_key'
                       +') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'), values)

def initiate_databse(CONFIG):
    """ Initiates Database with CONFIG in config table """
    ag_database = os.path.join(CONFIG['ag_database_dir'], 'AG_database.sqlite')
    if not os.path.isfile(ag_database):
        conn = sqlite3.connect(ag_database)
        c = conn.cursor()
        
        c.execute( ('CREATE TABLE Files ('
                   +'abs_path           TEXT PRIMARY KEY NOT NULL, '
                   +'registration_date  INT NOT NULL, '
                   +'file_exists        INT NOT NULL, '
                   +'registered         INT)') )
        #~ c.execute( 'CREATE INDEX abs_path_index ON Files (abs_path)' )
        
        c.execute( ('CREATE TABLE Backups ('
                   +'abs_path       TEXT NOT NULL, '
                   +'mod_date       INT NOT NULL, '
                   +'sha512         TEXT NOT NULL, '
                   +'job_id         INT NOT NULL)') )
        
        c.execute( ('CREATE TABLE Jobs ('
                   +'job_id                 INT PRIMARY KEY NOT NULL, '
                   +'configuration_set_id   INT NOT NULL, '
                   +'timestamp              INT NOT NULL, '
                   +'description            TEXT NOT NULL, '
                   +'arch_size              INT NOT NULL, '
                   +'sha512_checksum        TEXT NOT NULL, '
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
                   +'ag_database_dir        TEXT NOT NULL, '
                   +'aws_access_key_id      TEXT, '
                   +'aws_secret_access_key  TEXT, '
                   +'regular_runtime_params TEXT )') )
        
        insert_configuration_set(CONFIG, c)
        conn.commit()
        conn.close()
    else:
        raise RuntimeError
        # TODO: rethink this

def gen_RSA_keys(PRIV_RSA_KEY_PATH, PUBL_RSA_KEY_PATH, RSA_PASSPHRASE=None):
    ''' Helper function - RSA keys generation '''
    key = RSA.generate(2048)
    encrypted_key = key.exportKey(passphrase=RSA_PASSPHRASE, pkcs=8, protection="scryptAndAES128-CBC")
    with open(PRIV_RSA_KEY_PATH, 'wb') as f:
        f.write(encrypted_key)
    public_key_str = key.publickey().exportKey()
    with open(PUBL_RSA_KEY_PATH, 'wb') as f:
        f.write(public_key_str)
    return public_key_str


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

