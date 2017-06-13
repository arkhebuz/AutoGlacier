# pycryptodome package
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP


def manage_configs(argparse_args):
    if argparse_args.show:
        from autoglacier.database import GBDatabase
        with GBDatabase(argparse_args.database) as DB:
            config = DB.read_config_from_db(set_id=argparse_args.configid)
            for k in config.keys():
                print(k, ' = ', config[k])


def download_archive():
    # TODO
    pass

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


if __name__ == "__main__":
    pass
