#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <popt.h>

int main(int argc, char *argv[]) {
    int verbose = 0;
    int intval = 0;
    char *output = NULL;

    struct poptOption options[] = {
        {"verbose", 'v', POPT_ARG_NONE, &verbose, 0, "be verbose", NULL},
        {"output",  'o', POPT_ARG_STRING, &output, 0, "output file", "FILE"},
        {"int",     'i', POPT_ARG_INT, &intval, 0, "integer value", "N"},
        POPT_AUTOHELP
        POPT_TABLEEND
    };

    poptContext ctx = poptGetContext("test_popt", argc, (const char **)argv,
                                     options, 0);
    if (!ctx) {
        fprintf(stderr, "popt error: failed to create context\n");
        return 1;
    }

    int rc;
    while ((rc = poptGetNextOpt(ctx)) > 0) {
        /* parse options */
    }

    if (rc < -1) {
        const char *bad = poptBadOption(ctx, POPT_BADOPTION_NOALIAS);
        const char *err = poptStrerror(rc);
        fprintf(stderr, "popt error: %s: %s\n",
                bad ? bad : "(unknown option)",
                err ? err : "(unknown error)");
        poptFreeContext(ctx);
        return 1;
    }

    poptFreeContext(ctx);

    /* assertions */
    if (!verbose) {
        fprintf(stderr, "FAIL: verbose not parsed\n");
        return 1;
    }
    if (intval != 42) {
        fprintf(stderr, "FAIL: int not parsed (got %d, want 42)\n", intval);
        return 1;
    }
    if (!output || strcmp(output, "out.txt") != 0) {
        fprintf(stderr, "FAIL: string not parsed (got %s, want out.txt)\n",
                output ? output : "()");
        return 1;
    }

    printf("popt test PASSED: verbose=%d int=%d output=%s\n",
           verbose, intval, output ? output : "()");
    return 0;
}
