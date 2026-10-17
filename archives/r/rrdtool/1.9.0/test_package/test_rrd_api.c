/*
 * z23-rrdtool 1.9.0 — librrd consumer test.
 *
 * R34: this links against the packaged librrd and calls real exported API
 * symbols end to end (create -> update -> inspect), not a print-only stub.
 * It is the proof that the shared library and its headers are usable by a
 * third-party consumer, independently of the CLI.
 *
 * Symbols exercised (all present in src/librrd.sym's export list):
 *   rrd_version, rrd_strversion, rrd_create_r, rrd_update_r, rrd_info_r
 */
#include <rrd.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static int checks = 0;
static int fails = 0;

#define CHECK(cond, label)                                                   \
    do {                                                                     \
        checks++;                                                            \
        if (cond) {                                                          \
            printf("PASS [%02d] %s\n", checks, label);                       \
        } else {                                                             \
            fails++;                                                         \
            printf("FAIL [%02d] %s\n", checks, label);                       \
        }                                                                    \
    } while (0)

int main(int argc, char **argv)
{
    const char  *work  = (argc > 1) ? argv[1] : ".";
    char         path[4096];
    char         update_buf[64];
    const char  *defs[2];
    const char  *upd[1];
    int          rc;
    double       ver;
    char        *sver;
    rrd_info_t  *info;
    rrd_info_t  *node;
    int          saw_step   = 0;
    int          saw_ds     = 0;
    int          saw_rra    = 0;

    snprintf(path, sizeof(path), "%s/libapi.rrd", work);
    remove(path);

    /* 1 — the library itself reports the version it was built with */
    ver  = rrd_version();
    sver = rrd_strversion();
    printf("librrd runtime version: double=%.2f string=%s\n", ver,
           sver ? sver : "(null)");
    CHECK(ver >= 1.9, "rrd_version() reports >= 1.9");
    CHECK(sver != NULL && strstr(sver, "1.9") != NULL,
          "rrd_strversion() reports the 1.9 line");

    /* 2 — create a real round-robin database through the API */
    defs[0] = "DS:temp:GAUGE:600:U:U";
    defs[1] = "RRA:AVERAGE:0.5:1:24";
    rc = rrd_create_r(path, 300, (time_t)1700000000, 2, defs);
    if (rc != 0) {
        fprintf(stderr, "rrd_create_r error: %s\n",
                rrd_get_error() ? rrd_get_error() : "(unknown)");
    }
    CHECK(rc == 0, "rrd_create_r() creates the RRD");

    {
        FILE *probe = fopen(path, "rb");
        long  size  = 0;
        if (probe != NULL) {
            fseek(probe, 0, SEEK_END);
            size = ftell(probe);
            fclose(probe);
        }
        CHECK(size > 0, "the API-created RRD exists on disk and is non-empty");
    }

    /* 3 — push a sample through the API */
    snprintf(update_buf, sizeof(update_buf), "%ld:41.5", (long)1700000300);
    upd[0] = update_buf;
    rc = rrd_update_r(path, NULL, 1, upd);
    if (rc != 0) {
        fprintf(stderr, "rrd_update_r error: %s\n",
                rrd_get_error() ? rrd_get_error() : "(unknown)");
    }
    CHECK(rc == 0, "rrd_update_r() stores a sample");

    /* 4 — read the header metadata back through the API */
    info = rrd_info_r(path);
    CHECK(info != NULL, "rrd_info_r() returns a metadata chain");

    for (node = info; node != NULL; node = node->next) {
        if (node->key == NULL) {
            continue;
        }
        /* rrdtool 1.9.0 renamed the info keys vs 1.8: the RRD step is
         * "step" (RD_I_CNT), and datasources are keyed by NAME
         * ("ds[temp].index", ...), not by index ("ds[0].*").  Measured on
         * device against the packaged library via an rrd_info_r dump. */
        if (strcmp(node->key, "step") == 0 &&
            node->type == RD_I_CNT && node->value.u_cnt == 300) {
            saw_step = 1;
        }
        if (strncmp(node->key, "ds[", 3) == 0
            && strstr(node->key, "].index") != NULL) {
            saw_ds = 1;
        }
        if (strncmp(node->key, "rra[0].", 7) == 0) {
            saw_rra = 1;
        }
    }
    CHECK(saw_step, "rrd_info_r() reports pdp_step == 300");
    CHECK(saw_ds, "rrd_info_r() enumerates the datasource");
    CHECK(saw_rra, "rrd_info_r() enumerates the RRA");

    printf("\n==== librrd API test: %d checks, %d failed ====\n", checks, fails);
    return fails == 0 ? 0 : 1;
}
