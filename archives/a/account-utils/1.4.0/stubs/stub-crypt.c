/* Stub implementations for libxcrypt (crypt) API on OHOS.
 * SPDX-License-Identifier: BSD-3-Clause */
#include <stddef.h>

#include "crypt.h"

char *crypt(const char *key, const char *salt) {
    (void) key; (void) salt;
    return NULL;
}
char *crypt_r(const char *key, const char *salt, struct crypt_data *data) {
    (void) key; (void) salt; (void) data;
    return NULL;
}
char *crypt_gensalt(const char *prefix, unsigned long count,
                    const char *rbytes, int nrbytes) {
    (void) prefix; (void) count; (void) rbytes; (void) nrbytes;
    return NULL;
}
char *crypt_gensalt_r(const char *prefix, unsigned long count,
                      const char *rbytes, int nrbytes, char *output,
                      int output_size) {
    (void) prefix; (void) count; (void) rbytes; (void) nrbytes;
    (void) output; (void) output_size;
    return NULL;
}
char *crypt_gensalt_rn(const char *prefix, unsigned long count,
                       const char *rbytes, int nrbytes, char *output,
                       int output_size) {
    (void) prefix; (void) count; (void) rbytes; (void) nrbytes;
    (void) output; (void) output_size;
    return NULL;
}
char *crypt_gensalt_ra(const char *prefix, unsigned long count,
                       const char *rbytes, int nrbytes) {
    (void) prefix; (void) count; (void) rbytes; (void) nrbytes;
    return NULL;
}

int crypt_checksalt(const char *salt) {
    (void) salt;
    return 0; /* CRYPT_SALT_OK */
}
