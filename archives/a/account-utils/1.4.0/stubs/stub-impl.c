/* Stub implementations for sd-daemon/PAM/libxcrypt on OHOS.
 * (sd-varlink/sd-json stubs live in stub-varlink.c/stub-json.c)
 * SPDX-License-Identifier: LGPL-2.1-or-later */
#include <errno.h>
#include <stdarg.h>
#include <stdlib.h>
#include <stdint.h>
#include "systemd/sd-daemon.h"
#include "security/pam_stub.h"
#include "crypt.h"
/* ---- sd-daemon ---- */
int sd_notify(int unset_environment, const char *state) {
    (void) unset_environment; (void) state;
    return 0;
}
int sd_notifyf(int unset_environment, const char *format, ...) {
    (void) unset_environment; (void) format;
    return 0;
}
int sd_listen_fds(int unset_environment) { (void) unset_environment; return 0; }
int sd_listen_fds_with_names(int unset_environment, char ***names) {
    (void) unset_environment;
    if (names) *names = NULL;
    return 0;
}
int sd_watchdog_enabled(int unset_environment, uint64_t *usec) {
    (void) unset_environment;
    if (usec) *usec = 0;
    return 0;
}
int sd_booted(void) { return 0; }

/* ---- PAM ---- */
int pam_start(const char *service_name, const char *user,
              const pam_conv_t *pam_conversation, pam_handle_t **pamh) {
    (void) service_name; (void) user; (void) pam_conversation;
    if (pamh) *pamh = NULL;
    return PAM_SUCCESS;
}
int pam_end(pam_handle_t *pamh, int pam_status) {
    (void) pamh; (void) pam_status;
    return PAM_SUCCESS;
}
const char *pam_strerror(pam_handle_t *pamh, int errnum) {
    (void) pamh; (void) errnum;
    return "pam stub";
}
int pam_get_item(const pam_handle_t *pamh, int item_type, const void **item) {
    (void) pamh; (void) item_type;
    if (item) *item = NULL;
    return PAM_SUCCESS;
}
int pam_set_item(pam_handle_t *pamh, int item_type, const void *item) {
    (void) pamh; (void) item_type; (void) item;
    return PAM_SUCCESS;
}
int pam_authenticate(pam_handle_t *pamh, int flags) { (void) pamh; (void) flags; return PAM_SUCCESS; }
int pam_acct_mgmt(pam_handle_t *pamh, int flags) { (void) pamh; (void) flags; return PAM_SUCCESS; }
int pam_open_session(pam_handle_t *pamh, int flags) { (void) pamh; (void) flags; return PAM_SUCCESS; }
int pam_close_session(pam_handle_t *pamh, int flags) { (void) pamh; (void) flags; return PAM_SUCCESS; }
int pam_chauthtok(pam_handle_t *pamh, int flags) { (void) pamh; (void) flags; return PAM_SUCCESS; }
int pam_get_user(pam_handle_t *pamh, const char **user, const char *prompt) {
    (void) pamh; (void) prompt;
    if (user) *user = NULL;
    return PAM_SUCCESS;
}
int pam_getenv(pam_handle_t *pamh, const char *name) { (void) pamh; (void) name; return 0; }
int pam_putenv(pam_handle_t *pamh, const char *name_value) { (void) pamh; (void) name_value; return PAM_SUCCESS; }
int pam_syslog(const pam_handle_t *pamh, int priority, const char *format, ...) {
    (void) pamh; (void) priority; (void) format;
    return 0;
}
int pam_error(const pam_handle_t *pamh, const char *format, ...) {
    (void) pamh; (void) format;
    return 0;
}
int pam_info(const pam_handle_t *pamh, const char *format, ...) {
    (void) pamh; (void) format;
    return 0;
}

/* ---- glibc passwd/shadow stream functions (files.c uses them) ---- */
#include <pwd.h>
#include <shadow.h>
struct passwd *fgetpwent(FILE *stream) { (void) stream; return NULL; }
struct spwd *fgetspent(FILE *stream) { (void) stream; return NULL; }

#include <pwd.h>
#include <shadow.h>
struct spwd *getspnam(const char *name) { (void) name; return NULL; }

#include <stddef.h>
void explicit_bzero(void *s, size_t n) {
    volatile char *p = (volatile char *)s;
    while (n--) *p++ = 0;
}

char *get_current_dir_name(void) { return NULL; }

#include <stdarg.h>
int sd_journal_printv_with_location(int priority, const char *file,
                                    int line, const char *func,
                                    const char *format, va_list ap) {
    (void) priority; (void) file; (void) line; (void) func;
    (void) format; (void) ap;
    return 0;
}
int sd_journal_print_with_location(int priority, const char *file,
                                   int line, const char *func,
                                   const char *format, ...) {
    (void) priority; (void) file; (void) line; (void) func; (void) format;
    return 0;
}

#include <stdio.h>
int putpwent(const struct passwd *p, FILE *stream) {
    (void) p; (void) stream;
    return 0;
}

const char *pam_modutil_getlogin(pam_handle_t *pamh) { (void) pamh; return NULL; }

#include <stdarg.h>
int pam_prompt(const pam_handle_t *pamh, int style, char **response,
               const char *fmt, ...) {
    (void) pamh; (void) style; (void) response; (void) fmt;
    return PAM_SUCCESS;
}
int pam_vprompt(const pam_handle_t *pamh, int style, char **response,
                const char *fmt, va_list args) {
    (void) pamh; (void) style; (void) response; (void) fmt; (void) args;
    return PAM_SUCCESS;
}
