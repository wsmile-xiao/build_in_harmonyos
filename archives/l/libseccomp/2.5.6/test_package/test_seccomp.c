/* libseccomp consumer test (R34): actually call the tested API.
 * seccomp_version()/seccomp_api_get() are pure user-space (no kernel
 * filter load) — linked program execution (not dlopen, which the CI
 * el2 sandbox rejects with Permission denied).
 * AI review tid-186014328 (same as #6043): previous test only did
 * existence checks (listdir/ELF magic/headers) — this linked program
 * really calls seccomp_version()/seccomp_api_get().
 */
#include <seccomp.h>
#include <stdio.h>

int main(void) {
    const char *ver = seccomp_version();
    int api = seccomp_api_get();
    if (!ver || api == 0) {
        fprintf(stderr, "seccomp API call failed (ver=%s api=%d)\n",
                ver ? ver : "(null)", api);
        return 1;
    }
    printf("OK: libseccomp %s (api %d)\n", ver, api);
    return 0;
}
