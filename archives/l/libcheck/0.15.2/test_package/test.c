#include <check.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* CI self-configuration of a writable IPC temp directory.
 *
 * libcheck's open_tmp_file() picks the IPC temp directory in this priority:
 *   1) getenv("TEMP")   -- CI (conan ctest) provides NO TEMP
 *   2) P_tmpdir (/tmp)  -- hard-coded; CI sandbox /tmp is NOT writable
 *   3) getenv("TMPDIR") -- CI DOES export TMPDIR=/data/storage/el2/base/cache
 *   4) "."
 * So without self-configuration the runner falls to /tmp, mkstemp() fails,
 * check_msg.c:317 eprintf() -> exit(2), and ctest/conan test() report failure
 * even though the library and the consumer binary built fine.
 *
 * Fix: BEFORE creating any SRunner, probe candidate directories for real
 * writability (mkstemp + close + unlink) and, when one works, setenv TEMP so
 * libcheck uses it.  Candidates cover the CI-provided TMPDIR plus common
 * fallbacks; a candidate is accepted only if a real file can be created in it.
 */

static int probe_writable(const char *cand)
{
    char probe[4096];
    int fd;

    if (cand == NULL || cand[0] == '\0')
        return 0;
    if (snprintf(probe, sizeof(probe), "%s/ck_probe_XXXXXX", cand) >= (int)sizeof(probe))
        return 0;
    fd = mkstemp(probe);
    if (fd < 0)
        return 0;
    close(fd);
    unlink(probe);
    return 1;
}

static void self_configure_temp(void)
{
    static const char *const candidates[] = {
        /* CI-provided env (conan ctest sandbox) */
        "/data/storage/el2/base/cache",  /* TMPDIR value seen in CI environment */
        "/data/storage/el2/base",
        "/storage/Users/currentUser/tmp",
        "/tmp",
        ".",
        NULL,
    };
    const char *env_tmpdir = getenv("TMPDIR");
    size_t i;

    /* 1) honour a TMPDIR that is actually writable */
    if (probe_writable(env_tmpdir)) {
        setenv("TEMP", env_tmpdir, 1);
        return;
    }
    /* 2) probe the fixed candidates in order */
    for (i = 0; candidates[i] != NULL; i++) {
        if (probe_writable(candidates[i])) {
            setenv("TEMP", candidates[i], 1);
            fprintf(stderr, "[test_libcheck] self-configured writable TEMP=%s\n", candidates[i]);
            return;
        }
    }
    /* 3) last resort: current working directory (ctest build dir) */
    if (probe_writable(".")) {
        setenv("TEMP", ".", 1);
        return;
    }
    fprintf(stderr, "[test_libcheck] WARNING: no writable temp dir found\n");
}

START_TEST(test_consumer_api_roundtrip)
{
    /* real assertion executed through libcheck's ck_assert machinery */
    ck_assert_int_eq(2 + 2, 4);
    ck_assert_str_eq("libcheck", "libcheck");
}
END_TEST

START_TEST(test_consumer_srunner_tracks_failures)
{
    /* verify srunner_ntests_failed returns 0 for a passing suite */
    Suite *s = suite_create("inner");
    TCase *tc = tcase_create("core");
    tcase_add_test(tc, test_consumer_api_roundtrip);
    suite_add_tcase(s, tc);
    SRunner *sr = srunner_create(s);
    srunner_run_all(sr, CK_SILENT);
    ck_assert_int_eq(srunner_ntests_failed(sr), 0);
    srunner_free(sr);
}
END_TEST

int main(void)
{
    self_configure_temp();  /* must run before any SRunner is created */

    Suite *s = suite_create("consumer");
    TCase *tc = tcase_create("core");
    tcase_add_test(tc, test_consumer_api_roundtrip);
    tcase_add_test(tc, test_consumer_srunner_tracks_failures);
    suite_add_tcase(s, tc);

    SRunner *sr = srunner_create(s);
    srunner_run_all(sr, CK_NORMAL);
    int failed = srunner_ntests_failed(sr);
    srunner_free(sr);

    printf("libcheck consumer test: suites=1 tests=2 failures=%d\n", failed);
    return failed == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
