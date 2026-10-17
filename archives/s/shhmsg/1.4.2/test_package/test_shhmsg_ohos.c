#include <shhmsg.h>

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef __OHOS__
#error "This test must be compiled by the HarmonyOS toolchain"
#endif

#ifndef __aarch64__
#error "This test targets HarmonyOS PC aarch64"
#endif

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

int main(void)
{
    const char *path = "shhmsg-ohos-output.txt";
    FILE *stream = fopen(path, "w+");
    FILE *old_message;
    FILE *old_error;
    char buffer[256];

    CHECK(sizeof(void *) == 8 && sizeof(long) == 8,
          "HarmonyOS PC uses the aarch64 LP64 data model");
    if (stream == NULL) {
        perror("fopen");
        return EXIT_FAILURE;
    }

    old_message = msgSetMessageStream(stream);
    msgSetShowNameAlways(MSG_OFF);
    msgSetQuiet(MSG_OUTPUT);
    msgMessage("HarmonyOS stream");
    CHECK(read_stream(stream, buffer, sizeof(buffer)) &&
              strcmp(buffer, "HarmonyOS stream") == 0,
          "HarmonyOS writable file streams accept redirected messages");

    fclose(stream);
    stream = fopen(path, "w+");
    if (stream == NULL) {
        perror("fopen");
        return EXIT_FAILURE;
    }
    msgSetMessageStream(stream);
    msgMessage("鸿蒙消息");
    CHECK(read_stream(stream, buffer, sizeof(buffer)) &&
              strcmp(buffer, "鸿蒙消息") == 0,
          "HarmonyOS preserves UTF-8 message bytes");

    fclose(stream);
    stream = fopen(path, "w+");
    if (stream == NULL) {
        perror("fopen");
        return EXIT_FAILURE;
    }
    old_error = msgSetErrorStream(stream);
    errno = ENOENT;
    msgPerror("open");
    CHECK(read_stream(stream, buffer, sizeof(buffer)) &&
              strstr(buffer, strerror(ENOENT)) != NULL,
          "HarmonyOS strerror text is used by msgPerror");

    msgSetMessageStream(old_message);
    msgSetErrorStream(old_error);
    fclose(stream);
    remove(path);

    printf("shhmsg HarmonyOS test: 4/4 assertions passed\n");
    return check_number == 4 ? EXIT_SUCCESS : EXIT_FAILURE;
}
