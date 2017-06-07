"""
# running a job
`autoglacier job --database=/path/to/datgabase.sqlite --config_id=0`

database location is the only information really required.
default config ID is 0

!deleted files would be detected HERE!
"""
import logging
import sqlite3
import tarfile
import hashlib
import time
import os

import boto3
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP

from autoglacier.ag_misc import read_config_from_db



def do_backup_job(argparse_args):
    CONFIG = read_config_from_db(argparse_args.database)
    
    # TODO: error handling (make GTEU a context manager?)
    gteu = GTEU(CONFIG, argparse_args.database, 'asdf')
    gteu.get_files_from_db()
    gteu.archive_files()
    #~ gteu.encrypt_files()
    #~ gteu.glacier_upload()
    #~ gteu.clean_tmp()



class GTEU(object):
    # Formats supported by stdlib's tarfile:
    _comp = {'gzip': [':gz', '.tar.gz'],
             'lzma': [':xz', '.tar.xz'],
             'bzip2': [':bz2', '.tar.bz2'],
             'none': ['', '.tar'],
             '': ['', '.tar']}
    
    def __init__(self, CONFIG, database_path, description):
        self.logger = logging.getLogger("JobLogger")
        self.CONFIG = CONFIG
        self.timestamp = time.time()
        self.database_path = database_path
        seld.description = description
        self.logging.info("Running Job on %s database, configuration set %s",
                          self.database_path, CONFIG['set_id'])
        
        conn = sqlite3.connect(database_path)
        c = conn.cursor()
        c.execute('SELECT max(job_id) FROM Jobs')
        max_id = c.fetchone()[0]
        if max_id == None:
            self.logger.info('First job (job_id=0)')
            max_id = -1
        self.job_id = max_id+1
        self.logger.info('job_id = %s', self.job_id)
        
        values = (self.job_id, CONFIG['set_id'], self.timestamp, description, -1,
                  "", "", "", "", -1, "")
        c.execute( ('INSERT INTO Jobs ('
                   +'job_id, configuration_set_id, timestamp, description, arch_size, '
                   +'sha512_checksum, location, response, archive_id, success, '
                   +'errors_message) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'), values)
        
        conn.commit()
        conn.close()
        self.tbd_file_backups = []
        self.new_backups = []

    def get_files_from_db(self):
        """ Checks which registered files should be backed up """
        conn = sqlite3.connect(self.database_path)
        c = conn.cursor()
        
        if self.job_id > 0:
            c.execute('SELECT timestamp FROM Jobs WHERE job_id={} AND success=1'.format(self.job_id-1))
            previous_job_timestamp = c.fetchone()[0]
        else:
            previous_job_timestamp = -1
        
        # Find registered files modified since last job
        c.execute('SELECT abs_path FROM Files WHERE registered=1')
        paths = c.fetchall()
        for p in paths:
            p = p[0]
            if os.path.isfile(p):
                if os.path.getmtime(p) > previous_job_timestamp:
                    self.tbd_file_backups.append(p) 
            else:
                self.logger.warning("Missing file %s", p)
        
        # Find files not backed up yet, ever
        c.execute( ('SELECT * FROM Files WHERE abs_path NOT IN '
                   +'(SELECT Files.abs_path FROM Files JOIN '
                   +'Backups USING(abs_path) WHERE Files.registered=1)') )
        not_backed_up_yet = c.fetchall()
        for nb in not_backed_up_yet:
            path = nb[0]
            if os.path.isfile(path):
                self.tbd_file_backups.append(path)
            else:
                self.logger.warning("Missing file %s", path)
        
        conn.commit()
        conn.close()
    
    def archive_files(self):
        print('Tar...')
        flag, extension = self._comp[self.CONFIG['compression']]
        archive_name = 'arch_jid'+str(self.job_id)+'_'+str(self.timestamp)+extension
        self.archive = os.path.join(self.CONFIG['temporary_dir'], archive_name)
        
        with tarfile.open(self.archive, "w"+flag) as tar:
            for path in self.tbd_file_backups:
                self.logging.debug('Pasking file %s', path)
                modtime = os.path.getmtime(path)
                with open(path, 'rb') as f:
                    filehash = hashlib.sha512(f.read()).hexdigest()
                self.new_backups.append((path, modtime, filehash, self.job_id)) 
                tar.add(path)#, arcname=os.path.basename(source_dir))
        
    def encrypt_archive(self):
        ''' Encrypts archive with AES'''
        print('Encrypt...')
        key = self.CONFIG['public_key']
        self.encrypted_archive = self.archive+'.bin'
        
        with open(self.encrypted_archive, 'wb') as out_file:
            recipient_key = RSA.import_key(key)
            session_key = get_random_bytes(16)
         
            cipher_rsa = PKCS1_OAEP.new(recipient_key)
            out_file.write(cipher_rsa.encrypt(session_key))
         
            cipher_aes = AES.new(session_key, AES.MODE_EAX)
            with open(self.archive, 'rb') as in_file:
                data = in_file.read()
                ciphertext, tag = cipher_aes.encrypt_and_digest(data)
         
            out_file.write(cipher_aes.nonce)
            out_file.write(tag)
            out_file.write(ciphertext)
        
    def _generate_description(sef):
        pass
    
    def glacier_upload(self):
        ''' Uploads archive '''
        print('Upload...')
        
        glacier = boto3.client('glacier',
                               region_name = self.CONFIG['region_name'],
                               aws_access_key_id = self.CONFIG['aws_access_key_id'],
                               aws_secret_access_key = self.CONFIG['aws_secret_access_key'])
        # TODO: error logging
        response = glacier.upload_archive(vaultName = self.CONFIG['vault_name'],
                                          archiveDescription = self.description,
                                          body = open(self.encrypted_archive, 'rb'))
        print(str(response))
    
        # Jobs table is updated
        # self.new_backups is written to Backups table if backup job succeds
        #~ c.executemany( ('INSERT INTO Backups ('
                       #~ +'abs_path, mod_date, sha512, job_id'
                       #~ +') VALUES (?, ?, ?, ?)'), self.new_backups)
    
    def clean_tmp(self):
        pass
