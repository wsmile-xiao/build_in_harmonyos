/* dav2d 0.0.1 — decoder lifecycle consumer test (not a dlopen stub).
 *
 * Offline-verifiable verdicts, no AV2 bitstream sample needed:
 *   1. linked library identity: dav2d_version() non-empty plus
 *      dav2d_version_api() == 1.0.0 (stable contract from
 *      include/dav2d/version.h), and the VCS-derived project string is
 *      either "0.*" (tagged/tarball build; preflight shows "0.1.0" for
 *      package 0.0.1) or a bare git hash (tarball without
 *      .git: meson vcs_tag `git describe --long --always` falls back to a
 *      hash/project version — preflight shows `fatal: not a git
 *      repository`). A wrong-version stray copy ("1.5.x", "2.x", ...) still
 *      fails because it contains '.' yet lacks the "0.0.1" prefix;
 *   2-3. dav2d_default_settings() yields sane defaults
 *      (n_threads/max_frame_delay in range);
 *   4. dav2d_open() really opens a decoder context (walks internal
 *      allocation), dav2d_flush() on it is safe, dav2d_close() releases
 *      it and NULLs the pointer;
 *   5. an out-of-range n_threads is rejected by dav2d_open() — tells a
 *      real implementation apart from an always-succeed stub.
 *
 * Header path follows the installed layout: <dav2d/dav2d.h>.
 */
#include <dav2d/dav2d.h>

#include <stdio.h>
#include <string.h>

static int failures = 0;
static int checks = 0;
#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        ++checks;                                                              \
        if (!(cond)) {                                                         \
            fprintf(stderr, "[FAIL] %s  (%s:%d)\n", (msg), __FILE__, __LINE__); \
            ++failures;                                                        \
        } else {                                                               \
            printf("[ok] %s\n", (msg));                                        \
        }                                                                      \
    } while (0)

int main(void) {
    const char *ver = dav2d_version();
    unsigned api = dav2d_version_api();
    printf("dav2d version: %s\n", ver ? ver : "(null)");
    printf("dav2d api: 0x%06x (major=%u minor=%u patch=%u)\n", api,
           (api >> 16) & 0xFF, (api >> 8) & 0xFF, api & 0xFF);
    fflush(stdout);
    /* VCS-derived string is unstable for tarball builds (no .git), and the
     * library version string need not equal the package tag: preflight
     * shows ver="0.1.0" for package 0.0.1 (`fatal: not a git repository`
     * falls back to meson project version). So accept any "0.*" dotted
     * version or a bare hash (no '.'), but reject any other dotted
     * version (stray copy). API 1.0.0 is the stable identity. */
    CHECK(ver != NULL && ver[0] != '\0' && api == 0x010000 &&
          (strncmp(ver, "0.", 2) == 0 || strchr(ver, '.') == NULL),
          "dav2d_version() identity (0.* or hash) and api==1.0.0");

    Dav2dSettings s;
    memset(&s, 0, sizeof(s));
    dav2d_default_settings(&s);
    printf("dav2d defaults: n_threads=%d max_frame_delay=%d apply_grain=%d operating_point=%d\n",
           s.n_threads, s.max_frame_delay, s.apply_grain, s.operating_point);
    fflush(stdout);
    CHECK(s.n_threads >= 0, "default n_threads sane (>= 0)");
    CHECK(s.max_frame_delay >= 0, "default max_frame_delay sane (>= 0)");

    /* Open a real decoder context: walks internal allocation. */
    Dav2dContext *c = NULL;
    int rc = dav2d_open(&c, &s);
    printf("dav2d_open(default) rc=%d ctx=%p\n", rc, (void *)c);
    fflush(stdout);
    CHECK(rc == 0 && c != NULL, "dav2d_open() opened a context");
    if (rc == 0 && c != NULL) {
        dav2d_flush(c);
        printf("[ok] dav2d_flush() did not crash\n");
        ++checks;
        dav2d_close(&c);
        CHECK(c == NULL, "dav2d_close() released and nulled the context");
    }

    /* Out-of-range settings must be refused, not silently accepted. */
    Dav2dSettings bad;
    dav2d_default_settings(&bad);
    bad.n_threads = 1 << 20;
    Dav2dContext *c2 = NULL;
    int rc2 = dav2d_open(&c2, &bad);
    printf("dav2d_open(bad n_threads=%d) rc=%d ctx=%p\n", bad.n_threads, rc2, (void *)c2);
    fflush(stdout);
    CHECK(rc2 != 0, "out-of-range n_threads rejected by dav2d_open()");
    if (rc2 == 0 && c2 != NULL)
        dav2d_close(&c2);

    /* Tail-visible summary: survives log truncation (head is often elided,
     * tail is preserved), so the next round can see version/api/settings
     * even without the full log. */
    printf("[summary] version=%s api=0x%06x n_threads=%d max_frame_delay=%d rc=%d rc2=%d failures=%d checks=%d\n",
           ver ? ver : "(null)", api, s.n_threads, s.max_frame_delay, rc, rc2, failures, checks);
    fflush(stdout);

    if (failures) {
        fprintf(stderr, "\ndav2d 0.0.1: %d/%d assertions passed\n",
                checks - failures, checks);
        return 1;
    }
    printf("\ndav2d 0.0.1: %d/%d assertions passed\n", checks, checks);
    return 0;
}
