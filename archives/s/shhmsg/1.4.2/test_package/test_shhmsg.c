#include <shhmsg.h>

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int check_number;

#define CHECK(condition, name)                              \
    do {                                                    \
        ++check_number;                                     \
        if (!(condition)) {                                 \
            printf("not ok %d - %s\n", check_number, name); \
            return EXIT_FAILURE;                            \
        }                                                   \
        printf("ok %d - %s\n", check_number, name);        \
    } while (0)

static int read_stream(FILE *stream, char *buffer, size_t size)
{
    size_t count;

    if (fflush(stream) != 0 || fseek(stream, 0, SEEK_SET) != 0)
        return 0;
    count = fread(buffer, 1, size - 1, stream);
    buffer[count] = '\0';
    return 1;
}

static int reset_stream(FILE *stream)
{
    if (fflush(stream) != 0 || fseek(stream, 0, SEEK_SET) != 0)
        return 0;
    if (ftruncate(fileno(stream), 0) != 0)
        return 0;
    return fseek(stream, 0, SEEK_SET) == 0;
}

int main(void)
{
    const char *path = "shhmsg-consumer-output.txt";
    FILE *stream = fopen(path, "w+");
    FILE *old_error;
    FILE *old_message;
    FILE *old_verbose;
    char buffer[256];

    if (stream == NULL) {
        perror("fopen");
        return EXIT_FAILURE;
    }

    CHECK(strcmp(msgGetName(), "!!!") == 0,
          "unset program name uses the documented fallback");
    msgSetName("/opt/tools/shhmsg-consumer");
    CHECK(strcmp(msgGetName(), "shhmsg-consumer") == 0,
          "program name strips its path");

    old_error = msgSetErrorStream(stream);
    old_message = msgSetMessageStream(stream);
    old_verbose = msgSetVerboseStream(stream);
    CHECK(old_error == stderr, "error stream setter returns stderr by default");
    CHECK(old_message == stdout, "message stream setter returns stdout by default");
    CHECK(old_verbose == stderr, "verbose stream setter returns stderr by default");

    msgError("failure %d", 7);
    CHECK(read_stream(stream, buffer, sizeof(buffer)), "error output is readable");
    CHECK(strcmp(buffer, "shhmsg-consumer: failure 7") == 0,
          "error output includes the program name and formatting");

    CHECK(reset_stream(stream), "test output stream can be reset");
    msgSetShowNameAlways(MSG_OFF);
    msgSetQuiet(MSG_OUTPUT);
    msgMessage("message %s", "visible");
    CHECK(read_stream(stream, buffer, sizeof(buffer)), "message output is readable");
    CHECK(strcmp(buffer, "message visible") == 0,
          "normal messages preserve printf formatting");

    CHECK(reset_stream(stream), "message stream can be reset");
    msgSetQuiet(MSG_QUIET);
    msgMessage("hidden");
    CHECK(read_stream(stream, buffer, sizeof(buffer)) && buffer[0] == '\0',
          "quiet mode suppresses normal messages");

    msgSetQuiet(MSG_OUTPUT);
    msgSetShowNameAlways(MSG_ON);
    msgMessage("named");
    CHECK(read_stream(stream, buffer, sizeof(buffer)), "named message is readable");
    CHECK(strcmp(buffer, "shhmsg-consumer: named") == 0,
          "show-name mode prefixes normal messages");

    CHECK(reset_stream(stream), "verbose stream can be reset");
    msgSetShowNameAlways(MSG_OFF);
    msgSetVerbose(2);
    msgVerbose(3, "hidden");
    msgVerbose(2, "shown %d", 2);
    CHECK(read_stream(stream, buffer, sizeof(buffer)) && strcmp(buffer, "shown 2") == 0,
          "verbose level filters messages and keeps formatting");

    CHECK(reset_stream(stream), "environment-level stream can be reset");
    setenv("SHHMSG-CON_LEVEL", "4", 1);
    msgSetVerbose(MSG_VERBOSE_DEFAULT);
    msgVerbose(4, "environment");
    CHECK(read_stream(stream, buffer, sizeof(buffer)) &&
              strcmp(buffer, "environment") == 0,
          "default verbose level is read from the program environment");

    CHECK(reset_stream(stream), "errno stream can be reset");
    errno = 0;
    msgPerror("ignored");
    CHECK(read_stream(stream, buffer, sizeof(buffer)) && buffer[0] == '\0',
          "msgPerror is silent when errno is zero");

    errno = EINVAL;
    msgPerror("operation");
    CHECK(read_stream(stream, buffer, sizeof(buffer)) &&
              strstr(buffer, "operation: ") == buffer &&
              strstr(buffer, strerror(EINVAL)) != NULL,
          "msgPerror appends the system errno description");

    msgSetErrorStream(old_error);
    msgSetMessageStream(old_message);
    msgSetVerboseStream(old_verbose);
    fclose(stream);
    remove(path);

    printf("shhmsg consumer test: 21/21 assertions passed\n");
    return check_number == 21 ? EXIT_SUCCESS : EXIT_FAILURE;
}
