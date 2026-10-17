/* Offline consumer test for libmpd 11.8.17 (no server, no network).
 * Exercises only local MpdObj lifecycle APIs: each numbered stage prints
 * exactly one CHECK-OK line on success, any failure prints CHECK-FAIL and
 * exits nonzero. Total: 8 CHECK-OK lines.
 */
#include <stdio.h>
#include <string.h>
#include <libmpd/libmpd.h>

#define CHECK(n, cond) do { \
    if (!(cond)) { printf("CHECK-FAIL: %d\n", (n)); return 1; } \
    printf("CHECK-OK: %d\n", (n)); \
} while (0)

static void on_status(MpdObj *mi, ChangedStatusType what, void *ud)
{
    (void)mi; (void)what; (void)ud;
}

static int on_error(MpdObj *mi, int id, char *msg, void *ud)
{
    (void)mi; (void)id; (void)msg; (void)ud;
    return 0;
}

static void on_conn(MpdObj *mi, int conn, void *ud)
{
    (void)mi; (void)conn; (void)ud;
}

int main(void)
{
    MpdObj *d = mpd_new_default();
    CHECK(1, d != NULL);
    CHECK(2, d && mpd_get_hostname(d) && strcmp(mpd_get_hostname(d), "localhost") == 0);
    mpd_free(d);

    MpdObj *m = mpd_new("example.com", 6601, NULL);
    CHECK(3, m != NULL);
    CHECK(4, mpd_get_hostname(m) && strcmp(mpd_get_hostname(m), "example.com") == 0);
    CHECK(5, mpd_set_hostname(m, "127.0.0.1") == MPD_OK
        && strcmp(mpd_get_hostname(m), "127.0.0.1") == 0);
    CHECK(6, mpd_set_port(m, 6600) == MPD_OK
        && mpd_set_password(m, "secret") == MPD_OK
        && mpd_set_connection_timeout(m, 5.0f) == MPD_OK);
    /* No server: must report disconnected without crashing. */
    CHECK(7, mpd_check_connected(m) == FALSE);
    /* Pure/local helpers: signal connectors + tag lookup need no server. */
    mpd_signal_connect_status_changed(m, on_status, NULL);
    mpd_signal_connect_error(m, on_error, NULL);
    mpd_signal_connect_connection_changed(m, on_conn, NULL);
    CHECK(8, mpd_misc_get_tag_by_name((char *)"Artist") >= 0);
    mpd_free(m);
    return 0;
}
