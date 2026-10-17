#include <mcrypt.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    static const unsigned char plaintext[16] = {
        'O', 'H', 'O', 'S', '-', 'l', 'i', 'b',
        'm', 'c', 'r', 'y', 'p', 't', '!', '!'
    };
    unsigned char buffer[16];
    unsigned char key[16] = {
        0x2b, 0x7e, 0x15, 0x16, 0x28, 0xae, 0xd2, 0xa6,
        0xab, 0xf7, 0x15, 0x88, 0x09, 0xcf, 0x4f, 0x3c
    };
    unsigned char iv[16] = {
        0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
        0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f
    };
    MCRYPT encryptor = mcrypt_module_open("rijndael-128", NULL, "cbc", NULL);
    MCRYPT decryptor = mcrypt_module_open("rijndael-128", NULL, "cbc", NULL);
    int encryptor_initialized = 0;
    int decryptor_initialized = 0;
    int result = 1;

    if (encryptor == MCRYPT_FAILED || decryptor == MCRYPT_FAILED) {
        puts("mcrypt_module_open failed");
        goto cleanup;
    }
    if (mcrypt_enc_get_block_size(encryptor) != 16) {
        puts("unexpected AES block size");
        goto cleanup;
    }

    memcpy(buffer, plaintext, sizeof(buffer));
    if (mcrypt_generic_init(encryptor, key, sizeof(key), iv) < 0) {
        puts("mcrypt_generic_init encryptor failed");
        goto cleanup;
    }
    encryptor_initialized = 1;
    if (mcrypt_generic(encryptor, buffer, sizeof(buffer)) < 0) {
        puts("mcrypt_generic encrypt failed");
        goto cleanup;
    }
    if (memcmp(buffer, plaintext, sizeof(buffer)) == 0) {
        puts("ciphertext did not change");
        goto cleanup;
    }

    if (mcrypt_generic_init(decryptor, key, sizeof(key), iv) < 0) {
        puts("mcrypt_generic_init decryptor failed");
        goto cleanup;
    }
    decryptor_initialized = 1;
    if (mdecrypt_generic(decryptor, buffer, sizeof(buffer)) < 0) {
        puts("mdecrypt_generic decrypt failed");
        goto cleanup;
    }
    if (memcmp(buffer, plaintext, sizeof(buffer)) != 0) {
        puts("decrypted text mismatch");
        goto cleanup;
    }

    puts("libmcrypt aes-cbc roundtrip ok");
    result = 0;

cleanup:
    if (encryptor_initialized) {
        mcrypt_generic_deinit(encryptor);
    }
    if (decryptor_initialized) {
        mcrypt_generic_deinit(decryptor);
    }
    if (encryptor != MCRYPT_FAILED) {
        mcrypt_module_close(encryptor);
    }
    if (decryptor != MCRYPT_FAILED) {
        mcrypt_module_close(decryptor);
    }
    return result;
}
