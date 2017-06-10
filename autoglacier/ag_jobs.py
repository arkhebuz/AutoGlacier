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
    CONFIG = read_config_from_db(argparse_args.database, set_id=argparse_args.configid)
    
    # TODO: error handling (make GTEU a context manager?)
    bj = BackupJob(CONFIG, argparse_args.database, 'asdf')
    bj.get_files_from_db()
    bj.archive_files()
    bj.encrypt_files()
    #~ bj.glacier_upload()
    #~ bj.clean_tmp()


class BackupJob(object):
    """ Checks which files should be backed up, then backs them up """
    # Formats supported by stdlib's tarfile:
    _comp = {'gzip': [':gz', '.tar.gz'],
             'lzma': [':xz', '.tar.xz'],
             'bzip2': [':bz2', '.tar.bz2'],
             'none': ['', '.tar'],
             '': ['', '.tar']}
    
    def __init__(self, CONFIG, database_path, job_description):
        self.logger = logging.getLogger("JobLogger")
        self.CONFIG = CONFIG
        self.database_path = database_path
        self.description = job_description
        self.timestamp = time.time()
        self.tbd_file_backups = []
        self.backed_files_metadata = []
        
        try:
            db_conn = sqlite3.connect(self.database_path)
            db = db_conn.cursor()
            db.execute('SELECT max(job_id) FROM BackupJobs')
        except sqlite3.OperationalError:
            self.logger.exception( ("Wrong path to database or database structure "
                                   +"was corrupted (path: %s)"), self.database_path)
            raise
        max_id = db.fetchone()[0]
        if max_id == None:
            max_id = -1
        self.job_id = max_id+1
        self.logger.info("Running Backup Job on %s, job_id = %s, configuration set %s",
                         self.database_path, self.job_id, CONFIG['set_id'])
        
        values = (self.job_id, CONFIG['set_id'], self.timestamp, self.description, -1,
                  "", "", "", "", -1, "")
        db.execute( ('INSERT INTO BackupJobs ('
                    +'job_id, configuration_set_id, timestamp, description, archive_size, '
                    +'archive_checksum, location, response, archive_id, success, '
                    +'errors_message) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'), values)
        db_conn.commit()
        db_conn.close()

    def get_files_from_db(self):
        """ Checks which registered files should be backed up """
        previous_job_timestamp = self._get_last_successful_job_timestamp()
        db_conn = sqlite3.connect(self.database_path)
        db = db_conn.cursor()
        
        # Find registered and backed-up files and check if they were modified since last job
        db.execute( ('SELECT abs_path FROM Files WHERE abs_path IN '
                    +'( SELECT Files.abs_path FROM Files JOIN '
                    +'Backups USING(abs_path) WHERE Files.registered=1 )') )
        registered_files = [f[0] for f in db.fetchall()]
        for path in registered_files:
            if os.path.isfile(path):
                if os.path.getmtime(path) > previous_job_timestamp:
                    self.tbd_file_backups.append(path) 
            else:
                self.logger.warning("Missing registered file: %s", path)
        
        # Find registered files not backed up yet, ever
        db.execute( ('SELECT abs_path FROM Files WHERE abs_path NOT IN '
                    +'( SELECT Files.abs_path FROM Files JOIN '
                    +'Backups USING(abs_path) WHERE Files.registered=1 )') )
        files_not_backed_up_ever = [f[0] for f in db.fetchall()]
        for path in files_not_backed_up_ever:
            if os.path.isfile(path):
                self.tbd_file_backups.append(path)
            else:
                self.logger.warning("Missing registered file: %s", path)
        
        db_conn.commit()
        db_conn.close()
        self.logger.info("%s files found", len(self.tbd_file_backups) )
        
    def _get_last_successful_job_timestamp(self):
        """ Returns previous successful job timestamp or -1 if there are none """
        db_conn = sqlite3.connect(self.database_path)
        db = db_conn.cursor()
        if self.job_id == 0:
            previous_job_timestamp = -1
        else:
            db.execute('SELECT max(job_id) FROM BackupJobs WHERE job_id < ? AND success=1', (self.job_id,))
            last_succesfull_job = db.fetchone()[0]
            if last_succesfull_job is None:
                self.logger.debug("All previous jobs failed")
                previous_job_timestamp = -1
            else:
                self.logger.debug("Previous succesfull job id = %s", last_succesfull_job)
                db.execute('SELECT timestamp FROM BackupJobs WHERE job_id=?', (last_succesfull_job,))
                previous_job_timestamp = db.fetchone()[0]
        db_conn.close()
        return previous_job_timestamp

    def archive_files(self):
        flag, extension = self._comp[self.CONFIG['compression_algorithm']]
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
        
    def _generate_description(sef):
        """ description should fit within 1024 ascii chars """
        pass
    
    # This method could really be something external, invoked by GTEU
    # It may require DB reorganization (i.e. new table: uploaders), however
    def glacier_upload(self):
        ''' Uploads archive '''
        region_name = self.CONFIG['region_name']
        vault_name = self.CONFIG['vault_name']
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

        db_conn = sqlite3.connect(self.database_path)
        db = db_conn.cursor()
        db.execute( ('UPDATE BackupJobs SET location=?, archive_size=?, archive_checksum=?, '
                    +'archive_id=?, response=?, success=? WHERE job_id=?'),
                   (location, archsize, checksum, archiveId, repr(response), upload_succeed, self.job_id) )
        if upload_succeed == 1:
            db.executemany( ('INSERT INTO Backups '
                            +'(abs_path, mod_date, sha256, job_id) '
                            +'VALUES (?, ?, ?, ?) '), self.backed_files_metadata)
        db_conn.commit()
        db_conn.close()

    def clean_tmp(self):
        pass
