/* cyrus-sasl-ntlm test_package — NTLM mechanism consumer checks.
 *
 * Proves, against the packaged static libsasl2 with NTLM linked in and
 * OpenSSL provided by the conan dependency:
 *  1. library version is 2.1.x (matches upstream 2.1.28 source)
 *  2. sasl_client_init succeeds
 *  3. sasl_client_new creates a connection
 *  4. sasl_listmech enumerates mechanisms
 *  5. NTLM is among the available client mechanisms (purpose of this package)
 *  6. NTLM is among the available server mechanisms too (ntlm.c ships both
 *     sides; proves the static mechanism table carries the mechanism)
 *  7. OHOS-specific: with the plugin search path pinned to a directory that
 *     does not exist, NTLM must still be enumerated. This is the HarmonyOS
 *     adaptation invariant for this package: the library is built as a
 *     static libsasl2.a with STATIC_NTLM and --disable-staticdlopen, so no
 *     runtime dlopen / SASL_PATH plugin search (which HMDFS symlink rules
 *     and relocatable prefixes make unreliable) is needed at all.
 *
 * Each passing check prints one "CHECK-OK: <name>" line; the test_package
 * conanfile counts those lines for the HMBS_TEST_PACKAGE_RESULT marker.
 * Exit code is 0 only if all 7 checks pass (exit-0-alone is not proof).
 */
#include <sasl/sasl.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static int cb_getsimple(void *ctx, int id, const char **result, unsigned *len)
{
    (void) ctx;
    (void) id;
    *result = "testuser";
    if (len) {
        *len = 8;
    }
    return SASL_OK;
}

static int cb_getsecret(sasl_conn_t *conn, void *ctx, int id,
                        sasl_secret_t **psecret)
{
    static sasl_secret_t *s = NULL;
    const char *pw = "testpass";
    size_t n;
    (void) conn;
    (void) ctx;
    (void) id;
    n = strlen(pw);
    if (!s) {
        s = (sasl_secret_t *) malloc(sizeof(sasl_secret_t) + n);
        if (!s) {
            return SASL_NOMEM;
        }
    }
    s->len = (unsigned) n;
    memcpy(s->data, pw, n);
    *psecret = s;
    return SASL_OK;
}

int main(void)
{
    const char *impl = NULL;
    const char *ver = NULL;
    int major = 0, minor = 0, step = 0, patch = 0;
    int r;
    sasl_conn_t *conn = NULL;
    sasl_conn_t *sconn = NULL;
    const char *mechlist = NULL;
    const char *smechlist = NULL;
    unsigned mechlen = 0;
    unsigned smechlen = 0;
    int count = 0;
    int scount = 0;
    sasl_callback_t callbacks[] = {
        { SASL_CB_AUTHNAME, (int (*)(void)) &cb_getsimple, NULL },
        { SASL_CB_USER, (int (*)(void)) &cb_getsimple, NULL },
        { SASL_CB_PASS, (int (*)(void)) &cb_getsecret, NULL },
        { SASL_CB_LIST_END, NULL, NULL }
    };

    sasl_version_info(&impl, &ver, &major, &minor, &step, &patch);
    printf("libsasl2 impl=%s version=%s (%d.%d.%d.%d)\n",
           impl ? impl : "?", ver ? ver : "?",
           major, minor, step, patch);
    if (major != 2 || minor != 1) {
        fprintf(stderr, "FAIL: unexpected version (want 2.1.x)\n");
        return 1;
    }
    printf("CHECK-OK: version-2.1\n");

    /* OHOS adaptation precondition: point the plugin search path at a
     * directory that cannot exist, so any dlopen-only mechanism would
     * disappear. The package is static, so NTLM must survive it. */
    if (sasl_set_path(SASL_PATH_TYPE_PLUGIN,
                      (char *) "/nonexistent-ohos-sasl2-plugindir") != SASL_OK) {
        fprintf(stderr, "FAIL: sasl_set_path failed\n");
        return 1;
    }

    r = sasl_client_init(callbacks);
    if (r != SASL_OK) {
        fprintf(stderr, "FAIL: sasl_client_init = %d\n", r);
        return 1;
    }
    printf("CHECK-OK: client-init\n");

    r = sasl_client_new("smtp", "localhost", NULL, NULL, callbacks, 0, &conn);
    if (r != SASL_OK || conn == NULL) {
        fprintf(stderr, "FAIL: sasl_client_new = %d\n", r);
        return 1;
    }
    printf("CHECK-OK: client-new\n");

    r = sasl_listmech(conn, NULL, "", " ", "", &mechlist, &mechlen, &count);
    if (r != SASL_OK) {
        fprintf(stderr, "FAIL: sasl_listmech = %d\n", r);
        sasl_dispose(&conn);
        return 1;
    }
    printf("client mechs (%d): %s\n", count, mechlist ? mechlist : "(none)");
    printf("CHECK-OK: listmech\n");

    if (!mechlist || !strstr(mechlist, "NTLM")) {
        fprintf(stderr, "FAIL: NTLM mechanism not available (client)\n");
        sasl_dispose(&conn);
        return 1;
    }
    printf("CHECK-OK: ntlm-available\n");

    printf("CHECK-OK: ohos-static-mech-table\n");

    /* Server side: same mechanism table, server role. */
    r = sasl_server_init(NULL, "cyrus-sasl-ntlm-test");
    if (r != SASL_OK) {
        fprintf(stderr, "FAIL: sasl_server_init = %d\n", r);
        sasl_dispose(&conn);
        return 1;
    }
    r = sasl_server_new("smtp", "localhost", NULL, NULL, NULL, NULL, 0,
                        &sconn);
    if (r != SASL_OK || sconn == NULL) {
        fprintf(stderr, "FAIL: sasl_server_new = %d\n", r);
        sasl_dispose(&conn);
        return 1;
    }
    r = sasl_listmech(sconn, NULL, "", " ", "", &smechlist, &smechlen, &scount);
    if (r != SASL_OK) {
        fprintf(stderr, "FAIL: server sasl_listmech = %d\n", r);
        sasl_dispose(&sconn);
        sasl_dispose(&conn);
        return 1;
    }
    printf("server mechs (%d): %s\n", scount,
           smechlist ? smechlist : "(none)");
    if (!smechlist || !strstr(smechlist, "NTLM")) {
        fprintf(stderr, "FAIL: NTLM mechanism not available (server)\n");
        sasl_dispose(&sconn);
        sasl_dispose(&conn);
        return 1;
    }
    printf("CHECK-OK: ntlm-server-available\n");

    sasl_dispose(&sconn);
    sasl_dispose(&conn);
    sasl_client_done();
    sasl_server_done();
    printf("cyrus-sasl-ntlm consumer test PASS (7/7)\n");
    return 0;
}
