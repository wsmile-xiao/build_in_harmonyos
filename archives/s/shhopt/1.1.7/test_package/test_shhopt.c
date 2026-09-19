#include <shhopt.h>

#include <limits.h>
#include <setjmp.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int check_number;
static int callback_flag;
static int callback_int;
static const char *callback_string;
static int fatal_called;
static char fatal_message[128];
static jmp_buf fatal_jump;

#define CHECK(condition, name)                              \
    do {                                                    \
        ++check_number;                                     \
        if (!(condition)) {                                 \
            printf("not ok %d - %s\n", check_number, name); \
            return EXIT_FAILURE;                            \
        }                                                   \
        printf("ok %d - %s\n", check_number, name);        \
    } while (0)

static void set_flag(void)
{
    callback_flag = 1;
}

static void set_int(int value)
{
    callback_int = value;
}

static void set_string(char *value)
{
    callback_string = value;
}

static void capture_fatal(const char *format, ...)
{
    va_list args;

    fatal_called = 1;
    va_start(args, format);
    vsnprintf(fatal_message, sizeof(fatal_message), format, args);
    va_end(args);
    longjmp(fatal_jump, 1);
}

int main(void)
{
    int flag = 0;
    int number = 0;
    unsigned int unsigned_number = 0;
    long long_number = 0;
    unsigned long unsigned_long_number = 0;
    char *string = NULL;
    optStruct options[] = {
        {'f', "flag", OPT_FLAG, &flag, 0},
        {'s', "string", OPT_STRING, &string, 0},
        {'n', "number", OPT_INT, &number, 0},
        {'u', "unsigned", OPT_UINT, &unsigned_number, 0},
        {'l', "long", OPT_LONG, &long_number, 0},
        {'U', "unsigned-long", OPT_ULONG, &unsigned_long_number, 0},
        {'F', "flag-callback", OPT_FLAG, set_flag, OPT_CALLFUNC},
        {'N', "number-callback", OPT_INT, set_int, OPT_CALLFUNC},
        {'S', "string-callback", OPT_STRING, set_string, OPT_CALLFUNC},
        {0, NULL, OPT_END, NULL, 0}
    };

    {
        int argc = 9;
        char *argv[] = {
            "consumer", "-f", "--string=alpha", "-n-42", "--unsigned", "17",
            "--long=123456", "--unsigned-long=654321", "payload", NULL
        };
        optParseOptions(&argc, argv, options, 0);
        CHECK(flag == 1, "flag option writes its destination");
        CHECK(string != NULL && strcmp(string, "alpha") == 0,
              "long string option accepts equals syntax");
        CHECK(number == -42, "short integer option accepts an attached value");
        CHECK(unsigned_number == 17U, "unsigned option accepts a following value");
        CHECK(long_number == 123456L, "long option parses a signed long");
        CHECK(unsigned_long_number == 654321UL,
              "unsigned-long option parses an unsigned long");
        CHECK(argc == 2 && strcmp(argv[1], "payload") == 0 && argv[2] == NULL,
              "parsed options are removed from argv");
    }

    {
        int argc = 7;
        char *argv[] = {
            "consumer", "-F", "--number-callback=73", "-S", "callback",
            "left", "right", NULL
        };
        optParseOptions(&argc, argv, options, 0);
        CHECK(callback_flag == 1, "flag callback is invoked");
        CHECK(callback_int == 73, "integer callback receives its value");
        CHECK(callback_string != NULL && strcmp(callback_string, "callback") == 0,
              "string callback receives its value");
        CHECK(argc == 3 && strcmp(argv[1], "left") == 0 &&
                  strcmp(argv[2], "right") == 0,
              "callback options preserve positional arguments");
    }

    {
        int compact_flag = 0;
        int compact_callback = 0;
        optStruct compact_options[] = {
            {'a', "alpha", OPT_FLAG, &compact_flag, 0},
            {'b', "beta", OPT_FLAG, &compact_callback, 0},
            {0, NULL, OPT_END, NULL, 0}
        };
        int argc = 2;
        char *argv[] = {"consumer", "-ab", NULL};
        optParseOptions(&argc, argv, compact_options, 0);
        CHECK(compact_flag == 1 && compact_callback == 1 && argc == 1,
              "combined short flags are parsed");
    }

    {
        int argc = 5;
        char *argv[] = {"consumer", "-", "--", "--flag", "tail", NULL};
        flag = 0;
        optParseOptions(&argc, argv, options, 0);
        CHECK(argc == 4 && strcmp(argv[1], "-") == 0 &&
                  strcmp(argv[2], "--flag") == 0 && strcmp(argv[3], "tail") == 0,
              "single dash is positional and double dash stops scanning");
        CHECK(flag == 0, "options after double dash are not executed");
    }

    {
        int argc = 2;
        char *argv[] = {"consumer", "--unknown", NULL};

        optSetFatalFunc(capture_fatal);
        if (setjmp(fatal_jump) == 0)
            optParseOptions(&argc, argv, options, 0);
        CHECK(fatal_called == 1, "custom fatal callback is invoked");
        CHECK(strstr(fatal_message, "unrecognized option") != NULL,
              "custom fatal callback receives the parser diagnostic");
    }

    printf("shhopt consumer test: 16/16 assertions passed\n");
    return EXIT_SUCCESS;
}
