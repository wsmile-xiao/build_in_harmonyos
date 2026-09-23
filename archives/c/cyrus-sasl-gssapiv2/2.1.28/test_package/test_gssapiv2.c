/* cyrus-sasl-gssapiv2 test_package — GSSAPI mechanism consumer checks.
 *
 * Proves, against the packaged libsasl2 with GSSAPI support:
 *  1. library version is 2.1.x (matches upstream 2.1.28 source)
 *  2. sasl_client_init succeeds
 *  3. sasl_client_new creates a connection
 *  4. sasl_listmech enumerates client mechanisms
 *  5. GSSAPI is among the available client mechanisms (purpose of this package)
 *  6. sasl_server_init/new/listmech exposes GSSAPI server-side too
 *
 * Mechanism enumeration needs no KDC or credentials; actual GSSAPI
 * authentication (gss_init_sec_context) is out of scope for a consumer
 * test. Each passing check prints one "CHECK-OK: <name>" line; the
 * test_package conanfile counts those lines for the
 * HMBS_TEST_PACKAGE_RESULT marker. Exit code is 0 only if all 6 checks
 * pass (exit-0-alone is not proof).
 */
#include <sasl/sasl.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    const char *impl = NULL;
    const char *ver = NULL;
    int major = 0, minor = 0, step = 0, patch = 0;
    int r;
    sasl_conn_t *conn = NULL;
    sasl_conn_t *server = NULL;
    const char *mechlist = NULL;
    unsigned mechlen = 0;
    int count = 0;
    const char *server_mechs = NULL;
    unsigned server_mechlen = 0;
    int server_count = 0;

    sasl_version_info(&impl, &ver, &major, &minor, &step, &patch);
    printf("libsasl2 impl=%s version=%s (%d.%d.%d.%d)\n",
           impl ? impl : "?", ver ? ver : "?",
           major, minor, step, patch);
    if (major != 2 || minor != 1) {
        fprintf(stderr, "FAIL: unexpected version (want 2.1.x)\n");
        return 1;
    }
    printf("CHECK-OK: version-2.1\n");

    r = sasl_client_init(NULL);
    if (r != SASL_OK) {
        fprintf(stderr, "FAIL: sasl_client_init = %d\n", r);
        return 1;
    }
    printf("CHECK-OK: client-init\n");

    r = sasl_client_new("smtp", "localhost", NULL, NULL, NULL, 0, &conn);
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

    if (!mechlist || !strstr(mechlist, "GSSAPI")) {
        fprintf(stderr, "FAIL: GSSAPI mechanism not available\n");
        sasl_dispose(&conn);
        return 1;
    }
    printf("CHECK-OK: gssapi-available\n");

    r = sasl_server_init(NULL, "test_gssapiv2");
    if (r != SASL_OK) {
        fprintf(stderr, "FAIL: sasl_server_init = %d\n", r);
        sasl_dispose(&conn);
        return 1;
    }
    r = sasl_server_new("smtp", "localhost", NULL, NULL, NULL, NULL, 0, &server);
    if (r != SASL_OK || server == NULL) {
        fprintf(stderr, "FAIL: sasl_server_new = %d\n", r);
        sasl_dispose(&conn);
        sasl_server_done();
        return 1;
    }
    r = sasl_listmech(server, NULL, "", " ", "", &server_mechs,
                      &server_mechlen, &server_count);
    if (r != SASL_OK || !server_mechs || !strstr(server_mechs, "GSSAPI")) {
        fprintf(stderr, "FAIL: GSSAPI not in server mech list = %d (%s)\n",
                r, server_mechs ? server_mechs : "(none)");
        sasl_dispose(&conn);
        sasl_dispose(&server);
        sasl_server_done();
        return 1;
    }
    printf("server mechs (%d): %s\n", server_count, server_mechs);
    printf("CHECK-OK: server-gssapi-available\n");

    sasl_dispose(&conn);
    sasl_dispose(&server);
    sasl_client_done();
    sasl_server_done();
    printf("cyrus-sasl-gssapiv2 consumer test PASS (6/6)\n");
    return 0;
}
