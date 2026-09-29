/*
 * libradsec 0.0.5 — test_package consumer test (R34 compliant).
 *
 * Exercises libradsec's real public API locally (no network/server needed):
 *   * context creation
 *   * load a realm configuration file (rs_context_read_config) — this is the
 *     upstream-blessed connection setup mode (examples/client-blocking.c is
 *     built with -DUSE_CONFIG_FILE). A realm loaded from config allocates and
 *     fills conn->realm and conn->peers; the manual mode
 *     (rs_conn_create(..., NULL) + rs_conn_set_type) is NOT usable because it
 *     leaves conn->realm == NULL and rs_conn_set_type()/rs_peer_set_timeout()
 *     unconditionally dereference it -> SEGV on a NDEBUG build.
 *   * connection bound to the UDP realm from config
 *   * RADIUS Access-Request packet construction
 *   * packet code, and User-Name / User-Password AVP handling.
 *
 * Usage: test_libradsec <config-file>
 *
 * Emits the HMBS_TEST_PACKAGE_RESULT JSON marker with the real executed
 * and passed counts.
 */
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <radsec/radsec.h>
#include <radsec/request.h>
#include <radsec/radius.h>  /* PW_USER_NAME (radsec.h/request.h do not include radius.h) */

#define TOTAL_CHECKS 7

static int g_checks = 0;
static int g_passed = 0;

static void check(const char *name, int cond)
{
    g_checks++;
    if (cond) {
        g_passed++;
        printf("PASS: %s\n", name);
    } else {
        printf("FAIL: %s\n", name);
    }
}

int main(int argc, char **argv)
{
    struct rs_context *ctx = NULL;
    struct rs_connection *conn = NULL;
    struct rs_packet *msg = NULL;
    rs_const_avp *vp = NULL;
    const char *config_file = (argc > 1) ? argv[1] : "test.conf";

    /* 1. context */
    check("rs_context_create", rs_context_create(&ctx) == 0 && ctx != NULL);

    /* 2. load the realm configuration (defines the blocking-udp UDP realm
     *    and its peer with secret/timeout/retries). */
    check("rs_context_read_config",
          ctx && rs_context_read_config(ctx, config_file) == 0);

    /* 3. connection bound to the UDP realm loaded from config; this populates
     *    conn->realm (type=UDP, timeout, retries) and conn->peers so no
     *    NULL-realm deref occurs later. */
    check("rs_conn_create",
          ctx && rs_conn_create(ctx, &conn, "blocking-udp") == 0 && conn != NULL);

    /* 4. build a RADIUS Access-Request packet with User-Name / User-Password */
    check("rs_packet_create_authn_request",
          conn && rs_packet_create_authn_request(conn, &msg, "testuser", "testpass") == 0
          && msg != NULL);

    /* 5. packet code must be PW_ACCESS_REQUEST (1) */
    check("rs_packet_code", msg && rs_packet_code(msg) == PW_ACCESS_REQUEST);

    /* 6. User-Name AVP present and correct (dictionary-driven).
     *    NOTE: use rs_packet_avps() + rs_avp_find_const() instead of the
     *    declared-but-not-exported rs_packet_find_avp(): libradsec links with
     *    `-export-symbols radsec.sym`, and rs_packet_find_avp is NOT in that
     *    list, so it is absent from the exported shared-library symbol table
     *    (undefined symbol at consumer link time). rs_packet_avps and
     *    rs_avp_find_const ARE exported. */
    {
        rs_avp **avps = NULL;
        rs_packet_avps(msg, &avps);
        vp = avps ? rs_avp_find_const(*avps, PW_USER_NAME, 0) : NULL;
    }
    check("rs_avp_find_const(User-Name)",
          vp != NULL && strcmp(rs_avp_string_value(vp), "testuser") == 0);

    /* 7. User-Password AVP present and correct */
    {
        rs_avp **avps = NULL;
        rs_packet_avps(msg, &avps);
        vp = avps ? rs_avp_find_const(*avps, PW_USER_PASSWORD, 0) : NULL;
    }
    check("rs_avp_find_const(User-Password)",
          vp != NULL && strcmp(rs_avp_string_value(vp), "testpass") == 0);

    /* cleanup */
    if (msg) rs_packet_destroy(msg);
    if (conn) rs_conn_destroy(conn);
    if (ctx) rs_context_destroy(ctx);

    printf("\nlibradsec test summary: %d/%d checks passed\n", g_passed, g_checks);
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,"
           "\"command\":\"./test_libradsec\",\"discovered\":%d,\"passedCount\":%d}\n",
           g_passed == g_checks ? "true" : "false", TOTAL_CHECKS, g_passed);

    return g_passed == g_checks ? 0 : 1;
}
