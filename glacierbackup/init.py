""" 
GlacierBackup database/directories/RSA keys initialization
"""
import logging
import json
import os
# Beyond stdlib
# pycryptodome package
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP

from glacierbackup.database import GBDatabase



def initialize_ag(argparse_args):
    # TODO: check if already not initialized
    config_path = argparse_args.config_file
    with open(config_path, 'r') as f:
        CONFIG = json.load(f)
    CONFIG['set_id'] = 0
    database_dir = CONFIG['database_dir']
    try: 
        os.mkdir(database_dir)
    except FileExistsError:
        pass
    try:
        os.mkdir(os.path.join(database_dir, 'logs'))
    except FileExistsError:
        pass
    
    tmp_dir = CONFIG['temporary_dir']
    try: 
        os.mkdir(tmp_dir)
    except FileExistsError:
        pass

    if argparse_args.genkeys:
        public = os.path.join(database_dir, 'GB_RSA_public.pem')
        private = os.path.join(database_dir, 'GB_RSA_private.pem')
        public_key = gen_RSA_keys(private, public)
        CONFIG['public_key'] = public_key.decode('utf8')

    database_path = os.path.join(database_dir, 'GB_database.sqlite')
    DB = GBDatabase(database_path)
    DB.initialize(CONFIG)



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

