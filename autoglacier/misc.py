
def manage_configs(arpgaprse_args):
    pass


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
    #~ __create_test_backup_files_and_dirs()
