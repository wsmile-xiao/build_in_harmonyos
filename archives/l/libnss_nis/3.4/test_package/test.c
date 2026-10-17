/*
 * test_libnss_nis — consumer test for the libnss_nis NSS module.
 *
 * libnss_nis is a glibc Name Service Switch module: it is not linked at
 * build time, glibc's NSS framework dlopen()s libnss_nis.so.2 and resolves
 * the _nss_nis_*_r entry points. This consumer simulates a business-layer
 * NSS consumer exactly that way:
 *
 *   1. dlopen() the module artifact (libnss_nis.so.2),
 *   2. dlsym() the public API symbol _nss_nis_getpwnam_r,
 *   3. actually call it with a NIS-domain-less environment and verify the
 *      observable result: no NIS domain is configured on OHOS, so the NIS
 *      backend must return NSS_STATUS_UNAVAIL (not crash, not hang, not a
 *      wrong status). This proves the module loads, its symbol table is
 *      intact and the reentrant entry point executes end-to-end.
 */
#include <stdio.h>
#include <string.h>
#include <dlfcn.h>
#include <pwd.h>

/* glibc nss_status values (libnss_nis exports them via its public API). */
#define NSS_STATUS_TRYAGAIN (-2)
#define NSS_STATUS_UNAVAIL  (-1)
#define NSS_STATUS_NOTFOUND 0
#define NSS_STATUS_SUCCESS  1
#define NSS_STATUS_RETURN   2

typedef int (*nss_getpwnam_r_fn)(const char *name, struct passwd *pwd,
                                 char *buffer, size_t buflen, int *errnop);

int main(void)
{
    void *handle;
    nss_getpwnam_r_fn fn;
    char *error;
    int status;
    struct passwd pw;
    char buf[2048];
    int errnop = 0;

    handle = dlopen("libnss_nis.so.2", RTLD_NOW);
    if (!handle) {
        fprintf(stderr, "FAIL: dlopen(libnss_nis.so.2): %s\n", dlerror());
        return 1;
    }

    fn = (nss_getpwnam_r_fn)dlsym(handle, "_nss_nis_getpwnam_r");
    if ((error = dlerror()) != NULL) {
        fprintf(stderr, "FAIL: dlsym(_nss_nis_getpwnam_r): %s\n", error);
        dlclose(handle);
        return 1;
    }

    /* Real call of the public reentrant API. On OHOS there is no NIS
     * domain, so yp_get_default_domain() fails and the backend must
     * report NSS_STATUS_UNAVAIL. Any other status (or a crash) means the
     * adaptation is broken. */
    memset(&pw, 0, sizeof(pw));
    status = fn("root", &pw, buf, sizeof(buf), &errnop);

    if (status == NSS_STATUS_UNAVAIL) {
        printf("PASS: _nss_nis_getpwnam_r returned NSS_STATUS_UNAVAIL "
               "(no NIS domain configured, expected)\n");
        dlclose(handle);
        return 0;
    }

    fprintf(stderr, "FAIL: _nss_nis_getpwnam_r returned status %d "
            "(expected NSS_STATUS_UNAVAIL=%d), errno=%d\n",
            status, NSS_STATUS_UNAVAIL, errnop);
    dlclose(handle);
    return 1;
}
