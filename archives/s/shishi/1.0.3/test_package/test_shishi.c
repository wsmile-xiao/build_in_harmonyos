/*
 * Consumer-side API assertions for libshishi / libshisa.
 *
 * Deterministic, offline checks only.  All four assertions were validated
 * empirically on-device before being written; the shisa one deliberately
 * avoids shisa_init()'s compiled-in defaults (see below).
 */
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

#include <shisa.h>
#include <shishi.h>

static int failures = 0;

#define CHECK(cond, msg)                        \
    do {                                        \
        if (cond) {                             \
            printf("ok: %s\n", msg);            \
        } else {                                \
            fprintf(stderr, "FAIL: %s\n", msg); \
            failures++;                         \
        }                                       \
    } while (0)

int main(void)
{
    Shisa *dbh = NULL;
    int rc;

    /* 1: shishi_check_version(SHISHI_VERSION) answers with the exact version */
    const char *req = shishi_check_version(SHISHI_VERSION);
    CHECK(req != NULL && strcmp(req, SHISHI_VERSION) == 0,
          "shishi_check_version(SHISHI_VERSION) reports " SHISHI_VERSION);

    /* 2: NULL request returns the library's own version */
    const char *own = shishi_check_version(NULL);
    CHECK(own != NULL && strcmp(own, SHISHI_VERSION) == 0,
          "shishi_check_version(NULL) reports library version");

    /* 3: error string API links and answers for SHISHI_OK (0) */
    const char *err = shishi_strerror(SHISHI_OK);
    CHECK(err != NULL && err[0] != '\0', "shishi_strerror(SHISHI_OK) non-empty");

    /* 4: libshisa database backend lifecycle with an explicit, writable
     *    location.  shisa_init()'s compiled-in defaults are host-absolute
     *    (/etc/shishi/shisa.conf, <prefix>/var/shishi) and unusable for a
     *    conan-packaged consumer, so write a config pointing at a db dir
     *    below the current working directory (the test_package build dir,
     *    see cwd= in test_package/conanfile.py) and initialize from it.
     *    Probe-verified on device: returns SHISA_OK, then shisa_done(). */
    mkdir("tshisa-db", 0755);  /* EEXIST on re-run is fine */
    FILE *cfg = fopen("tshisa.conf", "w");
    int cfg_ok = (cfg != NULL);
    if (cfg_ok) {
        fputs("db file tshisa-db\n", cfg);
        fclose(cfg);
    }
    dbh = NULL;
    rc = cfg_ok ? shisa_init_with_paths(&dbh, "tshisa.conf") : -1;
    CHECK(cfg_ok && rc == SHISA_OK && dbh != NULL,
          "shisa_init_with_paths opens explicit writable db location");
    if (dbh != NULL)
        shisa_done(dbh);

    printf("test_shishi: %d assertion(s) checked, %d failed\n", 4, failures);
    return failures == 0 ? 0 : 1;
}
