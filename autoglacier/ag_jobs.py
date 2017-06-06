

def do_backup_job():
    # TODO
    gteu = GTEU()
    gteu.get_files_from_db()
    gteu.archive_files()
    gteu.encrypt_files()
    gteu.glacier_upload()
    gteu.clean_tmp()


class GTEU(object):
    # Formats supported by stdlib's tarfile:
    _comp = {'gzip': [':gz', '.tar.gz'],
             'lzma': [':xz', '.tar.xz'],
             'bzip2': [':bz2', '.tar.bz2'],
             'none': ['', '.tar'],
             '': ['', '.tar']}
    
    def __init__(self):
        pass
    
    def get_files_from_db(self):
        pass
    
    def archive_files(self):
        pass
    
    def encrypt_archive(self):
        pass
    
    def _generate_description(sef):
        pass
    
    def glacier_upload(self):
        pass
    
    def clean_tmp(self):
        pass
