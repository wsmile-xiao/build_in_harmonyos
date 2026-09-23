/* cyrus-sasl-gs2 test_package — GS2 mechanism consumer checks.
 *
 * Proves, against the packaged libsasl2 with the GS2/GSSAPI plugin
 * modules (plugins/*.so, discovered via sasl_set_path/SASL_PATH):
 *  1. library version is 2.1.x (matches upstream 2.1.28 source)
 *  2. sasl_client_init succeeds
 *  3. sasl_client_new creates a connection
 *  4. sasl_listmech enumerates mechanisms
 *  5. GS2 is among the available mechanisms (purpose of this package;
 *     concrete SASL names are GS2-KRB5 etc. derived from the GSS mechs,
 *     so match the "GS2-" prefix rather than an exact token)
 *  6. GSSAPI is available too (gs2.c and gssapi.c come from the same
 *     SASL_GSSAPI_CHK detection; proves the GSS linkage, not stubbed)
 *
 * Each passing check prints one "CHECK-OK: <name>" line; the test_package
 * conanfile counts those lines for the HMBS_TEST_PACKAGE_RESULT marker.
 * Exit code is 0 only if all 6 checks pass (exit-0-alone is not proof).
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
    const char *mechlist = NULL;
    unsigned mechlen = 0;
    int count = 0;
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

#ifdef SASL_PLUGIN_DIR
    /* The library's compiled-in plugin path (//lib/sasl2 from
     * prefix=/) does not exist after Conan relocation; pin the
     * package plugin dir so GS2 discovery never depends on the
     * ambient SASL_PATH alone (cyrus-sasl/2.1.28 precedent). */
    if (sasl_set_path(SASL_PATH_TYPE_PLUGIN, (char *)SASL_PLUGIN_DIR) != SASL_OK) {
        fprintf(stderr, "FAIL: sasl_set_path(%s) failed\n", SASL_PLUGIN_DIR);
        return 1;
    }
    printf("plugin dir = %s\n", SASL_PLUGIN_DIR);
#endif

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

    if (!mechlist || !strstr(mechlist, "GS2-")) {
        fprintf(stderr, "FAIL: GS2 mechanism not available (want GS2-*)\n");
        sasl_dispose(&conn);
        return 1;
    }
    printf("CHECK-OK: gs2-available\n");

    if (!strstr(mechlist, "GSSAPI")) {
        fprintf(stderr, "FAIL: GSSAPI mechanism not available\n");
        sasl_dispose(&conn);
        return 1;
    }
    printf("CHECK-OK: gssapi-available\n");

    sasl_dispose(&conn);
    sasl_client_done();
    printf("cyrus-sasl-gs2 consumer test PASS (6/6)\n");
    return 0;
}
