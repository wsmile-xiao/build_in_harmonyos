/*
 * Consumer test for termrec/0.19.
 *
 * Links the installed libtty and exercises the public ttyrec writer/reader
 * API: format registry queries, the vt terminal object lifecycle, and a real
 * record → load → frame-iteration round trip with data and timestamp
 * assertions. Exit code: 0 = all checks passed, 1 = at least one failed.
 *
 * Ownership note: ttyrec_load() hands the passed vt to the timeline, and
 * ttyrec_free() releases it (tr->tev_vt) — freeing it again would be a
 * double free.
 */
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <unistd.h>

#include <libtty/tty.h>
#include <libtty/ttyrec.h>

static int failures = 0;

#define CHECK(cond, what) do {                  \
    if (!(cond)) {                              \
        ++failures;                             \
        printf("FAIL: %s\n", (what));           \
    }                                           \
} while (0)

static int report(void)
{
    if (failures == 0) {
        printf("ALL CHECKS PASSED\n");
        return 0;
    }
    printf("%d CHECK(S) FAILED\n", failures);
    return 1;
}

int main(void)
{
    /* 1) Built-in writer format registry is populated. */
    CHECK(ttyrec_w_get_format_name(0) != NULL, "writer format 0 has a name");
    CHECK(ttyrec_w_get_format_name(9999) == NULL, "unknown format index is NULL");
    CHECK(ttyrec_w_get_format_ext("ttyrec") != NULL,
          "ttyrec format declares an extension");
    CHECK(ttyrec_w_find_format(NULL, "probe.ttyrec", "ansi") != NULL,
          "format lookup by filename succeeds");

    /* 2) vt terminal object lifecycle. */
    tty vt = tty_init(80, 24, 0);
    CHECK(vt != NULL, "tty_init(80x24)");
    if (vt) {
        tty_write(vt, "hello", 5);
        tty_reset(vt);
        tty_resize(vt, 100, 30);
        tty_free(vt);
    }

    /* 3) Record two frames, then load them back through the public API. */
    const char *path = "consumer_roundtrip.ttyrec";
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    CHECK(fd >= 0, "create ttyrec file");
    if (fd < 0)
        return report();

    struct timeval ts = {1, 0};
    recorder w = ttyrec_w_open(fd, NULL, path, &ts);
    CHECK(w != NULL, "ttyrec_w_open");
    if (!w) {
        close(fd);
        return report();
    }
    {
        struct timeval t1 = {1, 500000};
        struct timeval t2 = {2, 0};
        CHECK(ttyrec_w_write(w, &t1, "hello ", 6) == 1, "frame 1 recorded");
        CHECK(ttyrec_w_write(w, &t2, "world!", 6) == 1, "frame 2 recorded");
        CHECK(ttyrec_w_close(w) == 1, "ttyrec_w_close");
    }

    int rfd = open(path, O_RDONLY);
    CHECK(rfd >= 0, "reopen ttyrec file");
    if (rfd < 0)
        return report();

    tty rvt = tty_init(80, 24, 0);
    ttyrec tr = ttyrec_load(rfd, NULL, path, rvt);
    CHECK(tr != NULL, "ttyrec_load");
    if (tr) {
        int seen_hello = 0, seen_world = 0;
        ttyrec_frame fr;
        for (fr = ttyrec_seek(tr, NULL, NULL); fr != NULL;
             fr = ttyrec_next_frame(tr, fr)) {
            if (fr->len == 6 && memcmp(fr->data, "hello ", 6) == 0)
                seen_hello = 1;
            if (fr->len == 6 && memcmp(fr->data, "world!", 6) == 0) {
                seen_world = 1;
                CHECK(fr->t.tv_sec == 2 && fr->t.tv_usec == 0,
                      "frame 2 timestamp round-trips");
            }
        }
        CHECK(seen_hello, "frame 1 data round-trips");
        CHECK(seen_world, "frame 2 data round-trips");
        ttyrec_free(tr);   /* also releases rvt (the timeline owns it) */
    } else if (rvt) {
        tty_free(rvt);
    }
    close(rfd);
    unlink(path);
    return report();
}
