''' Amazon Glacier backup script aimed at simplicity, portability and extendability, 
featuring (some) file-picking functionality, data encryption and local metadata logging.
'''
import datetime
import tarfile
import hashlib
import json
import glob
import time
import os
# Beyond stdlib
import boto3
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP



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


class _jsondb(object):
    ''' Manages json log file writing
    
    Helper class for GTEU.run(). It's not thread safe!
    '''
    def __init__(self, CONFIG):
        self.database = CONFIG['JSON_DATABASE']
        with open(self.database, 'r') as f:
            self.DB = json.load(f)
            # TODO: bug-out on corrupted JSON
            # TODO: JSON file creation if none
            
    def add_ts(self, ts, data):
        self.DB[ts] = data
        with open(self.database, 'w') as f:
            json.dump(self.DB, f, indent=2)
            
    def update_ts(self, ts, data):
        self.DB[ts].update(data)
        with open(self.database, 'w') as f:
            json.dump(self.DB, f, indent=2)


class GTEU(object):
    ''' [G]athers files, [T]ars them up, [E]ncrypts and [U]ploads them into Glacier 
    
    Use case: 1 AWS user uploads 1 encrypted single-part archive to a single Glacier vault.
    GTEU class employs a simple 1-directional internal data/execution flow to do just that: 
      GTEU.gather() -> GTEU.tar() -> GTEU.encrypt() -> GTEU.upload()
    
    Backup job can be defined by inheriting from this class and overwriting 
    configuration variables, including lists of files to be backed up or
    directories to be backed-up non-recursively (Python glob module syntax).
    More advanced file-picking code can be added by re-implementing gather hook 
    method (GTEU.gather_hook). Job can be started by invoking run() classmethod
    on a newly defined class (see example).
    
    Backup is uploaded as an LZMA-compressed tar archive encrypted with AES using
    RSA keys (only the public key is required). In addition, process metadata 
    (including backed-up files locations and their SHA512 hashes) is saved into 
    a flat-file JSON database indexed by unix timestamp at script launch.
    
    Currently this class is ill-siuted for large files (single-part upload only,
    in-memory file hashing) or huge numbers of small files (separate hashing and
    taring steps causes files to be read into memory twice). Also the code isn't
    fully thread-safe (data log writing, race condition with timestamps)
    '''
    # Formats supported by stdlib's tarfile:
    _comp = {'gzip': [':gz', '.tar.gz'],
             'lzma': [':xz', '.tar.xz'],
             'bzip2': [':bz2', '.tar.bz2'],
             'none': ['', '.tar'],
             '': ['', '.tar']}
    
    # A JSON configuration dictionary
    CONFIG = {
      # Default compression algorithm
      'COMPRESSION' = "lzma",
      # Temporary dir location
      'TMP_DIR': "C:\\TMP",
      # JSON metadata log file location
      'JSON_DATABASE': 'C:\\logs\log.json',
      # Public RSA key for data encryption
      'PUBL_RSA_KEY_PATH': ".\my_rsa_public.pem",
      # Glacier account (IAM user) settings - single user, region and vault
      'REGION_NAME': 'eu-west-1',
      'VAULT_NAME': 'TestVault1',
      'AWS_ACCESS_KEY_ID': "",
      'AWS_SECRET_ACCESS_KEY': "",
    }
    # Explicit list of files to be backed up (full paths)
    files = []
    # List of glob patterns to be matched, result is added to `files` list
    list_of_globs = []
    # Archive description for Glacier upload
    description = "default description"
    
    def __init__(self, TIMESTAMP, jsondb):
        self.TIMESTAMP = TIMESTAMP
        self.jsondb = jsondb

    def gather_hook(self):
        ''' Overwrite this function to fiddle with GTEU.files list directly
        
        This placeholder function is always called after automated file list 
        formulation and before metadata collection. File list can be accessed
        under self.files.
        '''
        pass
        
    def _glob_dirs(self):
        # TODO: nested dirs? - cannot hash folder
        for adir in self.list_of_globs:
            self.files = self.files + list(glob.iglob(adir))
        
    @staticmethod
    def _file_metadata(afile):
        ''' finds absolute file path, file SHA512 hash, file modification timestep '''
        # read modification time
        modtime = os.path.getmtime(afile)
        modtimestr = datetime.datetime.fromtimestamp(modtime).strftime('%Y-%m-%d %H:%M:%S')

        # calculate hash - memory inefficient method
        with open(afile, 'rb') as f:
            filehash = hashlib.sha512(f.read()).hexdigest()

        return {'SHA512':filehash, 'mod_time':modtimestr, 'abs_path':os.path.abspath(afile)}

    def gather(self):
        ''' Gathers files (with metadata) for a single archive
        
        files come from: 
        1. self.files list
        2. globs written in self.list_of_globs 
        3. GTEU.gather_hook (if implemented)
        '''
        print('Gather...')
        self._glob_dirs()
        self.gather_hook()
        myjson = {'TIMESTAMP': self.TIMESTAMP}
        myjson['timestring'] = datetime.datetime.fromtimestamp(self.TIMESTAMP).strftime('%Y-%m-%d %H:%M:%S')
        myjson['files'] = [self._file_metadata(ff) for ff in self.files]
        self.jsondb.update_ts(self.TIMESTAMP, myjson)
        
        tmp = self.CONFIG['TMP_DIR']
        lstfile = os.path.join(tmp, 'gather_{0}.lst'.format(str(self.TIMESTAMP)))
        with open(lstfile, 'w') as flst:
            json.dump(myjson, flst, indent=2)
        self.files = self.files+[lstfile]

    def tar(self):
        ''' Full path preserving, default compression is LZMA '''
        # TODO: skipping tar on single file archives (w/ discarding lstfile)?
        # TODO: skipping full path?
        print('Tar...')
        flag, extension = self._comp[self.CONFIG['COMPRESSION']]
        self.archive = os.path.join(self.CONFIG['TMP_DIR'], 'arch_'+str(self.TIMESTAMP)+extension)
        tar = tarfile.open(self.archive, "w"+flag)
        for name in self.files:
            tar.add(name)#, arcname=os.path.basename(source_dir))
        tar.close()
        self.jsondb.update_ts(self.TIMESTAMP, 
                              {'compression': self.compression,
                               'archive_size': os.path.getsize(self.archive)})
    def encrypt(self):
        ''' Encrypts archive with AES'''
        print('Encrypt...')
        key_path = self.CONFIG['PUBL_RSA_KEY_PATH']
        with open(key_path) as f:
            publ_key = f.read()
        
        self.jsondb.update_ts(self.TIMESTAMP, {'used_public_key': publ_key,
                                               'public_key_path': key_path})
        self.encrypted_archive = self.archive+'.bin'
    
        with open(self.encrypted_archive, 'wb') as out_file:
            recipient_key = RSA.import_key(publ_key)
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

    def upload(self):
        ''' Uploads archive '''
        print('Upload...')
        self.jsondb.update_ts(self.TIMESTAMP, 
                              {'region_name': self.CONFIG['REGION_NAME'],
                               'vault_name': self.CONFIG['VAULT_NAME'],
                               'descryption': self.description,})
        
        glacier = boto3.client('glacier',
                               region_name = self.CONFIG['REGION_NAME'],
                               aws_access_key_id = self.CONFIG['AWS_ACCESS_KEY_ID'],
                               aws_secret_access_key = self.CONFIG['AWS_SECRET_ACCESS_KEY'])
        # TODO: error logging
        response = glacier.upload_archive(vaultName = self.CONFIG['VAULT_NAME'],
                                          archiveDescription = self.description,
                                          body = open(self.encrypted_archive, 'rb'))

        print(str(response))
        self.jsondb.update_ts(self.TIMESTAMP, {'response':response})
        
    def tmp_clean(self):
        # TODO: clean TMP_DIR
        pass

    @classmethod
    def run(cls):
        ''' Runs backup job, classmethod
        
        This basically invokes gather(), tar(), encrypt(), upload() methods in order,
        while taking care for exception handling and JSON data log management.'''
        print('Starting...')
        global _jsondb
        TS, jsondb = time.time(), _jsondb(cls.CONFIG)
        jsondb.add_ts(TS, {'JOB SUCCEED': False})
        gbbg = cls(TS, jsondb)
        try:
            gbbg.gather()
            gbbg.tar()
            gbbg.encrypt()
            gbbg.upload()
        except:
            # TODO: error logging
            raise
        else:
            jsondb.update_ts(TS, {'JOB SUCCEED': True})
        finally:
            gbbg.tmp_clean()

    @classmethod
    def read_config(cls, path):
        with open(path, 'r') as f:
            cls.CONFIG = json.load(f)


def auto_glacier(files, list_of_globs, description):
    class Backup(GTEU):
        files = files
        list_of_globs = list_of_globs
        description = description

    Backup.read_config('~/.config/autoglacier/CONFIG.json')
    Backup.run()


if __name__ == "__main__":
    pass
