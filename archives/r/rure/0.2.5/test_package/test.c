/*
 * Consumer test for the installed rure C API.
 *
 * Two groups:
 *   - capi checks            : generic C-API behaviour (is_match/find/captures)
 *   - ohos checks            : HarmonyOS-specific platform contract
 *                              (aarch64-linux-ohos musl loader, worker-thread
 *                               usage, mmap'ed file-backed haystack)
 */
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include "rure.h"

static int g_capi_assertions = 0;
static int g_ohos_assertions = 0;

#define FAIL(...) do { fprintf(stderr, "FAIL: " __VA_ARGS__); fputc('\n', stderr); return 1; } while (0)

/* ───────────────────────── generic C-API checks ───────────────────────── */
static int run_capi_checks(void) {
    const char *haystack = "hello world";
    size_t len = strlen(haystack);

    rure *re = rure_compile_must("\\w+");
    g_capi_assertions++;
    if (!rure_is_match(re, (const uint8_t *)haystack, len, 0)) FAIL("rure_is_match");

    rure_match match = {0};
    g_capi_assertions++;
    if (!rure_find(re, (const uint8_t *)haystack, len, 0, &match)) FAIL("rure_find");
    g_capi_assertions++;
    if (match.start != 0 || match.end != 5) {
        FAIL("unexpected match range (%zu, %zu)", match.start, match.end);
    }

    rure *re2 = rure_compile_must("(\\w+)\\s+(\\w+)");
    rure_captures *caps = rure_captures_new(re2);
    g_capi_assertions++;
    if (!rure_find_captures(re2, (const uint8_t *)haystack, len, 0, caps)) {
        FAIL("rure_find_captures");
    }
    rure_match g1 = {0};
    rure_captures_at(caps, 1, &g1);
    g_capi_assertions++;
    if (g1.end - g1.start != 5) FAIL("unexpected capture group size");

    rure_captures_free(caps);
    rure_free(re2);
    rure_free(re);
    return 0;
}

/* ─────────────────────── HarmonyOS-specific checks ────────────────────── */
struct ohos_worker_arg { int ok; };

static void *ohos_worker(void *argp) {
    struct ohos_worker_arg *arg = (struct ohos_worker_arg *)argp;
    const char *text = "call 555-1234 now";
    rure *re = rure_compile_must("\\d{3}-\\d{4}");
    if (re == NULL) {
        arg->ok = 0;
        return NULL;
    }
    rure_match m = {0};
    if (rure_find(re, (const uint8_t *)text, strlen(text), 0, &m) &&
        m.end - m.start == 8 &&
        memcmp(text + m.start, "555-1234", 8) == 0) {
        arg->ok = 1;
    }
    rure_free(re);
    return NULL;
}

static int run_ohos_checks(void) {
    /* 1) Target is HarmonyOS: the OHOS/aarch64 musl dynamic loader is present. */
    struct stat st;
    g_ohos_assertions++;
    if (stat("/lib/ld-musl-aarch64.so.1", &st) != 0) {
        FAIL("HarmonyOS musl loader /lib/ld-musl-aarch64.so.1 not found");
    }
    g_ohos_assertions++;
#ifdef __OHOS__
    /* compiled by the OHOS clang for aarch64-unknown-linux-ohos */
#else
    FAIL("__OHOS__ not defined: consumer was not built for HarmonyOS");
#endif

    /* 2) rure must be usable from a fresh worker thread (OHOS runtime usage). */
    g_ohos_assertions++;
    pthread_t tid;
    struct ohos_worker_arg arg = {0};
    if (pthread_create(&tid, NULL, ohos_worker, &arg) != 0) {
        FAIL("pthread_create");
    }
    pthread_join(tid, NULL);
    g_ohos_assertions++;
    if (!arg.ok) FAIL("rure failed inside worker thread");

    /* 3) rure must work over an mmap'ed file-backed buffer (OHOS file I/O). */
    const char *tmp = "rure_ohos_mmap.tmp";
    const char *body = "order A-1234 shipped";
    int fd = open(tmp, O_CREAT | O_TRUNC | O_RDWR, 0644);
    g_ohos_assertions++;
    if (fd < 0) FAIL("open(%s)", tmp);
    if (write(fd, body, strlen(body)) != (ssize_t)strlen(body)) {
        close(fd);
        unlink(tmp);
        FAIL("write(%s)", tmp);
    }
    void *map = mmap(NULL, strlen(body), PROT_READ, MAP_PRIVATE, fd, 0);
    close(fd);
    g_ohos_assertions++;
    if (map == MAP_FAILED) {
        unlink(tmp);
        FAIL("mmap(%s)", tmp);
    }
    rure *re = rure_compile_must("[A-Z]-\\d{4}");
    rure_match m = {0};
    const uint8_t *mp = (const uint8_t *)map;
    g_ohos_assertions++;
    if (!rure_find(re, mp, strlen(body), 0, &m) ||
        m.end - m.start != 6 ||
        memcmp(mp + m.start, "A-1234", 6) != 0) {
        rure_free(re);
        munmap(map, strlen(body));
        unlink(tmp);
        FAIL("rure over mmap'ed OHOS buffer");
    }
    rure_free(re);
    munmap(map, strlen(body));
    unlink(tmp);

    return 0;
}

int main(void) {
    if (run_capi_checks() != 0) return 1;
    if (run_ohos_checks() != 0) return 1;
    printf("capi_assertions=%d ohos_assertions=%d\n",
           g_capi_assertions, g_ohos_assertions);
    printf("PASSED: test_rure_capi\n");
    printf("PASSED: test_ohos_platform\n");
    printf("rure consumer ok: match=(0, 5) group1_len=5\n");
    return 0;
}
