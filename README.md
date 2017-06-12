

## AutoGlacier

```usage: AutoGlacier [-h] {init,register,job,config} ...

AutoGlacier tracks and backs-up small files into Amazon Glacier.
Example usage:

    $ autoglacier init ./conf.json --genkeys
    $ autoglacier register --filelist ~/small_files.lst
    $ autoglacier job

positional arguments:
  {init,register,job,config}
    init                Initialize AutoGlacier configuration and database
    register            Register files in AutoGlacier database
    job                 Do backup Job - gathers and uploads files into Glacier
    config              Show/add/delete AutoGlacier configuration sets

optional arguments:
  -h, --help            show this help message and exit

This Amazon Glacier backup script is aimed at the case when one needs to 
back-up a considerable number of small files into cold-storage, i.e. to 
prevent data loss caused by ransomware attack. AutoGlacier keeps track 
of files: checks if their contents changed, backs them up if so, and notes 
which version of which file was backed up into which archive and when.
This information comes very handy as every uploaded backup is an
AES-encrypted LZMA-compressed tar archive.

The tool is aimed at simplicity, portability and extendability, featuring
file changes tracking, local metadata logging, data compression, encryption
and (some) file-picking functionality. Alpha at the moment (although it works!).
```


### `autoglacier init`

```usage: AutoGlacier init [-h] [--genkeys] config_file

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
      "ag_database_dir": database_directory,
      "compression_algorithm" : "lzma",
      "temporary_dir": tmp_dir,
      "public_key": "key",
      "region_name": "eu-west-1",
      "vault_name": "MyVault",
      "aws_access_key_id": "key",
      "aws_secret_access_key": "key"
    }
```


### `autoglacier register`

```usage: AutoGlacier register [-h] [--database DATABASE] [--configid CONFIGID] [--filelist FILELIST]

optional arguments:
  -h, --help           show this help message and exit
  --database DATABASE  path to AG database
  --configid CONFIGID  configuration set ID
  --filelist FILELIST  read files from text file, one absolute path per line

Register registers files in the database, or more precisely speaking,
absolute paths to files. AutoGlacier stores no information about file 
contents aside from SHA256 hash, however currently it determines if 
the file has changed and backup is needed from the modification time.
```


### `autoglacier job`

```usage: AutoGlacier job [-h] [--database DATABASE] [--configid CONFIGID]

optional arguments:
  -h, --help           show this help message and exit
  --database DATABASE  path to AG database
  --configid CONFIGID  configuration set ID

AutoGlacier backup job is launched against a database and proceeds in an
automated fashion. AutoGlacier checks if any new files were registered 
and if any old registered files were changed, then gathers them, packs,
encrypts and uploads into Glacier using credentials from a given 
configuration set (default 0). Jobs can be safely cron-automated.
```


### `autoglacier config`

```usage: AutoGlacier config [-h] [--show]

optional arguments:
  -h, --help  show this help message and exit
  --show      show existing configs
```

