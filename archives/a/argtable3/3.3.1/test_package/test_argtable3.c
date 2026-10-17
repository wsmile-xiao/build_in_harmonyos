#include <stdio.h>
#include <string.h>

#include <argtable3.h>

static int expect(int condition, const char *message) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

int main(void) {
    struct arg_lit *verbose = arg_lit0("v", "verbose", "enable output");
    struct arg_int *count = arg_int1("n", "count", "<n>", "item count");
    struct arg_file *input = arg_file1(NULL, NULL, "<file>", "input file");
    struct arg_end *end = arg_end(10);
    void *argtable[] = {verbose, count, input, end};
    char *valid[] = {
        "consumer", "--verbose", "--count", "42", "input.txt"
    };
    char *invalid[] = {
        "consumer", "--count", "not-an-integer", "input.txt"
    };
    int failures = 0;

    if (arg_nullcheck(argtable) != 0) {
        fprintf(stderr, "FAIL: argtable allocation\n");
        arg_freetable(argtable, sizeof(argtable) / sizeof(argtable[0]));
        return 1;
    }

    failures += expect(
        arg_parse(5, valid, argtable) == 0,
        "valid command line parses"
    );
    failures += expect(verbose->count == 1, "verbose flag is recorded");
    failures += expect(count->ival[0] == 42, "integer value is parsed");
    failures += expect(input->count == 1, "positional file is recorded");
    failures += expect(
        strcmp(input->filename[0], "input.txt") == 0,
        "positional filename matches"
    );
    failures += expect(
        arg_parse(4, invalid, argtable) > 0,
        "invalid integer is rejected"
    );

    arg_freetable(argtable, sizeof(argtable) / sizeof(argtable[0]));
    if (failures != 0) {
        return 1;
    }

    puts("argtable3 consumer test passed (6/6 assertions)");
    return 0;
}
