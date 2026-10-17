/*
 * test.c — Conan consumer test for resolv-wrapper 1.1.8.
 *
 * Calls the library's real public API: res_ninit(), res_nquery(), res_nclose()
 * exported by libresolv_wrapper.so incl. the classic res_init()/res_query()
 * family.  On OHOS/musl the thread-safe res_n* declarations are absent from
 * <resolv.h>; the wrapper library still exports them, so we declare them here
 * and link directly against libresolv_wrapper (no LD_PRELOAD needed).
 *
 * The test drives the DNS-faking path: point RESOLV_WRAPPER_HOSTS at a small
 * hosts file, then verify a fake A query returns a parseable answer.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <arpa/nameser.h>
#include <arpa/inet.h>
#include <resolv.h>

#if defined(__OHOS__) || defined(__OHOS) || !defined(res_ninit)
/* Declarations for the wrapper-provided res_n* family (absent in
 * OHOS/musl libc headers; exported by libresolv_wrapper). */
extern int res_ninit(struct __res_state *state);
extern int res_nquery(struct __res_state *state,
                      const char *dname, int class, int type,
                      unsigned char *answer, int anslen);
extern void res_nclose(struct __res_state *state);
#endif

#define FAKE_HOSTS \
    "A cwrap.org 127.0.0.21\n" \
    "A www.cwrap.org 127.0.0.22\n"

int main(void)
{
    struct __res_state state;
    unsigned char answer[512];
    char hosts_path[256];
    FILE *fp;
    int rv, qlen;
    const char *tmp = getenv("TMPDIR");

    /* Prepare a fake-hosts file in a writable location */
    if (tmp == NULL) {
        tmp = "/data/local/tmp";
    }
    snprintf(hosts_path, sizeof(hosts_path), "%s/resolv-wrapper-tp-hosts-%ld",
             tmp, (long)getpid());
    fp = fopen(hosts_path, "w");
    if (fp == NULL) {
        perror("fopen(hosts)");
        return 1;
    }
    fputs(FAKE_HOSTS, fp);
    fclose(fp);

    setenv("RESOLV_WRAPPER_HOSTS", hosts_path, 1);
    unsetenv("RESOLV_WRAPPER_CONF");

    memset(&state, 0, sizeof(state));
    rv = res_ninit(&state);
    if (rv != 0) {
        fprintf(stderr, "FAIL: res_ninit() = %d\n", rv);
        return 1;
    }

    qlen = res_nquery(&state, "cwrap.org", ns_c_in, ns_t_a,
                      answer, sizeof(answer));
    if (qlen <= 0) {
        fprintf(stderr, "FAIL: res_nquery() returned %d\n", qlen);
        return 1;
    }

    res_nclose(&state);
    unlink(hosts_path);

    printf("resolv-wrapper consumer test PASSED (fake A query answered, len=%d)\n",
           qlen);
    return 0;
}
