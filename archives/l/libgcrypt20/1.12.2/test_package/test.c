#include <gcrypt.h>

#include <stdio.h>
#include <string.h>

static int expect_bytes(const char *name, const unsigned char *actual,
                        const unsigned char *expected, size_t size) {
    size_t index;

    if (memcmp(actual, expected, size) != 0) {
        fprintf(stderr, "%s mismatch\n", name);
        fprintf(stderr, "actual:   ");
        for (index = 0; index < size; ++index) {
            fprintf(stderr, "%02x", actual[index]);
        }
        fprintf(stderr, "\nexpected: ");
        for (index = 0; index < size; ++index) {
            fprintf(stderr, "%02x", expected[index]);
        }
        fprintf(stderr, "\n");
        return 1;
    }
    return 0;
}

static int initialize_gcrypt(void) {
    if (!gcry_check_version(GCRYPT_VERSION)) {
        fprintf(stderr, "libgcrypt version check failed\n");
        return 1;
    }
    if (gcry_control(GCRYCTL_DISABLE_SECMEM, 0) ||
        gcry_control(GCRYCTL_INITIALIZATION_FINISHED, 0)) {
        fprintf(stderr, "libgcrypt initialization failed\n");
        return 1;
    }
    return 0;
}

static int test_version(void) {
    return gcry_check_version("1.12.2") == NULL;
}

static int test_sha256(void) {
    static const unsigned char expected[32] = {
        0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
        0x41, 0x41, 0x40, 0xde, 0x5d, 0xae, 0x22, 0x23,
        0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c,
        0xb4, 0x10, 0xff, 0x61, 0xf2, 0x00, 0x15, 0xad
    };
    unsigned char actual[32];
    gcry_md_hash_buffer(GCRY_MD_SHA256, actual, "abc", 3);
    return expect_bytes("SHA-256", actual, expected, sizeof(actual));
}

static int test_sha512(void) {
    static const unsigned char expected[64] = {
        0xdd, 0xaf, 0x35, 0xa1, 0x93, 0x61, 0x7a, 0xba,
        0xcc, 0x41, 0x73, 0x49, 0xae, 0x20, 0x41, 0x31,
        0x12, 0xe6, 0xfa, 0x4e, 0x89, 0xa9, 0x7e, 0xa2,
        0x0a, 0x9e, 0xee, 0xe6, 0x4b, 0x55, 0xd3, 0x9a,
        0x21, 0x92, 0x99, 0x2a, 0x27, 0x4f, 0xc1, 0xa8,
        0x36, 0xba, 0x3c, 0x23, 0xa3, 0xfe, 0xeb, 0xbd,
        0x45, 0x4d, 0x44, 0x23, 0x64, 0x3c, 0xe8, 0x0e,
        0x2a, 0x9a, 0xc9, 0x4f, 0xa5, 0x4c, 0xa4, 0x9f
    };
    unsigned char actual[64];
    gcry_md_hash_buffer(GCRY_MD_SHA512, actual, "abc", 3);
    return expect_bytes("SHA-512", actual, expected, sizeof(actual));
}

static int test_sha3_256(void) {
    static const unsigned char expected[32] = {
        0x3a, 0x98, 0x5d, 0xa7, 0x4f, 0xe2, 0x25, 0xb2,
        0x04, 0x5c, 0x17, 0x2d, 0x6b, 0xd3, 0x90, 0xbd,
        0x85, 0x5f, 0x08, 0x6e, 0x3e, 0x9d, 0x52, 0x5b,
        0x46, 0xbf, 0xe2, 0x45, 0x11, 0x43, 0x15, 0x32
    };
    unsigned char actual[32];
    gcry_md_hash_buffer(GCRY_MD_SHA3_256, actual, "abc", 3);
    return expect_bytes("SHA3-256", actual, expected, sizeof(actual));
}

static int test_hmac_sha256(void) {
    static const unsigned char expected[32] = {
        0xf7, 0xbc, 0x83, 0xf4, 0x30, 0x53, 0x84, 0x24,
        0xb1, 0x32, 0x98, 0xe6, 0xaa, 0x6f, 0xb1, 0x43,
        0xef, 0x4d, 0x59, 0xa1, 0x49, 0x46, 0x17, 0x59,
        0x97, 0x47, 0x9d, 0xbc, 0x2d, 0x1a, 0x3c, 0xd8
    };
    static const char message[] = "The quick brown fox jumps over the lazy dog";
    unsigned char actual[32];
    size_t actual_size = sizeof(actual);
    gcry_mac_hd_t mac = NULL;
    gcry_error_t error = gcry_mac_open(&mac, GCRY_MAC_HMAC_SHA256, 0, NULL);

    if (!error) {
        error = gcry_mac_setkey(mac, "key", 3);
    }
    if (!error) {
        error = gcry_mac_write(mac, message, strlen(message));
    }
    if (!error) {
        error = gcry_mac_read(mac, actual, &actual_size);
    }
    if (mac != NULL) {
        gcry_mac_close(mac);
    }
    if (error || actual_size != sizeof(actual)) {
        fprintf(stderr, "HMAC-SHA256 API failed: %s\n", gcry_strerror(error));
        return 1;
    }
    return expect_bytes("HMAC-SHA256", actual, expected, sizeof(actual));
}

static int test_cmac_aes(void) {
    static const unsigned char key[16] = {
        0x2b, 0x7e, 0x15, 0x16, 0x28, 0xae, 0xd2, 0xa6,
        0xab, 0xf7, 0x15, 0x88, 0x09, 0xcf, 0x4f, 0x3c
    };
    static const unsigned char message[16] = {
        0x6b, 0xc1, 0xbe, 0xe2, 0x2e, 0x40, 0x9f, 0x96,
        0xe9, 0x3d, 0x7e, 0x11, 0x73, 0x93, 0x17, 0x2a
    };
    static const unsigned char expected[16] = {
        0x07, 0x0a, 0x16, 0xb4, 0x6b, 0x4d, 0x41, 0x44,
        0xf7, 0x9b, 0xdd, 0x9d, 0xd0, 0x4a, 0x28, 0x7c
    };
    unsigned char actual[16];
    size_t actual_size = sizeof(actual);
    gcry_mac_hd_t mac = NULL;
    gcry_error_t error = gcry_mac_open(&mac, GCRY_MAC_CMAC_AES, 0, NULL);

    if (!error) {
        error = gcry_mac_setkey(mac, key, sizeof(key));
    }
    if (!error) {
        error = gcry_mac_write(mac, message, sizeof(message));
    }
    if (!error) {
        error = gcry_mac_read(mac, actual, &actual_size);
    }
    if (mac != NULL) {
        gcry_mac_close(mac);
    }
    if (error || actual_size != sizeof(actual)) {
        fprintf(stderr, "CMAC-AES API failed: %s\n", gcry_strerror(error));
        return 1;
    }
    return expect_bytes("CMAC-AES", actual, expected, sizeof(actual));
}

static int aes128_ecb(int decrypt) {
    static const unsigned char key[16] = {
        0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
        0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f
    };
    static const unsigned char plain[16] = {
        0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
        0x88, 0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff
    };
    static const unsigned char cipher[16] = {
        0x69, 0xc4, 0xe0, 0xd8, 0x6a, 0x7b, 0x04, 0x30,
        0xd8, 0xcd, 0xb7, 0x80, 0x70, 0xb4, 0xc5, 0x5a
    };
    const unsigned char *input = decrypt ? cipher : plain;
    const unsigned char *expected = decrypt ? plain : cipher;
    unsigned char actual[16];
    gcry_cipher_hd_t handle = NULL;
    gcry_error_t error = gcry_cipher_open(
        &handle, GCRY_CIPHER_AES128, GCRY_CIPHER_MODE_ECB, 0);

    if (!error) {
        error = gcry_cipher_setkey(handle, key, sizeof(key));
    }
    if (!error && decrypt) {
        error = gcry_cipher_decrypt(
            handle, actual, sizeof(actual), input, sizeof(cipher));
    } else if (!error) {
        error = gcry_cipher_encrypt(
            handle, actual, sizeof(actual), input, sizeof(plain));
    }
    if (handle != NULL) {
        gcry_cipher_close(handle);
    }
    if (error) {
        fprintf(stderr, "AES-128 ECB API failed: %s\n", gcry_strerror(error));
        return 1;
    }
    return expect_bytes(
        decrypt ? "AES-128 decrypt" : "AES-128 encrypt",
        actual, expected, sizeof(actual));
}

static int test_aes256_cbc(void) {
    static const unsigned char key[32] = {
        0x60, 0x3d, 0xeb, 0x10, 0x15, 0xca, 0x71, 0xbe,
        0x2b, 0x73, 0xae, 0xf0, 0x85, 0x7d, 0x77, 0x81,
        0x1f, 0x35, 0x2c, 0x07, 0x3b, 0x61, 0x08, 0xd7,
        0x2d, 0x98, 0x10, 0xa3, 0x09, 0x14, 0xdf, 0xf4
    };
    static const unsigned char iv[16] = {
        0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
        0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f
    };
    static const unsigned char plain[16] = {
        0x6b, 0xc1, 0xbe, 0xe2, 0x2e, 0x40, 0x9f, 0x96,
        0xe9, 0x3d, 0x7e, 0x11, 0x73, 0x93, 0x17, 0x2a
    };
    static const unsigned char expected[16] = {
        0xf5, 0x8c, 0x4c, 0x04, 0xd6, 0xe5, 0xf1, 0xba,
        0x77, 0x9e, 0xab, 0xfb, 0x5f, 0x7b, 0xfb, 0xd6
    };
    unsigned char cipher[16];
    unsigned char recovered[16];
    gcry_cipher_hd_t handle = NULL;
    gcry_error_t error = gcry_cipher_open(
        &handle, GCRY_CIPHER_AES256, GCRY_CIPHER_MODE_CBC, 0);

    if (!error) {
        error = gcry_cipher_setkey(handle, key, sizeof(key));
    }
    if (!error) {
        error = gcry_cipher_setiv(handle, iv, sizeof(iv));
    }
    if (!error) {
        error = gcry_cipher_encrypt(
            handle, cipher, sizeof(cipher), plain, sizeof(plain));
    }
    if (error || expect_bytes("AES-256 CBC", cipher, expected, sizeof(cipher))) {
        if (handle != NULL) {
            gcry_cipher_close(handle);
        }
        return 1;
    }
    gcry_cipher_reset(handle);
    error = gcry_cipher_setkey(handle, key, sizeof(key));
    if (!error) {
        error = gcry_cipher_setiv(handle, iv, sizeof(iv));
    }
    if (!error) {
        error = gcry_cipher_decrypt(
            handle, recovered, sizeof(recovered), cipher, sizeof(cipher));
    }
    gcry_cipher_close(handle);
    return error || expect_bytes(
        "AES-256 CBC roundtrip", recovered, plain, sizeof(recovered));
}

static int test_chacha20(void) {
    static const unsigned char key[32] = {
        0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
        0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
        0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
        0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f
    };
    static const unsigned char nonce[12] = {
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x02
    };
    static const unsigned char plain[32] = {
        0x6c, 0x69, 0x62, 0x67, 0x63, 0x72, 0x79, 0x70,
        0x74, 0x20, 0x63, 0x68, 0x61, 0x63, 0x68, 0x61,
        0x32, 0x30, 0x20, 0x70, 0x6f, 0x72, 0x74, 0x61,
        0x62, 0x69, 0x6c, 0x69, 0x74, 0x79, 0x21, 0x21
    };
    unsigned char cipher[32];
    unsigned char recovered[32];
    gcry_cipher_hd_t handle = NULL;
    gcry_error_t error = gcry_cipher_open(
        &handle, GCRY_CIPHER_CHACHA20, GCRY_CIPHER_MODE_STREAM, 0);

    if (!error) {
        error = gcry_cipher_setkey(handle, key, sizeof(key));
    }
    if (!error) {
        error = gcry_cipher_setiv(handle, nonce, sizeof(nonce));
    }
    if (!error) {
        error = gcry_cipher_encrypt(
            handle, cipher, sizeof(cipher), plain, sizeof(plain));
    }
    if (error || memcmp(cipher, plain, sizeof(cipher)) == 0) {
        if (handle != NULL) {
            gcry_cipher_close(handle);
        }
        return 1;
    }
    gcry_cipher_reset(handle);
    error = gcry_cipher_setkey(handle, key, sizeof(key));
    if (!error) {
        error = gcry_cipher_setiv(handle, nonce, sizeof(nonce));
    }
    if (!error) {
        error = gcry_cipher_decrypt(
            handle, recovered, sizeof(recovered), cipher, sizeof(cipher));
    }
    gcry_cipher_close(handle);
    return error || expect_bytes(
        "ChaCha20 roundtrip", recovered, plain, sizeof(recovered));
}

static int test_pbkdf2_sha256(void) {
    static const unsigned char expected[32] = {
        0x12, 0x0f, 0xb6, 0xcf, 0xfc, 0xf8, 0xb3, 0x2c,
        0x43, 0xe7, 0x22, 0x52, 0x56, 0xc4, 0xf8, 0x37,
        0xa8, 0x65, 0x48, 0xc9, 0x2c, 0xcc, 0x35, 0x48,
        0x08, 0x05, 0x98, 0x7c, 0xb7, 0x0b, 0xe1, 0x7b
    };
    unsigned char actual[32];
    gcry_error_t error = gcry_kdf_derive(
        "password", 8, GCRY_KDF_PBKDF2, GCRY_MD_SHA256,
        "salt", 4, 1, sizeof(actual), actual);
    return error || expect_bytes("PBKDF2-SHA256", actual, expected, sizeof(actual));
}

static int test_mpi_add(void) {
    gcry_mpi_t left = gcry_mpi_set_ui(NULL, 1234);
    gcry_mpi_t right = gcry_mpi_set_ui(NULL, 5678);
    gcry_mpi_t result = gcry_mpi_new(0);
    int failed;

    gcry_mpi_add(result, left, right);
    failed = gcry_mpi_cmp_ui(result, 6912) != 0;
    gcry_mpi_release(result);
    gcry_mpi_release(right);
    gcry_mpi_release(left);
    return failed;
}

static int test_mpi_mod(void) {
    gcry_mpi_t value = gcry_mpi_set_ui(NULL, 65537);
    gcry_mpi_t modulus = gcry_mpi_set_ui(NULL, 257);
    gcry_mpi_t result = gcry_mpi_new(0);
    int failed;

    gcry_mpi_mod(result, value, modulus);
    failed = gcry_mpi_cmp_ui(result, 2) != 0;
    gcry_mpi_release(result);
    gcry_mpi_release(modulus);
    gcry_mpi_release(value);
    return failed;
}

static int test_sexp(void) {
    static const char payload[] = "abc";
    gcry_sexp_t expression = NULL;
    gcry_sexp_t value = NULL;
    const char *actual;
    size_t actual_size = 0;
    gcry_error_t error = gcry_sexp_build(
        &expression, NULL, "(data (flags raw) (value %b))",
        (int)sizeof(payload) - 1, payload);

    if (!error) {
        value = gcry_sexp_find_token(expression, "value", 0);
    }
    actual = value ? gcry_sexp_nth_data(value, 1, &actual_size) : NULL;
    if (error || actual == NULL || actual_size != sizeof(payload) - 1 ||
        memcmp(actual, payload, actual_size) != 0) {
        gcry_sexp_release(value);
        gcry_sexp_release(expression);
        return 1;
    }
    gcry_sexp_release(value);
    gcry_sexp_release(expression);
    return 0;
}

static int test_nonce(void) {
    unsigned char first[32] = {0};
    unsigned char second[32] = {0};
    unsigned char zero[32] = {0};

    gcry_create_nonce(first, sizeof(first));
    gcry_create_nonce(second, sizeof(second));
    return memcmp(first, zero, sizeof(first)) == 0 ||
           memcmp(second, zero, sizeof(second)) == 0 ||
           memcmp(first, second, sizeof(first)) == 0;
}

struct test_case {
    const char *name;
    int (*run)(void);
};

static const struct test_case test_cases[] = {
    {"version", test_version},
    {"sha256", test_sha256},
    {"sha512", test_sha512},
    {"sha3-256", test_sha3_256},
    {"hmac-sha256", test_hmac_sha256},
    {"cmac-aes", test_cmac_aes},
    {"aes128-ecb-encrypt", NULL},
    {"aes128-ecb-decrypt", NULL},
    {"aes256-cbc", test_aes256_cbc},
    {"chacha20", test_chacha20},
    {"pbkdf2-sha256", test_pbkdf2_sha256},
    {"mpi-add", test_mpi_add},
    {"mpi-mod", test_mpi_mod},
    {"sexp", test_sexp},
    {"nonce", test_nonce}
};

int main(int argc, char **argv) {
    size_t index;
    int result;

    if (argc != 2 || initialize_gcrypt()) {
        fprintf(stderr, "expected one initialized test case\n");
        return 2;
    }
    for (index = 0; index < sizeof(test_cases) / sizeof(test_cases[0]); ++index) {
        if (strcmp(argv[1], test_cases[index].name) != 0) {
            continue;
        }
        if (strcmp(argv[1], "aes128-ecb-encrypt") == 0) {
            result = aes128_ecb(0);
        } else if (strcmp(argv[1], "aes128-ecb-decrypt") == 0) {
            result = aes128_ecb(1);
        } else {
            result = test_cases[index].run();
        }
        if (result == 0) {
            printf("PASS %s\n", argv[1]);
        }
        return result;
    }
    fprintf(stderr, "unknown test case: %s\n", argv[1]);
    return 2;
}
