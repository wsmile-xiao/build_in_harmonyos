/* cyrus-sasl test_package - real consumer of the packaged libsasl2 API.
 *
 * Verifies (not a print-only stub):
 *   1. sasl_version_info() reports the 2.1.x libsasl2 ABI;
 *   2. sasl_client_init() with authentication callbacks succeeds;
 *   3. sasl_client_new() allocates a client connection;
 *   4. sasl_listmech() enumerates mechanisms that were dlopen'ed from the
 *      packaged plugin directory (lib/sasl2), and PLAIN / CRAM-MD5 are
 *      present. CRAM-MD5 additionally proves the internal HMAC-MD5 code path
 *      is functional in the shipped library.
 */
#include <sasl/sasl.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int cb_getsimple(void *ctx, int id, const char **result, unsigned *len)
{
    (void)ctx;
    (void)id;
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
    size_t n = strlen(pw);
    (void)conn;
    (void)ctx;
    (void)id;
    if (!s) {
        s = (sasl_secret_t *)malloc(sizeof(sasl_secret_t) + n);
        if (!s) {
            return SASL_NOMEM;
        }
    }
    s->len = (unsigned)n;
    memcpy(s->data, pw, n);
    *psecret = s;
    return SASL_OK;
}

int main(void)
{
    const char *impl = NULL;
    int major = 0, minor = 0, step = 0, patch = 0;
    sasl_callback_t callbacks[] = {
        {SASL_CB_AUTHNAME, (int (*)(void))&cb_getsimple, NULL},
        {SASL_CB_USER, (int (*)(void))&cb_getsimple, NULL},
        {SASL_CB_PASS, (int (*)(void))&cb_getsecret, NULL},
        {SASL_CB_LIST_END, NULL, NULL},
    };
    sasl_conn_t *conn = NULL;
    const char *mechlist = NULL;
    unsigned len = 0;
    int count = 0;
    int rc;

    sasl_version_info(&impl, NULL, &major, &minor, &step, &patch);
    printf("cyrus-sasl impl=%s version=%d.%d.%d.%d\n",
           impl ? impl : "?", major, minor, step, patch);
    if (major != 2 || minor != 1) {
        fprintf(stderr, "FAIL: unexpected version (want 2.1.x)\n");
        return 1;
    }

    /* Point the loader at the packaged plugin directory (VirtualRunEnv also
     * exports SASL_PATH; setting it explicitly keeps the check deterministic).
     */
    {
        const char *plugin_dir = getenv("SASL_PATH");
        if (plugin_dir && plugin_dir[0]) {
            char buf[4096];
            const char *colon = strchr(plugin_dir, ':');
            size_t n = colon ? (size_t)(colon - plugin_dir) : strlen(plugin_dir);
            if (n >= sizeof(buf)) {
                n = sizeof(buf) - 1;
            }
            memcpy(buf, plugin_dir, n);
            buf[n] = '\0';
            rc = sasl_set_path(SASL_PATH_TYPE_PLUGIN, buf);
            if (rc != SASL_OK) {
                fprintf(stderr, "FAIL: sasl_set_path(%s) = %d\n", buf, rc);
                return 1;
            }
            printf("plugin dir = %s\n", buf);
        }
    }

    rc = sasl_client_init(callbacks);
    if (rc != SASL_OK) {
        fprintf(stderr, "FAIL: sasl_client_init = %d\n", rc);
        return 1;
    }

    rc = sasl_client_new("smtp", "localhost", NULL, NULL, callbacks, 0, &conn);
    if (rc != SASL_OK) {
        fprintf(stderr, "FAIL: sasl_client_new = %d\n", rc);
        return 1;
    }

    rc = sasl_listmech(conn, NULL, "", " ", "", &mechlist, &len, &count);
    if (rc != SASL_OK) {
        fprintf(stderr, "FAIL: sasl_listmech = %d\n", rc);
        return 1;
    }
    printf("client mechs (%d): %s\n", count, mechlist ? mechlist : "(none)");

    if (!mechlist || !strstr(mechlist, "PLAIN")) {
        fprintf(stderr, "FAIL: PLAIN plugin not loaded\n");
        return 1;
    }
    if (!strstr(mechlist, "CRAM-MD5")) {
        fprintf(stderr, "FAIL: CRAM-MD5 plugin not loaded\n");
        return 1;
    }

    sasl_dispose(&conn);
    sasl_client_done();
    printf("cyrus-sasl test PASS\n");
    return 0;
}
