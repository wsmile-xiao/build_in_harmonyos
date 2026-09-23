#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <locale.h>

#include <librcc.h>

int main(void) {
    int failures = 0;

    /* Case 1: library init must succeed. */
    if (rccInit() != 0) {
        fprintf(stderr, "FAIL: rccInit() returned non-zero\n");
        return 1;
    }
    printf("ok 1: rccInit succeeded\n");

    /* Case 2: default context with two standard classes. */
    {
        rcc_class classes[] = {
            { "input", RCC_CLASS_STANDARD, NULL, NULL, "Input Encoding", 0 },
            { "output", RCC_CLASS_STANDARD, "LC_CTYPE", NULL, "Output Encoding", 0 },
            { NULL }
        };
        setlocale(LC_ALL, "");
        if (rccInitDefaultContext(NULL, 0, 0, classes, 0) != 0) {
            fprintf(stderr, "FAIL: rccInitDefaultContext failed\n");
            failures++;
        } else {
            printf("ok 2: rccInitDefaultContext succeeded\n");
        }
    }

    /* Case 3: language query + passthrough recode must not crash. */
    {
        const char *lang = rccGetCurrentLanguageName(NULL);
        printf("info: current language: %s\n", lang ? lang : "(null, allowed)");
        /* Recode ASCII passthrough: must return non-NULL or echo input. */
        char *recoded = rccRecode(NULL, 0, 1, "hello librcc");
        if (recoded) {
            if (strstr(recoded, "hello") == NULL) {
                fprintf(stderr, "FAIL: rccRecode mangled ASCII passthrough\n");
                failures++;
            } else {
                printf("ok 3: rccRecode passthrough: %s\n", recoded);
            }
            free(recoded);
        } else {
            /* NULL means no recoding required: acceptable, still exercised. */
            printf("ok 3: rccRecode returned NULL (no recoding required)\n");
        }
    }

    rccFree();
    if (failures) {
        fprintf(stderr, "FAIL: %d case(s) failed\n", failures);
        return 1;
    }
    printf("test librcc 0.2.13: OK (3 cases)\n");
    return 0;
}
