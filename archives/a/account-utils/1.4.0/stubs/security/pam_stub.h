/* Minimal stub of security/pam_appl.h + pam_misc.h for OHOS (no PAM).
 * SPDX-License-Identifier: BSD-3-Clause */
#ifndef PAM_STUB_H
#define PAM_STUB_H

#include <stddef.h>

typedef struct pam_handle pam_handle_t;

typedef struct pam_message {
    int msg_style;
    const char *msg;
} pam_message_t;

typedef struct pam_response {
    char *resp;
    int resp_retcode;
} pam_response_t;

typedef struct pam_conv {
    int (*conv)(int num_msg, const pam_message_t **msg,
                pam_response_t **resp, void *appdata_ptr);
    void *appdata_ptr;
} pam_conv_t;

#define PAM_SUCCESS 0
#define PAM_AUTH_ERR 1
#define PAM_SYSTEM_ERR 4
#define PAM_BUF_ERR 5
#define PAM_USER_UNKNOWN 10
#define PAM_CHANGE_EXPIRED_AUTHTOK 11

#define PAM_PROMPT_ECHO_OFF 1
#define PAM_PROMPT_ECHO_ON 2
#define PAM_ERROR_MSG 3
#define PAM_TEXT_INFO 4

int pam_start(const char *service_name, const char *user,
              const pam_conv_t *pam_conversation, pam_handle_t **pamh);
int pam_end(pam_handle_t *pamh, int pam_status);
const char *pam_strerror(pam_handle_t *pamh, int errnum);
int pam_get_item(const pam_handle_t *pamh, int item_type, const void **item);
int pam_set_item(pam_handle_t *pamh, int item_type, const void *item);
int pam_authenticate(pam_handle_t *pamh, int flags);
int pam_acct_mgmt(pam_handle_t *pamh, int flags);
int pam_open_session(pam_handle_t *pamh, int flags);
int pam_close_session(pam_handle_t *pamh, int flags);
int pam_chauthtok(pam_handle_t *pamh, int flags);
int pam_get_user(pam_handle_t *pamh, const char **user, const char *prompt);
int pam_getenv(pam_handle_t *pamh, const char *name);
int pam_putenv(pam_handle_t *pamh, const char *name_value);
int pam_syslog(const pam_handle_t *pamh, int priority, const char *format, ...);
int pam_error(const pam_handle_t *pamh, const char *format, ...);
int pam_info(const pam_handle_t *pamh, const char *format, ...);

#endif /* PAM_STUB_H */
