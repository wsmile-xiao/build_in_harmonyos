/*
 * sysrepo test_package: exercises the public core API of the consumed package.
 *
 * Every call below is a real symbol from libsysrepo; the assertions check
 * returned values, so the test fails if the library is missing, stubbed out,
 * or if the connection/datastore machinery cannot run on this platform.
 */
#include <stdio.h>
#include <string.h>

#include <libyang/libyang.h>
#include <sysrepo.h>

int
main(void)
{
    sr_conn_ctx_t *conn = NULL;
    sr_session_ctx_t *session = NULL;
    const char *msg;
    int rc;

    /* surface internal sysrepo errors in the ctest log */
    sr_log_stderr(SR_LL_DBG);

    /* 1) error-code to text mapping, no I/O */
    msg = sr_strerror(SR_ERR_OK);
    if ((msg == NULL) || (strlen(msg) == 0)) {
        fprintf(stderr, "FAIL: sr_strerror(SR_ERR_OK) returned no text\n");
        return 1;
    }
    printf("sr_strerror(SR_ERR_OK) = %s\n", msg);

    msg = sr_strerror(SR_ERR_NOT_FOUND);
    if ((msg == NULL) || (strlen(msg) == 0)) {
        fprintf(stderr, "FAIL: sr_strerror(SR_ERR_NOT_FOUND) returned no text\n");
        return 1;
    }
    printf("sr_strerror(SR_ERR_NOT_FOUND) = %s\n", msg);

    /* 2) connect to the datastore: creates/attaches SHM segment + repo access */
    rc = sr_connect(SR_CONN_DEFAULT, &conn);
    if (rc != SR_ERR_OK) {
        fprintf(stderr, "FAIL: sr_connect returned %d (%s)\n", rc, sr_strerror(rc));
        return 1;
    }
    if (conn == NULL) {
        fprintf(stderr, "FAIL: sr_connect reported OK but left conn NULL\n");
        return 1;
    }
    printf("sr_connect OK\n");

    /* 3) open a session against the running datastore */
    rc = sr_session_start(conn, SR_DS_RUNNING, &session);
    if (rc != SR_ERR_OK) {
        fprintf(stderr, "FAIL: sr_session_start returned %d (%s)\n", rc, sr_strerror(rc));
        sr_disconnect(conn);
        return 1;
    }
    if (session == NULL) {
        fprintf(stderr, "FAIL: sr_session_start reported OK but left session NULL\n");
        sr_disconnect(conn);
        return 1;
    }
    printf("sr_session_start OK\n");

    /* 4) tear the session down and detach from the datastore */
    rc = sr_session_stop(session);
    if (rc != SR_ERR_OK) {
        fprintf(stderr, "FAIL: sr_session_stop returned %d (%s)\n", rc, sr_strerror(rc));
        sr_disconnect(conn);
        return 1;
    }

    rc = sr_disconnect(conn);
    if (rc != SR_ERR_OK) {
        fprintf(stderr, "FAIL: sr_disconnect returned %d (%s)\n", rc, sr_strerror(rc));
        return 1;
    }
    printf("PASS: sysrepo core connect/session/read path usable\n");
    return 0;
}
