/*
 * Minimal Check-framework compatible shim used to build and run the
 * upstream sipsak unit tests (tests/check_helper.c, tests/check_md5.c)
 * on HarmonyOS, where the Check framework is not available as a system
 * dependency.  Only the subset of the Check API used by those test
 * sources is implemented; upstream test sources are not modified.
 */
#ifndef SIPSAK_CHECK_SHIM_H
#define SIPSAK_CHECK_SHIM_H

#include <stdio.h>
#include <stdlib.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct Suite Suite;
typedef struct TCase TCase;
typedef struct SRunner SRunner;

/* Test functions produced by START_TEST have the signature void (int). */
typedef void (*TFun)(int);

#define START_TEST(name) static void name(int _i)
#define END_TEST

#define fail_unless(condition, ...)                                  \
    do {                                                             \
        if (!(condition)) {                                          \
            printf("FAIL: %s:%d: ", __FILE__, __LINE__);             \
            printf("" __VA_ARGS__);                                     \
            printf("\n");                                            \
            check_shim_record_failure();                             \
        }                                                            \
    } while (0)

enum print_output {
    CK_SILENT = 0,
    CK_MINIMAL = 1,
    CK_NORMAL = 2,
    CK_VERBOSE = 3,
    CK_ENV = 4
};

void check_shim_record_failure(void);

Suite *suite_create(const char *name);
TCase *tcase_create(const char *name);
void tcase_add_test(TCase *tc, TFun fn);
void suite_add_tcase(Suite *suite, TCase *tc);
SRunner *srunner_create(Suite *suite);
void srunner_run_all(SRunner *runner, int print_mode);
int srunner_ntests_failed(SRunner *runner);
void srunner_free(SRunner *runner);

#ifdef __cplusplus
}
#endif

#endif /* SIPSAK_CHECK_SHIM_H */