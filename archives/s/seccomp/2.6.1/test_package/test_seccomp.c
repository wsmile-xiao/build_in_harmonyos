/* seccomp (libseccomp) consumer test (R34): actually call the tested API.
 * seccomp_version()/seccomp_api_get() are pure user-space (no kernel
 * filter load) — linked program execution (not dlopen, which the CI
 * el2 sandbox rejects with Permission denied).
 * seccomp_version() returns `const struct scmp_version *` (major/minor/
 * micro), NOT a string — print the struct fields.
 */
#include <seccomp.h>
#include <stdio.h>

int main(void) {
    const struct scmp_version *ver = seccomp_version();
    int api = seccomp_api_get();
    if (!ver || api == 0) {
        fprintf(stderr, "seccomp API call failed (ver=%p api=%d)\n",
                (void *)ver, api);
        return 1;
    }
    printf("OK: libseccomp %u.%u.%u (api %d)\n",
           ver->major, ver->minor, ver->micro, api);
    return 0;
}
