#include <csv.h>

#include <stdio.h>
#include <string.h>

static int field_count = 0;
static int row_count = 0;

static void field_cb(void *data, size_t len, void *ctx)
{
    (void)data;
    (void)len;
    (void)ctx;
    field_count++;
}

static void row_cb(int c, void *ctx)
{
    (void)c;
    (void)ctx;
    row_count++;
}

int main(void)
{
    struct csv_parser parser;
    const char input[] =
        "name,age\n"
        "Alice,20\n"
        "Bob,30\n";

    char output[32];
    const char value[] = "a,b";
    const char expected[] = "\"a,b\"";

    size_t parsed;
    size_t written;
    if (CSV_MAJOR != 3 || CSV_MINOR != 0 || CSV_RELEASE != 3)
        return 1;

    if (csv_init(&parser, 0) != 0)
        return 2;

    parsed = csv_parse(
        &parser,
        input,
        strlen(input),
        field_cb,
        row_cb,
        NULL
    );

    if (parsed != strlen(input)) {
        csv_free(&parser);
        return 3;
    }

    if (csv_fini(&parser, field_cb, row_cb, NULL) != 0) {
        csv_free(&parser);
        return 4;
    }

    csv_free(&parser);

    if (field_count != 6)
        return 5;

    if (row_count != 3)
        return 6;

    written = csv_write(
        output,
        sizeof(output),
        value,
        strlen(value)
    );

    if (written != strlen(expected))
        return 7;

    if (memcmp(output, expected, written) != 0)
        return 8;

    printf("libcsv 3.0.3 smoke test passed\n");
    return 0;
}
