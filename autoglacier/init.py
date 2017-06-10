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

from autoglacier.database import AGDatabase



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
    
    if argparse_args.genkeys:
        public = os.path.join(database_dir, 'AG_RSA_public.pem')
        private = os.path.join(database_dir, 'AG_RSA_private.pem')
        public_key = gen_RSA_keys(private, public)
        CONFIG['public_key'] = public_key.decode('utf8')

    database_path = os.path.join(CONFIG['ag_database_dir'], 'AG_database.sqlite')
    DB = AGDatabase(database_path)
    DB.initialize(CONFIG)
    
    # Just a handy copy of original config file
    new_config_json = os.path.join(database_dir, 'CONFIG.json')
    if not os.path.isfile(new_config_json):
        with open(new_config_json, 'w') as f:
            json.dump(CONFIG, f, indent=2)


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


