#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <security/pam_appl.h>
#include <security/pam_misc.h>

#ifndef LINUX_PAM_TEST_MODULE
#error "LINUX_PAM_TEST_MODULE is not defined"
#endif

static int quiet_conv(int num_msg,
                      const struct pam_message **msg,
                      struct pam_response **resp,
                      void *appdata_ptr)
{
    (void)num_msg;
    (void)msg;
    (void)appdata_ptr;

    if (num_msg < 0 || resp == NULL) {
        return PAM_CONV_ERR;
    }

    *resp = NULL;
    if (num_msg == 0) {
        return PAM_SUCCESS;
    }

    *resp = calloc((size_t)num_msg, sizeof(**resp));
    if (*resp == NULL) {
        return PAM_BUF_ERR;
    }

    return PAM_SUCCESS;
}

static int write_text_file(const char *path, const char *content)
{
    FILE *fp = fopen(path, "w");
    if (fp == NULL) {
        fprintf(stderr, "open %s failed: %s\n", path, strerror(errno));
        return 1;
    }
    if (fputs(content, fp) < 0) {
        fprintf(stderr, "write %s failed: %s\n", path, strerror(errno));
        fclose(fp);
        return 1;
    }
    if (fclose(fp) != 0) {
        fprintf(stderr, "close %s failed: %s\n", path, strerror(errno));
        return 1;
    }
    return 0;
}

int main(void)
{
    const char *confdir = getenv("LINUX_PAM_TEST_CONFDIR");
    char service_path[1024];
    char service_content[2048];
    struct pam_conv conv = { quiet_conv, NULL };
    pam_handle_t *pamh = NULL;
    const char *value;
    int rc;
    int written;

    if (confdir == NULL || confdir[0] == '\0') {
        fprintf(stderr, "LINUX_PAM_TEST_CONFDIR must be set\n");
        return 1;
    }

    written = snprintf(service_path, sizeof(service_path), "%s/permit", confdir);
    if (written < 0 || (size_t)written >= sizeof(service_path)) {
        fprintf(stderr, "service path too long for %s\n", confdir);
        return 1;
    }
    written = snprintf(service_content,
                       sizeof(service_content),
                       "auth required %s\naccount required %s\nsession required %s\n",
                       LINUX_PAM_TEST_MODULE,
                       LINUX_PAM_TEST_MODULE,
                       LINUX_PAM_TEST_MODULE);
    if (written < 0 || (size_t)written >= sizeof(service_content)) {
        fprintf(stderr, "service content too long for %s\n", LINUX_PAM_TEST_MODULE);
        return 1;
    }
    if (write_text_file(service_path, service_content) != 0) {
        return 1;
    }

    rc = pam_start_confdir("permit", "ohos-user", &conv, confdir, &pamh);
    if (rc != PAM_SUCCESS) {
        fprintf(stderr, "pam_start_confdir failed: %d\n", rc);
        return 1;
    }

    rc = pam_authenticate(pamh, 0);
    if (rc != PAM_SUCCESS) {
        fprintf(stderr, "pam_authenticate failed: %d\n", rc);
        pam_end(pamh, rc);
        return 1;
    }

    rc = pam_acct_mgmt(pamh, 0);
    if (rc != PAM_SUCCESS) {
        fprintf(stderr, "pam_acct_mgmt failed: %d\n", rc);
        pam_end(pamh, rc);
        return 1;
    }

    rc = pam_misc_setenv(pamh, "LINUX_PAM_TEST", "ok", 0);
    if (rc != PAM_SUCCESS) {
        fprintf(stderr, "pam_misc_setenv failed: %d\n", rc);
        pam_end(pamh, rc);
        return 1;
    }

    value = pam_getenv(pamh, "LINUX_PAM_TEST");
    if (value == NULL || strcmp(value, "ok") != 0) {
        fprintf(stderr, "pam_getenv mismatch\n");
        pam_end(pamh, PAM_SYSTEM_ERR);
        return 1;
    }

    rc = pam_end(pamh, PAM_SUCCESS);
    if (rc != PAM_SUCCESS) {
        fprintf(stderr, "pam_end failed: %d\n", rc);
        return 1;
    }

    puts("linux-pam pam_permit and pam_misc smoke test passed");
    return 0;
}
