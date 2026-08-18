/* Stub implementations for libtermkey API on OHOS (not published).
 * All functions return minimal values so vis compiles and links.
 * SPDX-License-Identifier: ISC */
#include <stdlib.h>

#include "termkey.h"

unsigned long termkey_get_version(void) { return TERMKEY_VERSION; }
TermKey *termkey_new(int fd, int flags) {
    (void) fd; (void) flags;
    return NULL;
}
TermKey *termkey_new_abstract(const char *term, int flags) {
    (void) term; (void) flags;
    return NULL;
}
void termkey_free(TermKey *tk) { (void) tk; }
void termkey_destroy(TermKey *tk) { (void) tk; }
int termkey_start(TermKey *tk) { (void) tk; return 0; }
int termkey_stop(TermKey *tk) { (void) tk; return 0; }
void termkey_reopen(TermKey *tk, int fd, int flags) {
    (void) tk; (void) fd; (void) flags;
}
size_t termkey_push_bytes(TermKey *tk, const char *bytes, size_t len) {
    (void) tk; (void) bytes; (void) len;
    return 0;
}
size_t termkey_interpret_key(TermKey *tk, char *buffer, size_t buflen,
                             int flags, TermKeyResult *result) {
    (void) tk; (void) buffer; (void) buflen; (void) flags;
    if (result) *result = TERMKEY_RES_NONE;
    return 0;
}
TermKeyResult termkey_getkey(TermKey *tk, TermKeyKey *key) {
    (void) tk; (void) key;
    return TERMKEY_RES_NONE;
}
TermKeyResult termkey_getkey_force(TermKey *tk, TermKeyKey *key) {
    (void) tk; (void) key;
    return TERMKEY_RES_NONE;
}
TermKeyResult termkey_waitkey(TermKey *tk, TermKeyKey *key) {
    (void) tk; (void) key;
    return TERMKEY_RES_NONE;
}
TermKeyResult termkey_getkey_force_sse(TermKey *tk, TermKeyKey *key) {
    (void) tk; (void) key;
    return TERMKEY_RES_NONE;
}
int termkey_advisereadable(TermKey *tk) { (void) tk; return 0; }
size_t termkey_get_buffer_remaining(TermKey *tk) { (void) tk; return 0; }
int termkey_get_waittime(TermKey *tk) { (void) tk; return 0; }
int termkey_set_waittime(TermKey *tk, int waittime) {
    (void) tk; (void) waittime;
    return 0;
}
int termkey_get_canonflags(TermKey *tk) { (void) tk; return 0; }
int termkey_set_canonflags(TermKey *tk, int flags) {
    (void) tk; (void) flags;
    return 0;
}
int termkey_get_flags(TermKey *tk) { (void) tk; return 0; }
int termkey_set_flags(TermKey *tk, int flags) { (void) tk; (void) flags; return 0; }
size_t termkey_strfkey(TermKey *tk, char *buffer, size_t len,
                       TermKeyKey *key, int flags) {
    (void) tk; (void) buffer; (void) len; (void) key; (void) flags;
    return 0;
}
const char *termkey_strpkey(TermKey *tk, const char *str, TermKeyKey *key,
                           int flags) {
    (void) tk; (void) str; (void) key; (void) flags;
    return str;
}
const char *termkey_get_keyname(TermKey *tk, TermKeySym sym) {
    (void) tk; (void) sym;
    return "unknown";
}
TermKeySym termkey_keyname2sym(const char *keyname) {
    (void) keyname;
    return TERMKEY_SYM_UNKNOWN;
}
int termkey_interpret_csi(TermKey *tk, TermKeyKey *key, long *args,
                          size_t *nargs, unsigned long *cmd) {
    (void) tk; (void) key; (void) args; (void) nargs; (void) cmd;
    return TERMKEY_RES_NONE;
}
size_t termkey_interpret_mouse(TermKey *tk, const char *buffer, size_t len,
                               TermKeyMouseEventInfo *info, int *flags) {
    (void) tk; (void) buffer; (void) len; (void) info; (void) flags;
    return 0;
}
int termkey_parse_darwin(TermKey *tk, TermKeyKey *key, const char *buffer,
                         size_t len) {
    (void) tk; (void) key; (void) buffer; (void) len;
    return 0;
}
