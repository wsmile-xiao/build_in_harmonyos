/* Minimal stub of crypt.h for OHOS (no libxcrypt).
 * SPDX-License-Identifier: BSD-3-Clause */
#ifndef CRYPT_STUB_H
#define CRYPT_STUB_H

#include <stddef.h>

/* libxcrypt size macros (approximate; only buffer sizing is affected) */
#define CRYPT_OUTPUT_SIZE           3848
#define CRYPT_GENSALT_OUTPUT_SIZE   192
#define CRYPT_MAX_PASSPHRASE_SIZE   512

struct crypt_data {
    char output[CRYPT_OUTPUT_SIZE];
    char setting[CRYPT_GENSALT_OUTPUT_SIZE];
    char input[CRYPT_MAX_PASSPHRASE_SIZE];
    char initialized;
};

#ifdef __cplusplus
extern "C" {
#endif

char *crypt(const char *key, const char *salt);
char *crypt_r(const char *key, const char *salt, struct crypt_data *data);
char *crypt_gensalt(const char *prefix, unsigned long count,
                    const char *rbytes, int nrbytes);
char *crypt_gensalt_r(const char *prefix, unsigned long count,
                      const char *rbytes, int nrbytes, char *output,
                      int output_size);
char *crypt_gensalt_rn(const char *prefix, unsigned long count,
                       const char *rbytes, int nrbytes, char *output,
                       int output_size);
char *crypt_gensalt_ra(const char *prefix, unsigned long count,
                       const char *rbytes, int nrbytes);

#ifdef __cplusplus
}
#endif

#endif /* CRYPT_STUB_H */

/* crypt_checksalt result codes (libxcrypt) */
#define CRYPT_SALT_OK            0
#define CRYPT_SALT_INVALID       1
#define CRYPT_SALT_METHOD_DISABLED 2
#define CRYPT_SALT_TOO_NEW       3
#define CRYPT_SALT_TOO_OLD       4
#define CRYPT_SALT_METHOD_LEGACY 5

int crypt_checksalt(const char *salt);
