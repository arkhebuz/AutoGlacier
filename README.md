Amazon Glacier backup script aimed at simplicity, portability and extendability, 
featuring (some) file-picking functionality, data encryption and local metadata logging.

Alpha at the moment.
---

## GTEU class

**G**athers files, **T**ars them up, **E**ncrypts and **U**ploads them into Glacier 
    
Use case: 1 AWS user uploads 1 encrypted single-part archive to a single Glacier vault.
GTEU class employs a simple 1-directional internal data/execution flow to do just that: 
  `GTEU.gather() -> GTEU.tar() -> GTEU.encrypt() -> GTEU.upload()`

In addition, process metadata (including backed-up files locations and their
SHA hashes) is saved into a flat-file JSON database indexed by unix timestamp
at script launch.

Backup job can be defined by inheriting from this class and overwriting 
configuration variables, including lists of files to be backed up or
directories to be backed-up non-recursively (Python glob module syntax).
More advanced file-picking code can be added by re-implementing gather hook 
method (GTEU.gather_hook). Job can be started by invoking run() classmethod
on a newly defined class (see example).

Backup is uploaded as an LZMA-compressed tar archive encrypted with AES using
RSA keys (only the public key is required).

Currently this class is ill-siuted for large files (single-part upload only,
in-memory file hashing) or huge numbers of small files (separate hashing and
taring steps causes files to be read into memory twice). Also the code isn't
fully thread-safe (data log writing, race condition with timestamps)


**Example backup job script:**


```python
import glob, os
from autoglacier import GTEU


class Backup(GTEU):
    # A JSON configuration dictionary
    CONFIG = {
      # Default compression algorithm:
      'COMPRESSION' = "lzma",
      'TMP_DIR': "/tmp",
      'JSON_DATABASE': '/home/arkhebuz/AutoGlacier/log.json',
    
      # passphrase used for key generation and file decryption
      'RSA_PASSPHRASE': None,     # None == no passphrase
      'PUBL_RSA_KEY_PATH': "/home/arkhebuz/AutoGlacier/my_rsa_public.pem",
    
      # Glacier account (IAM user) settings - single user, region and vault
      'REGION_NAME': 'eu-west-1',
      'VAULT_NAME': 'TestVault1',
      'AWS_ACCESS_KEY_ID': "key",
      'AWS_SECRET_ACCESS_KEY': "key",
    }

    # Explicit list of files to be backed up (full paths)
    files = ['/home/arkhebuz/view.sh'. /home/arkhebuz/login.sh']

    # List of glob patterns to be matched, result is added to `files` list
    list_of_globs = ['/home/arkhebuz/scripts/*.sh',]

    # Archive description for Glacier upload
    description = "shell scripts archive"
    
    # Implementing additional file-picking by overwriting placeholder function
    def gather_hook(self):
        newest = max(glob.iglob('/home/arkhebuz/bugging/bug*.sh'), key=os.path.getmtime)
        self.files.append(newest)


if __name__ == "__main__":
    Backup.run()    # Run is a classmethod
```
