/*
 * Minimal Check-framework compatible shim (implementation).
 * See check_shim.h for details.
 */
#include "check.h"

#include <string.h>

struct TCase {
    const char *name;
    TFun *tests;
    int count;
    int capacity;
};

struct Suite {
    const char *name;
    TCase **tcases;
    int count;
    int capacity;
};

struct SRunner {
    Suite *suite;
    int tests_run;
    int tests_failed;
};

static int s_failures;

void check_shim_record_failure(void)
{
    s_failures++;
}

Suite *suite_create(const char *name)
{
    Suite *suite = calloc(1, sizeof(*suite));
    if (suite) {
        suite->name = name;
    }
    return suite;
}

TCase *tcase_create(const char *name)
{
    TCase *tc = calloc(1, sizeof(*tc));
    if (tc) {
        tc->name = name;
    }
    return tc;
}

void tcase_add_test(TCase *tc, TFun fn)
{
    if (!tc || !fn) {
        return;
    }
    if (tc->count == tc->capacity) {
        int new_capacity = tc->capacity ? tc->capacity * 2 : 8;
        TFun *grown = realloc(tc->tests, (size_t)new_capacity * sizeof(*grown));
        if (!grown) {
            return;
        }
        tc->tests = grown;
        tc->capacity = new_capacity;
    }
    tc->tests[tc->count++] = fn;
}

void suite_add_tcase(Suite *suite, TCase *tc)
{
    if (!suite || !tc) {
        return;
    }
    if (suite->count == suite->capacity) {
        int new_capacity = suite->capacity ? suite->capacity * 2 : 8;
        TCase **grown = realloc(suite->tcases, (size_t)new_capacity * sizeof(*grown));
        if (!grown) {
            return;
        }
        suite->tcases = grown;
        suite->capacity = new_capacity;
    }
    suite->tcases[suite->count++] = tc;
}

SRunner *srunner_create(Suite *suite)
{
    SRunner *runner = calloc(1, sizeof(*runner));
    if (runner) {
        runner->suite = suite;
    }
    return runner;
}

void srunner_run_all(SRunner *runner, int print_mode)
{
    Suite *suite;
    int i;

    if (!runner || !runner->suite) {
        return;
    }
    suite = runner->suite;
    if (print_mode != CK_SILENT) {
        printf("Running suite: %s\n", suite->name ? suite->name : "(unnamed)");
    }
    for (i = 0; i < suite->count; ++i) {
        TCase *tc = suite->tcases[i];
        int j;
        if (!tc) {
            continue;
        }
        if (print_mode != CK_SILENT) {
            printf("  %s:\n", tc->name ? tc->name : "(unnamed)");
        }
        for (j = 0; j < tc->count; ++j) {
            int before = s_failures;
            tc->tests[j](0);
            runner->tests_run++;
            if (s_failures > before) {
                runner->tests_failed++;
                if (print_mode != CK_SILENT) {
                    printf("    [FAILED]\n");
                }
            } else {
                if (print_mode == CK_VERBOSE) {
                    printf("    [OK]\n");
                }
            }
        }
    }
    if (print_mode != CK_SILENT) {
        printf("%d tests run, %d failed\n", runner->tests_run, runner->tests_failed);
    }
}

int srunner_ntests_failed(SRunner *runner)
{
    return runner ? runner->tests_failed : 0;
}

void srunner_free(SRunner *runner)
{
    int i;

    if (!runner) {
        return;
    }
    if (runner->suite) {
        for (i = 0; i < runner->suite->count; ++i) {
            TCase *tc = runner->suite->tcases[i];
            if (tc) {
                free(tc->tests);
            }
            free(tc);
        }
        free(runner->suite->tcases);
        free(runner->suite);
    }
    free(runner);
}