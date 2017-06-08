import sqlite3
import os



def manage_configs(arpgaprse_args):
    pass


def read_config_from_db(database_path, set_id=0):
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute( 'SELECT * FROM ConfigurationSets WHERE set_id={}'.format(set_id) )
    CONFIG = c.fetchone()
    #~ print(dict(CONFIG))
    conn.close()
    return CONFIG
#~ read_config_from_db(os.path.join(os.path.expanduser('~'), '.autoglacier/AG_database.sqlite'))


def __remove_database_dir_with_contents(CONFIG):
    import shutil
    shutil.rmtree(CONFIG['ag_database_dir'])

def _create_test_backup_files_and_dirs(parent_dir):
    root_test_dir = os.path.join(parent_dir, '__test_backup_structure')
    os.mkdir(root_test_dir)
    
    dir1 = os.path.join(root_test_dir, 'dir1')
    os.mkdir(dir1)
    dir2 = os.path.join(root_test_dir, 'dir2')
    os.mkdir(dir2)
    for char in 'a10':
        for adir in (dir1, dir2):
            with open(os.path.join(adir, char), 'w') as f:
                f.write(char*10**5)
    
    file_list_loc = os.path.join(root_test_dir, '__test_backup_file_list.txt')
    paths = [root_test_dir+'/dir1/'+char for char in 'a10']
    paths += [root_test_dir+'/dir2/'+char for char in 'a10']
    with open(file_list_loc, 'w') as f:
        for p in paths:
            f.write(p)
            f.write('\n')
    return file_list_loc

def download_archive():
    # TODO
    pass



if __name__ == "__main__":
    pass
    #~ __create_test_backup_files_and_dirs()
