"""
Autoglacier Backup Jobs
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

from glacierbackup.database import GBDatabase



def do_backup_job(argparse_args):
    with GBDatabase(argparse_args.database) as DB:
        bj = BackupJob(DB, 'asdf', configuration_set_id=argparse_args.configid)
        bj.run()


class BackupJob(object):
    """ Checks which files should be backed up, then backs them up """
    # Formats supported by stdlib's tarfile:
    _compr = {'gzip': [':gz', '.tar.gz'],
              'lzma': [':xz', '.tar.xz'],
              'bzip2': [':bz2', '.tar.bz2'],
              'none': ['', '.tar'],
              '': ['', '.tar']}
    
    def __init__(self, gb_database, job_description, configuration_set_id=0):
        self.logger = logging.getLogger("JobLogger")
        self.DB = gb_database
        self.CONFIG = self.DB.read_config_from_db(set_id=configuration_set_id)
        self.description = job_description
        self.timestamp = time.time()
        self.tbd_file_backups = []
        self.backed_files_metadata = []
        
        max_id = self.DB.fetch_row('SELECT max(job_id) FROM BackupJobs')[0]
        if max_id == None:
            max_id = -1
        self.job_id = max_id+1
        self.logger.info("Running Backup Job on %s, job_id = %s, configuration set %s",
                         self.DB.database_path, self.job_id, self.CONFIG['set_id'])
        
        sql = ('INSERT INTO BackupJobs ('
              +'job_id, configuration_set_id, timestamp, description, archive_size, '
              +'archive_checksum, location, response, archive_id, success, '
              +'errors_message) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
        values = (self.job_id, self.CONFIG['set_id'], self.timestamp, self.description, -1, '', '', '', '', -1, '')
        self.DB.change(sql, values)
        
    def run(self):
        N = self.checkout_files()
        if N > 0:
            self.archive_files()
            self.encrypt_archive()
            self.upload_into_glacier()
            self.clean_tmp()
        else:
            self.logger.info("No files meeting backup criteria found, exiting")
    
    def _checkout_missing_files(self):
        ''' Check if any registered files are missing, and deregisters them'''
        sql = 'SELECT abs_path FROM Files WHERE registered=1'
        all_registered_files = self.DB.fetch_all(sql)
        for f in all_registered_files:
            f = f[0]
            if not os.path.isfile(f):
                self.logger.warning("Missing registered file: %s, deregistering", f)
                sql = 'UPDATE Files SET registered=0, file_exists=0 WHERE abs_path=?'
                self.DB.change(sql, (f,))

    def checkout_files(self):
        """ Checks which registered files should be backed up """
        self._checkout_missing_files()
        
        # Find registered files not backed up yet, ever
        sql = ('SELECT abs_path FROM Files WHERE abs_path NOT IN '
              +'( SELECT Files.abs_path FROM Files JOIN '
              +'Backups USING(abs_path) WHERE Files.registered=1 )')
        files_not_backed_up_ever = self.DB.fetch_all(sql)
        for path in files_not_backed_up_ever:
            self.tbd_file_backups.append(path[0])
        
        # Find registered and backed-up files and check if they were modified since last job
        previous_job_timestamp = self._get_last_successful_job_timestamp()
        sql = ('SELECT abs_path FROM Files WHERE abs_path IN '
              +'( SELECT Files.abs_path FROM Files JOIN '
              +'Backups USING(abs_path) WHERE Files.registered=1 )') 
        registered_files = self.DB.fetch_all(sql)
        for path in registered_files:
            if os.path.getmtime(path[0]) > previous_job_timestamp:
                self.tbd_file_backups.append(path[0]) 
        
        number_of_files = len(self.tbd_file_backups)
        self.logger.info("%s files found",  number_of_files)
        return number_of_files
        
    def _get_last_successful_job_timestamp(self):
        """ Returns previous successful job timestamp or -1 if there are none """
        if self.job_id == 0:
            previous_job_timestamp = -1
        else:
            sql = 'SELECT max(job_id) FROM BackupJobs WHERE job_id < ? AND success=1'
            last_succesfull_job = self.DB.fetch_row(sql, (self.job_id,))[0]
            if last_succesfull_job is None:
                self.logger.debug("All previous jobs failed")
                previous_job_timestamp = -1
            else:
                self.logger.debug("Previous succesfull job id = %s", last_succesfull_job)
                sql = 'SELECT timestamp FROM BackupJobs WHERE job_id=?'
                previous_job_timestamp = self.DB.fetch_row(sql, (last_succesfull_job,))[0]
        return previous_job_timestamp

    def archive_files(self):
        flag, extension = self._compr[self.CONFIG['compression_algorithm']]
        archive_name = 'AG_arch_jid'+str(self.job_id)+'_ts'+str(self.timestamp)+extension
        self.archive = os.path.join(self.CONFIG['temporary_dir'], archive_name)
        
        with tarfile.open(self.archive, "w"+flag) as tar:
            for path in self.tbd_file_backups:
                self.logger.debug("Packing file %s (%s bytes)", path, os.stat(path).st_size)
                self._collect_metadata(path)
                tar.add(path)
        
        archive_size = os.stat(self.archive).st_size
        self.logger.info("Created archive %s (%s bytes)", self.archive, archive_size)
        if archive_size > 100 * 1024*1024:
            self.logger.warning("Archive is bigger than 100 MB")
        
    def _collect_metadata(self, file_path):
        with open(file_path, 'rb') as f:
            filehash = hashlib.sha256(f.read()).hexdigest()
        modtime = os.path.getmtime(file_path)
        metadata = (file_path, modtime, filehash, self.job_id)
        self.backed_files_metadata.append(metadata)
    
    def encrypt_archive(self):
        ''' Encrypts archive with AES'''
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
        
    def _generate_description(self):
        """ description should fit within 1024 ascii chars """
        self.description = self.description[:1024]
    
    # This method could really be something external, invoked by BackupJob
    # It may require DB reorganization (i.e. new table: uploaders), however
    def upload_into_glacier(self):
        ''' Uploads archive '''
        region_name = self.CONFIG['region_name']
        vault_name = self.CONFIG['vault_name']
        self._generate_description()
        self.logger.info("Uploading into Glacier, region %s, vault %s", region_name, vault_name)
        
        try:
            glacier = boto3.client('glacier',
                                   region_name = region_name,
                                   aws_access_key_id = self.CONFIG['aws_access_key_id'],
                                   aws_secret_access_key = self.CONFIG['aws_secret_access_key'])
            response = glacier.upload_archive(vaultName = vault_name,
                                              archiveDescription = self.description,
                                              body = open(self.encrypted_archive, 'rb'))
        except:
            self.logger.exception("Unknown exception raised during upload")
            raise
        self.logger.debug("Amazon response: %s", repr(response))
        
        if response["ResponseMetadata"]['HTTPStatusCode'] == 201:
            upload_succeed = 1
        else:
            upload_succeed = 0
            self.logger.error("Upload has failed")
        
        location = response['location']
        checksum = response['checksum']
        archiveId = response['archiveId']
        archsize = os.stat(self.encrypted_archive).st_size

        sql = ('UPDATE BackupJobs SET location=?, archive_size=?, archive_checksum=?, '
              +'archive_id=?, response=?, success=? WHERE job_id=?')
        values = (location, archsize, checksum, archiveId, repr(response), upload_succeed, self.job_id)
        self.DB.change(sql, values)
        if upload_succeed == 1:
            sql = 'INSERT INTO Backups (abs_path, mod_date, sha256, job_id) VALUES (?, ?, ?, ?)'
            self.DB.change_many(sql, self.backed_files_metadata)

    def clean_tmp(self):
        if os.path.isfile(self.archive):
            os.remove(self.archive)
        if os.path.isfile(self.encrypted_archive):
            os.remove(self.encrypted_archive)

