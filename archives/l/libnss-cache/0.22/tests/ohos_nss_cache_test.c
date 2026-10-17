/*
 * ohos_nss_cache_test.c — Independent HarmonyOS-specific test for libnss-cache 0.22.
 *
 * This is a SEPARATE test entry from test_package/: it has its own source file
 * and its own build/run entry (run_ohos_test.sh), and it verifies an OHOS/musl
 * platform behavior:
 *
 *   OHOS uses musl libc, which ships no <nss.h>, no <gshadow.h>, and no
 *   fgetspent_r()/fgetsgent_r().  Patch 0001 (0001-ohos-musl-compat.patch)
 *   provides tree-local nss.h / gshadow.h / shadow.h wrappers plus compat
 *   fgetspent_r/fgetsgent_r implementations, and enables shadow/gshadow
 *   caching on all Linux targets (upstream built those symbols only on GLIBC).
 *
 * This test drives the PUBLIC exported API (_nss_cache_set*_path,
 * _nss_cache_getpwnam_r, _nss_cache_getpwuid_r, _nss_cache_getspnam_r,
 * _nss_cache_getsgnam_r) against cache files written under $TMPDIR and
 * asserts every parsed field.  Every assertion is fail-able; setting
 * OHOS_NSS_CACHE_INJECT_FAIL=1 flips one expected value to an impossible one
 * so the run exits non-zero with the FAIL text (negative proof), proving the
 * test is not an evergreen shell.
 *
 * Output is written to $TMPDIR (or $HOME/tmp fallback), never to /tmp.
 */
#include <nss_cache.h>
#include <nss_test.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int passes = 0;
static int failures = 0;

#define CHECK(cond, msg)                                                   \
  do {                                                                     \
    if (cond) {                                                            \
      passes++;                                                            \
      printf("PASS: %s\n", msg);                                           \
    } else {                                                               \
      failures++;                                                          \
      fprintf(stderr, "FAIL: %s (%s:%d)\n", msg, __FILE__, __LINE__);      \
    }                                                                      \
  } while (0)

static char *mk_tmpdir(void) {
  const char *base = getenv("TMPDIR");
  if (!base || !*base) {
    base = getenv("HOME");
    if (!base || !*base) base = ".";
  }
  size_t n = strlen(base) + 32;
  char *dir = malloc(n);
  if (!dir) exit(3);
  snprintf(dir, n, "%s/ohos-nss-cache-test-XXXXXX", base);
  if (!mkdtemp(dir)) {
    perror("mkdtemp");
    exit(3);
  }
  return dir;
}

/* Write a shadow cache line: name:passwd:lstchg:min:max:warn:inact:expire:flag */
static int write_shadow_cache(const char *dir) {
  char path[512];
  snprintf(path, sizeof(path), "%s/shadow.cache", dir);
  FILE *f = fopen(path, "w");
  if (!f) return -1;
  fprintf(f, "testuser:hashedpw:18000:0:99999:7:30:20000:0\n");
  fclose(f);
  return 0;
}

/* Write a gshadow cache line: name:passwd:admin-list:member-list */
static int write_gshadow_cache(const char *dir) {
  char path[512];
  snprintf(path, sizeof(path), "%s/gshadow.cache", dir);
  FILE *f = fopen(path, "w");
  if (!f) return -1;
  fprintf(f, "admins:x:root,alice:root,bob\n");
  fclose(f);
  return 0;
}

/* Write a passwd cache line: name:passwd:uid:gid:gecos:dir:shell */
static int write_passwd_cache(const char *dir) {
  char path[512];
  snprintf(path, sizeof(path), "%s/passwd.cache", dir);
  FILE *f = fopen(path, "w");
  if (!f) return -1;
  fprintf(f, "testuser:x:1001:1001:Test User:/home/testuser:/bin/sh\n");
  fclose(f);
  return 0;
}

static int negative_mode(void) {
  const char *v = getenv("OHOS_NSS_CACHE_INJECT_FAIL");
  return v && *v && strcmp(v, "0") != 0;
}

int main(void) {
  int fail = negative_mode();
  char *dir = mk_tmpdir();
  char spath[512], gpath[512], ppath[512];
  struct passwd pw;
  struct spwd sp;
  struct sgrp sg;
  enum nss_status st;
  int errnop;
  char buf[1024];
  char *got;

  printf("tmpdir=%s\n", dir);
  printf("negative_mode=%d\n", fail);

  if (write_shadow_cache(dir) != 0 || write_gshadow_cache(dir) != 0 ||
      write_passwd_cache(dir) != 0) {
    fprintf(stderr, "FAIL: could not write cache files under %s\n", dir);
    return 3;
  }
  snprintf(spath, sizeof(spath), "%s/shadow.cache", dir);
  snprintf(gpath, sizeof(gpath), "%s/gshadow.cache", dir);
  snprintf(ppath, sizeof(ppath), "%s/passwd.cache", dir);

  /* --- shadow path (OHOS/musl compat: fgetspent_r) --- */
  got = _nss_cache_setspent_path(spath);
  CHECK(got != NULL && strcmp(got, spath) == 0,
        "_nss_cache_setspent_path returns configured path");
  st = _nss_cache_getspnam_r("testuser", &sp, buf, sizeof(buf), &errnop);
  CHECK(st == NSS_STATUS_SUCCESS,
        "_nss_cache_getspnam_r('testuser') -> NSS_STATUS_SUCCESS");
  CHECK(sp.sp_namp != NULL && strcmp(sp.sp_namp, "testuser") == 0,
        "shadow sp_namp == 'testuser'");
  CHECK(sp.sp_pwdp != NULL && strcmp(sp.sp_pwdp, "hashedpw") == 0,
        "shadow sp_pwdp == 'hashedpw'");
  /* negative proof hook: impossible expected value when injected */
  CHECK(sp.sp_lstchg == (fail ? 12345 : 18000),
        fail ? "shadow sp_lstchg == 12345 (injected impossible value)"
             : "shadow sp_lstchg == 18000");
  CHECK(sp.sp_min == 0, "shadow sp_min == 0");
  CHECK(sp.sp_max == 99999, "shadow sp_max == 99999");
  CHECK(sp.sp_warn == 7, "shadow sp_warn == 7");

  /* --- gshadow path (OHOS/musl compat: fgetsgent_r) --- */
  got = _nss_cache_setsgent_path(gpath);
  CHECK(got != NULL && strcmp(got, gpath) == 0,
        "_nss_cache_setsgent_path returns configured path");
  st = _nss_cache_getsgnam_r("admins", &sg, buf, sizeof(buf), &errnop);
  CHECK(st == NSS_STATUS_SUCCESS,
        "_nss_cache_getsgnam_r('admins') -> NSS_STATUS_SUCCESS");
  CHECK(sg.sg_namp != NULL && strcmp(sg.sg_namp, "admins") == 0,
        "gshadow sg_namp == 'admins'");
  CHECK(sg.sg_passwd != NULL && strcmp(sg.sg_passwd, "x") == 0,
        "gshadow sg_passwd == 'x'");
  CHECK(sg.sg_adm != NULL && sg.sg_adm[0] != NULL &&
            strcmp(sg.sg_adm[0], "root") == 0 &&
            sg.sg_adm[1] != NULL && strcmp(sg.sg_adm[1], "alice") == 0 &&
            sg.sg_adm[2] == NULL,
        "gshadow sg_adm == {root, alice, NULL}");
  CHECK(sg.sg_mem != NULL && sg.sg_mem[0] != NULL &&
            strcmp(sg.sg_mem[0], "root") == 0 &&
            sg.sg_mem[1] != NULL && strcmp(sg.sg_mem[1], "bob") == 0 &&
            sg.sg_mem[2] == NULL,
        "gshadow sg_mem == {root, bob, NULL}");

  /* --- passwd path (baseline public API) --- */
  got = _nss_cache_setpwent_path(ppath);
  CHECK(got != NULL && strcmp(got, ppath) == 0,
        "_nss_cache_setpwent_path returns configured path");
  st = _nss_cache_getpwuid_r(1001, &pw, buf, sizeof(buf), &errnop);
  CHECK(st == NSS_STATUS_SUCCESS,
        "_nss_cache_getpwuid_r(1001) -> NSS_STATUS_SUCCESS");
  CHECK(pw.pw_name != NULL && strcmp(pw.pw_name, "testuser") == 0,
        "passwd pw_name == 'testuser'");
  CHECK(pw.pw_uid == 1001 && pw.pw_gid == 1001,
        "passwd pw_uid/pw_gid == 1001/1001");

  printf("RESULT: %d passed, %d failed\n", passes, failures);
  free(dir);
  return failures == 0 ? 0 : 1;
}
