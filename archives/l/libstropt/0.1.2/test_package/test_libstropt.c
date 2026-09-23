#include <stropt.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int check_number;

#define CHECK(condition, name)                         \
    do {                                               \
        ++check_number;                                \
        if (!(condition)) {                            \
            printf("not ok %d - %s\n", check_number, name); \
            return EXIT_FAILURE;                       \
        }                                              \
        printf("ok %d - %s\n", check_number, name); \
    } while (0)

int main(void)
{
    char buffer[256];
    char *tags[16];
    char *args[16];
    int count;

    const char *basic = "ro,noatime,uid=0,gid=1000";
    CHECK(stropt(basic, NULL, NULL, NULL) == 5, "dry-run count includes terminator");

    count = stropt(basic, tags, args, buffer);
    CHECK(count == 5 && tags[4] == NULL && args[4] == NULL, "parsed arrays are terminated");
    CHECK(strcmp(tags[0], "ro") == 0 && strcmp(tags[1], "noatime") == 0 &&
              strcmp(tags[2], "uid") == 0 && strcmp(tags[3], "gid") == 0,
          "basic option tags");
    CHECK(args[0] == NULL && args[1] == NULL && strcmp(args[2], "0") == 0 &&
              strcmp(args[3], "1000") == 0,
          "basic option arguments");

    count = stropt("values='1,2,3,4',mode=fast", tags, args, buffer);
    CHECK(count == 3 && strcmp(tags[0], "values") == 0 &&
              strcmp(args[0], "1,2,3,4") == 0 && strcmp(args[1], "fast") == 0,
          "quoted argument protects separators");

    count = stropt("equal=\\=", tags, args, buffer);
    CHECK(count == 2 && strcmp(tags[0], "equal") == 0 && strcmp(args[0], "=") == 0,
          "backslash escapes assignment character");

    count = stropt("alpha,beta # ignored,gamma", tags, args, buffer);
    CHECK(count == 3 && strcmp(tags[0], "alpha") == 0 && strcmp(tags[1], "beta") == 0,
          "comment discards the rest of the line");

    count = stroptx("alpha|beta|gamma", "", "|", 0, tags, args, buffer);
    CHECK(count == 4 && strcmp(tags[0], "alpha") == 0 && strcmp(tags[2], "gamma") == 0,
          "custom separator");

    count = stroptx("key=value", "", ",", 0, tags, args, buffer);
    CHECK(count == 2 && strcmp(tags[0], "key=value") == 0 && args[0] == NULL,
          "disabled assignment feature");

    count = stroptx("a,,c", "", ",", STROPTX_ALLOW_MULTIPLE_SEP, tags, args, buffer);
    CHECK(count == 4 && strcmp(tags[0], "a") == 0 && strcmp(tags[1], "") == 0 &&
              strcmp(tags[2], "c") == 0,
          "multiple separators preserve empty fields");

    count = stroptx("'alpha beta'", "'", " ",
                    STROPTX_KEEP_QUOTATION_MARKS_IN_TAGS, tags, args, buffer);
    CHECK(count == 2 && strcmp(tags[0], "'alpha beta'") == 0,
          "quotation marks can be preserved");

    count = stroptx("a\nb", "\n", ",", STROPTX_NEWLINE_TAGS, tags, args, buffer);
    CHECK(count == 4 && strcmp(tags[0], "a") == 0 && strcmp(tags[1], "\n") == 0 &&
              strcmp(tags[2], "b") == 0,
          "newlines can be emitted as tags");

    {
        char rebuilt[64];
        char *out_tags[] = {"ro", "uid", NULL};
        char *out_args[] = {NULL, "1000", NULL};
        char *rebuilt_result = stropt2buf(rebuilt, sizeof(rebuilt), out_tags, out_args, ',', '=');
        CHECK(rebuilt_result == rebuilt && strcmp(rebuilt, "ro,uid=1000") == 0,
              "stropt2buf rebuilds options");

        char *allocated = stropt2str(out_tags, out_args, ';', '=');
        CHECK(allocated != NULL && strcmp(allocated, "ro;uid=1000") == 0,
              "stropt2str allocates a rebuilt string");
        free(allocated);
    }

    {
        char rebuilt[64];
        char *out_tags[] = {"keep", STROPTX_DELETED_TAG, "also", NULL};
        CHECK(stropt2buf(rebuilt, sizeof(rebuilt), out_tags, NULL, ',', '=') == rebuilt &&
                  strcmp(rebuilt, "keep,also") == 0,
              "deleted tags are omitted");
    }

    count = stropt("key=value", tags, NULL, buffer);
    CHECK(count == 2 && strcmp(tags[0], "key=value") == 0,
          "NULL argument array treats assignment as tag text");

    printf("libstropt consumer test: 16/16 assertions passed\n");
    return EXIT_SUCCESS;
}
