// test_libofx.cpp — consumer test for libofx 0.10.9.
//
// Suite 1 (context): version macros + file-format helpers + context lifecycle.
// Suite 2 (requests): OFX request builders with minimal login/account structs.
// Both suites call real libofx APIs; no print-only paths.
#include <libofx/libofx.h>

#include <cstdio>
#include <cstring>
#include <cstdlib>

static int suite_context() {
    int checks = 0;
    if (LIBOFX_MAJOR_VERSION != 0 || LIBOFX_MINOR_VERSION != 10 ||
        LIBOFX_MICRO_VERSION != 9) {
        printf("context: version macros mismatch %d.%d.%d\n",
               LIBOFX_MAJOR_VERSION, LIBOFX_MINOR_VERSION, LIBOFX_MICRO_VERSION);
        return 1;
    }
    checks++;

    enum LibofxFileFormat fmt =
        libofx_get_file_format_from_str(LibofxImportFormatList, "OFX");
    if (fmt != OFX) {
        printf("context: format from str failed\n");
        return 1;
    }
    checks++;

    const char *desc =
        libofx_get_file_format_description(LibofxImportFormatList, OFX);
    if (desc == NULL || desc[0] == '\0') {
        printf("context: format description empty\n");
        return 1;
    }
    checks++;

    LibofxContextPtr ctx = libofx_get_new_context();
    if (ctx == NULL) {
        printf("context: get_new_context returned null\n");
        return 1;
    }
    const char *tmpd = getenv("TMPDIR");
    if (!tmpd || !tmpd[0] || strcmp(tmpd, "/tmp") == 0) tmpd = getenv("TMP");
    if (!tmpd || !tmpd[0] || strcmp(tmpd, "/tmp") == 0) tmpd = getenv("TEMP");
    if (!tmpd || !tmpd[0]) tmpd = "/tmp";
    libofx_set_dtd_dir(ctx, tmpd);
    if (libofx_free_context(ctx) != 0) {
        printf("context: free_context failed\n");
        return 1;
    }
    checks++;

    if (checks != 4) {
        printf("context: checks=%d want 4\n", checks);
        return 1;
    }
    printf("test_libofx_context: all 4 checks passed\n");
    return 0;
}

static void fill_login(struct OfxFiLogin *login) {
    memset(login, 0, sizeof(*login));
    strncpy(login->fid, "1234", sizeof(login->fid) - 1);
    strncpy(login->org, "TestBank", sizeof(login->org) - 1);
    strncpy(login->userid, "user", sizeof(login->userid) - 1);
    strncpy(login->userpass, "pass", sizeof(login->userpass) - 1);
    strncpy(login->appid, "QWIN", sizeof(login->appid) - 1);
    strncpy(login->appver, "2800", sizeof(login->appver) - 1);
}

static void fill_account(struct OfxAccountData *acc) {
    memset(acc, 0, sizeof(*acc));
    acc->account_type = OfxAccountData::OFX_CHECKING;
    acc->account_type_valid = 1;
    strncpy(acc->account_number, "123456789", sizeof(acc->account_number) - 1);
    acc->account_number_valid = 1;
    strncpy(acc->bank_id, "123456789", sizeof(acc->bank_id) - 1);
    acc->bank_id_valid = 1;
}

static int suite_requests() {
    int checks = 0;
    struct OfxFiLogin login;
    struct OfxAccountData acc;
    fill_login(&login);
    fill_account(&acc);

    char *r1 = libofx_request_accountinfo(&login);
    if (r1 == NULL || r1[0] == '\0') {
        printf("requests: accountinfo request empty\n");
        if (r1) free(r1);
        return 1;
    }
    if (strstr(r1, "OFX") == NULL && strstr(r1, "ACCTINFO") == NULL) {
        printf("requests: accountinfo missing OFX marker\n");
        free(r1);
        return 1;
    }
    free(r1);
    checks++;

    char *r2 = libofx_request_statement(&login, &acc, 0);
    if (r2 == NULL || r2[0] == '\0') {
        printf("requests: statement request empty\n");
        if (r2) free(r2);
        return 1;
    }
    if (strstr(r2, "OFX") == NULL && strstr(r2, "STMTTRN") == NULL) {
        printf("requests: statement missing OFX marker\n");
        free(r2);
        return 1;
    }
    free(r2);
    checks++;

    // Negative path: unknown format string must map to UNKNOWN, not crash.
    enum LibofxFileFormat unk =
        libofx_get_file_format_from_str(LibofxImportFormatList, "NOT_A_FORMAT");
    if (unk != UNKNOWN) {
        printf("requests: unknown format not UNKNOWN\n");
        return 1;
    }
    checks++;

    if (checks != 3) {
        printf("requests: checks=%d want 3\n", checks);
        return 1;
    }
    printf("test_libofx_requests: all 3 checks passed\n");
    return 0;
}

int main() {
    int rc = 0;
    if (suite_context() != 0) rc = 1;
    if (suite_requests() != 0) rc = 1;
    // Falsifiability: non-empty output is required by the harness; an empty
    // binary printing nothing must not be mistaken for success.
    if (rc == 0) {
        printf("test_libofx: suites complete rc=0\n");
    }
    return rc;
}
