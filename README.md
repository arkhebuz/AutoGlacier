


# GlacierBackup
A tool to track small files and back them up into Glacier enabling disaster-recovery document
 backups at virtually no cost - installable via pip:
```
$ pip install glacierbackup
```

What follows is an overview of a CLI interface.


```usage: GlacierBackup [-h] {init,register,job,config} ...

GlacierBackup tracks and backs-up small files into Amazon Glacier.
Example usage:

    $ glacierbackup init ./conf.json --genkeys
    $ glacierbackup register --filelist ~/small_files.lst
    $ glacierbackup job

positional arguments:
  {init,register,job,config}
    init                Initialize GlacierBackup configuration and database
    register            Register files in GlacierBackup database
    job                 Do backup Job - gathers and uploads files into Glacier
    config              Show/add/delete GlacierBackup configuration sets

optional arguments:
  -h, --help            show this help message and exit

This Amazon Glacier backup script is aimed at the case when one needs to 
back-up a considerable number of small files into cold-storage, i.e. to 
prevent data loss caused by ransomware attack. GlacierBackup keeps track 
of files: checks if their contents changed, backs them up if so, and notes 
which version of which file was backed up into which archive and when.
This information comes very handy as every uploaded backup is an
AES-encrypted LZMA-compressed tar archive.

The tool is aimed at simplicity, portability and extendability, featuring
file changes tracking, local metadata logging, data compression, encryption
and (some) file-picking functionality. Alpha at the moment (although it works!).
```


### `glacierbackup init`

```usage: GlacierBackup init [-h] [--genkeys] config_file

positional arguments:
  config_file  path to config file in JSON format

optional arguments:
  -h, --help   show this help message and exit
  --genkeys    generate RSA key pair

The init command creates database directory, set-ups the required local
SQLite database and saves initial config into it. The initial config 
will be always written to the database with set_id=0. If --genkeys flag 
is activated an RSA key pair will be generated (no passphrase!) and 
saved as plain files in the database directory, the public key will
be also saved in the configuration set_id=0.

The config_file should be a proper JSON file storing 
the following parameters:
    {
      "set_id" : 0,
      "database_dir": database_directory,
      "compression_algorithm" : "lzma",
      "temporary_dir": tmp_dir,
      "public_key": "key",
      "region_name": "eu-west-1",
      "vault_name": "MyVault",
      "aws_access_key_id": "key",
      "aws_secret_access_key": "key"
    }
```


### `glacierbackup register`

```usage: GlacierBackup register [-h] [--database DATABASE] [--configid CONFIGID] [--filelist FILELIST]

optional arguments:
  -h, --help           show this help message and exit
  --database DATABASE  path to GB database
  --configid CONFIGID  configuration set ID
  --filelist FILELIST  read files from text file, one absolute path per line

Register registers files in the database, or more precisely speaking,
absolute paths to files. GlacierBackup stores no information about file 
contents aside from SHA256 hash, however currently it determines if 
the file has changed and backup is needed from the modification time.
```


### `glacierbackup job`

```usage: GlacierBackup job [-h] [--database DATABASE] [--configid CONFIGID]

optional arguments:
  -h, --help           show this help message and exit
  --database DATABASE  path to GB database
  --configid CONFIGID  configuration set ID

GlacierBackup backup job is launched against a database and proceeds in an
automated fashion. GlacierBackup checks if any new files were registered 
and if any old registered files were changed, then gathers them, packs,
encrypts and uploads into Glacier using credentials from a given 
configuration set (default 0). Jobs can be safely cron-automated.
```


### `glacierbackup config`

```usage: GlacierBackup config [-h] [--show]

optional arguments:
  -h, --help  show this help message and exit
  --show      show existing configs
```

