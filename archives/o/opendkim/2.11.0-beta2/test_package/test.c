/*
 * libopendkim 2.11.0-beta2 API smoke test (R34: real API usage).
 *
 * Exercises the core signing/verifying lifecycle of libopendkim:
 *   1. dkim_init()            — library constructor
 *   2. dkim_libfeature()      — query feature support (SHA256 is the
 *                                mandatory modern algorithm)
 *   3. dkim_options()         — set/get DKIM_OPTS_TIMEOUT
 *   4. dkim_sign()            — start an rsa-sha256 relaxed/relaxed
 *                                signature on a synthetic message
 *   5. dkim_header()/dkim_eoh()/dkim_body()/dkim_eom() — feed message
 *   6. dkim_getsighdr()       — extract the generated DKIM-Signature
 *   7. dkim_free()/dkim_close() — teardown
 * Links -lopendkim (static archive + headers from the conan package);
 * fails at compile/link time if the package is unusable and at runtime
 * if any API misbehaves.
 */
#include <stdio.h>
#include <string.h>
#include <assert.h>

#include <opendkim/dkim.h>

#define MAXHEADER 4096

/* 1024-bit RSA private key in PKCS#1 PEM, verbatim from the upstream
 * libopendkim/tests/t-testdata.h KEY constant (public test fixture). */
static const char *TESTKEY =
    "-----BEGIN RSA PRIVATE KEY-----\n"
    "MIICXQIBAAKBgQC4GUGr+d/6SFNzVLYpphnRd0QPGKz2uWnV65RAxa1Pw352Bqiz\n"
    "qiKOBjgYGzj8pJQSs8tOvv/2k6jpI809RnESqOFgF0gu3UJbNnu3+cd8k/kiQj+q\n"
    "4cKKRpAT92ccxc7svhCNgN1sBGmROYZuysG3Vu3Dyc079gSLtnSrgXb+gQIDAQAB\n"
    "AoGAemlI0opm1Kvs2T4VliH8/tvX5FXbBH8LEZQAUwVeFTB/UQlieXyCV39pIxZO\n"
    "0Sa50qm8YNL9rb5HTSZiHQFOwyAKNqS4m/7JCsbuH4gQkPgPF561BHNL9oKfYgJq\n"
    "9P4kEFfDTBoXKBMxwWtT7AKV8dYvCa3vYzPQ/1BnqQdw2zECQQDyscdgR9Ih59PQ\n"
    "b72ddibdsxS65uXS2vzYLe7SKl+4R5JgJzw0M6DTAnoYFf6JAsKGZM15PCC0E16t\n"
    "RRo47U9VAkEAwjEVrlQ0/8yPACbDggDJg/Zz/uRu1wK0zjqj4vKjleubaX4SEvj7\n"
    "r6xxZm9hC1pMJAC9y3bbkbgCRBjXfyY6fQJBANe5aq2MaZ41wTOPf45NjbKXEiAo\n"
    "SbUpboKCIbyyaa8V/2h0t7D3C0dE9l4efsguqdZoF7Rh2/f1F70QpYRgfJkCQQCH\n"
    "oRrAeGXP50JVW72fNgeJGH/pnghgOa6of0JpxwhENJuGMZxUDfxTtUA6yD3iXP3j\n"
    "A3WL/wbaHsfOYf9Y+g1NAkAGLhx67Ah+uBNK4Xvfz0YPGINX20m+CMsxAw7FOaNv\n"
    "IW2oWFfZCB4APkIis79Ql45AHpavwx5XodBMzZwJUvlL\n"
    "-----END RSA PRIVATE KEY-----\n";

static const char *HDR_FROM = "From: Murray S. Kucherawy <msk@sendmail.com>\r\n";
static const char *HDR_TO = "To: Sendmail Test Address <sa-test@sendmail.net>\r\n";
static const char *HDR_DATE = "Date: Thu, 05 May 2005 11:59:09 -0700\r\n";
static const char *HDR_SUBJ = "Subject: DKIM test message\r\n";
static const char *BODY00 = "Hello world.\r\n";
static const char *BODY01 = "Hello world again.\r\n";

int main(void)
{
    DKIM_LIB *lib;
    DKIM *dkim;
    DKIM_STAT status;
    dkim_sigkey_t key;
    unsigned char hdr[MAXHEADER + 1];
    size_t hlen;
    int fail = 0;
    unsigned int timeout;

    /* 1. dkim_init */
    lib = dkim_init(NULL, NULL);
    if (lib == NULL) {
        printf("FAIL: dkim_init returned NULL\n");
        return 1;
    }
    printf("PASS: dkim_init\n");

    /* 2. dkim_libfeature: SHA256 support is mandatory for modern DKIM */
    if (!dkim_libfeature(lib, DKIM_FEATURE_SHA256)) {
        printf("FAIL: DKIM_FEATURE_SHA256 not available\n");
        fail++;
    } else {
        printf("PASS: dkim_libfeature(DKIM_FEATURE_SHA256)\n");
    }

    /* 3. dkim_options get/set round-trip on the I/O timeout */
    timeout = 0;
    status = dkim_options(lib, DKIM_OP_GETOPT, DKIM_OPTS_TIMEOUT,
                          &timeout, sizeof timeout);
    if (status != DKIM_STAT_OK) {
        printf("FAIL: dkim_options GET timeout rc=%d\n", (int) status);
        fail++;
    } else {
        printf("PASS: dkim_options GET timeout=%u\n", timeout);
    }
    timeout = 10;
    status = dkim_options(lib, DKIM_OP_SETOPT, DKIM_OPTS_TIMEOUT,
                          &timeout, sizeof timeout);
    if (status != DKIM_STAT_OK) {
        printf("FAIL: dkim_options SET timeout rc=%d\n", (int) status);
        fail++;
    } else {
        printf("PASS: dkim_options SET timeout=10\n");
    }

    /* 4. dkim_sign: relaxed/relaxed rsa-sha256 */
    key = (dkim_sigkey_t) TESTKEY;
    dkim = dkim_sign(lib, (const unsigned char *) "test-package", NULL,
                     key,
                     (const unsigned char *) "test",
                     (const unsigned char *) "example.com",
                     DKIM_CANON_RELAXED, DKIM_CANON_RELAXED,
                     DKIM_SIGN_RSASHA256, -1L, &status);
    if (dkim == NULL || status != DKIM_STAT_OK) {
        printf("FAIL: dkim_sign rc=%d\n", (int) status);
        fail++;
    } else {
        printf("PASS: dkim_sign (relaxed/relaxed rsa-sha256)\n");
    }

    if (dkim != NULL) {
        /* 5. feed headers + body */
        status = dkim_header(dkim, (u_char *) HDR_FROM, strlen(HDR_FROM));
        status = dkim_header(dkim, (u_char *) HDR_TO, strlen(HDR_TO));
        status = dkim_header(dkim, (u_char *) HDR_DATE, strlen(HDR_DATE));
        status = dkim_header(dkim, (u_char *) HDR_SUBJ, strlen(HDR_SUBJ));
        if (status != DKIM_STAT_OK) { printf("FAIL: dkim_header\n"); fail++; }
        else { printf("PASS: dkim_header x4\n"); }

        status = dkim_eoh(dkim);
        if (status != DKIM_STAT_OK) { printf("FAIL: dkim_eoh rc=%d\n", (int) status); fail++; }
        else { printf("PASS: dkim_eoh\n"); }

        status = dkim_body(dkim, (u_char *) BODY00, strlen(BODY00));
        status = dkim_body(dkim, (u_char *) BODY01, strlen(BODY01));
        if (status != DKIM_STAT_OK) { printf("FAIL: dkim_body\n"); fail++; }
        else { printf("PASS: dkim_body x2\n"); }

        status = dkim_eom(dkim, NULL);
        if (status != DKIM_STAT_OK) { printf("FAIL: dkim_eom rc=%d\n", (int) status); fail++; }
        else { printf("PASS: dkim_eom\n"); }

        /* 6. dkim_getsighdr: the generated DKIM-Signature header */
        memset(hdr, '\0', sizeof hdr);
        hlen = sizeof hdr;
        status = dkim_getsighdr(dkim, hdr, hlen,
                                strlen(DKIM_SIGNHEADER) + 2);
        if (status != DKIM_STAT_OK || hdr[0] == '\0') {
            printf("FAIL: dkim_getsighdr rc=%d\n", (int) status);
            fail++;
        } else {
            printf("PASS: dkim_getsighdr (%zu bytes, starts \"%.16s...\")\n",
                   strlen((char *) hdr), hdr);
        }

        /* 7. teardown */
        status = dkim_free(dkim);
        if (status != DKIM_STAT_OK) { printf("FAIL: dkim_free\n"); fail++; }
        else { printf("PASS: dkim_free\n"); }
    }

    /* dkim_close returns void — calling it completes the lifecycle */
    dkim_close(lib);
    printf("PASS: dkim_close\n");

    printf("=== %d failure(s) ===\n", fail);
    return fail ? 1 : 0;
}
