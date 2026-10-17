/*
 * conan test_package for libnss-cache 0.22 (R34 fail-able rework).
 *
 * R02 fix: r01's test.c only asserted that _nss_cache_setpwent_path()
 * echoes the given path back (a constant-green check — any path input
 * trivially passes).  R34 forbids evergreen shells, so this version
 * actually drives the library's public NSS parsing path:
 *
 *   1. write a passwd.cache line under $TMPDIR (never /tmp),
 *   2. point the module at it via _nss_cache_setpwent_path(),
 *   3. call _nss_cache_getpwuid_r() and assert the parsed uid/gid/name.
 *
 * The assertions are fail-able: if the cache file parsing (fgetpwent_r
 * compat / lookup path) is wrong, getpwuid_r returns NSS_STATUS_NOTFOUND
 * or a mismatched struct and the test exits non-zero.  The negative proof
 * is a compile-time macro EXPECTED_UID: building with
 * -DEXPECTED_UID=9999 (a uid absent from the cache) makes the assertion
 * fail with a non-zero exit and the FAIL text; the default build passes.
 */
#include <nss_cache.h>
#include <nss_test.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifndef EXPECTED_UID
#define EXPECTED_UID 1001
#endif

int main(void) {
  const char *base = getenv("TMPDIR");
  if (!base || !*base) {
    base = getenv("HOME");
    if (!base || !*base) base = ".";
  }

  /* 1. cache file under $TMPDIR: name:passwd:uid:gid:gecos:dir:shell */
  char path[512];
  snprintf(path, sizeof(path), "%s/libnss-cache-0.22-test-passwd.cache", base);
  FILE *f = fopen(path, "w");
  if (f == NULL) {
    fprintf(stderr, "FAIL: cannot write cache file '%s'\n", path);
    return 3;
  }
  fprintf(f, "testuser:x:1001:1002:Test User:/home/testuser:/bin/sh\n");
  fclose(f);

  /* 2. point the module at the cache file */
  char *got = _nss_cache_setpwent_path(path);
  if (got == NULL || strcmp(got, path) != 0) {
    fprintf(stderr, "FAIL: _nss_cache_setpwent_path(%s) -> %s\n", path,
            got == NULL ? "NULL" : got);
    return 1;
  }

  /* 3. query by uid and assert the parsed fields */
  struct passwd pw;
  char buffer[1024];
  int errnop;
  enum nss_status st =
      _nss_cache_getpwuid_r((uid_t)EXPECTED_UID, &pw, buffer, sizeof(buffer),
                            &errnop);
  if (st != NSS_STATUS_SUCCESS) {
    fprintf(stderr,
            "FAIL: _nss_cache_getpwuid_r(%d) -> status %d (errnop %d); "
            "cache parsing broken or uid missing\n",
            EXPECTED_UID, st, errnop);
    return 2;
  }
  if (pw.pw_uid != (uid_t)EXPECTED_UID || pw.pw_gid != 1002 ||
      pw.pw_name == NULL || strcmp(pw.pw_name, "testuser") != 0) {
    fprintf(stderr, "FAIL: parsed uid=%lu gid=%lu name=%s (expected uid=%d "
                    "gid=1002 name=testuser)\n",
            (unsigned long)pw.pw_uid, (unsigned long)pw.pw_gid,
            pw.pw_name == NULL ? "NULL" : pw.pw_name, EXPECTED_UID);
    return 3;
  }

  printf("OK: _nss_cache_getpwuid_r(%d) parsed name='%s' uid=%lu gid=%lu "
         "from '%s'\n",
         EXPECTED_UID, pw.pw_name, (unsigned long)pw.pw_uid,
         (unsigned long)pw.pw_gid, path);
  return 0;
}
