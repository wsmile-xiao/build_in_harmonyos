#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* The upstream public header declares the CLI main symbol too.  Rename
 * that declaration while including it so the consumer's main is unambiguous. */
#define main compface_cli_main
#include <compface.h>
#undef main

#define BUFFER_SIZE 4096

static int checks;

static int check(int condition, const char *message) {
    ++checks;
    if (!condition) {
        fprintf(stderr, "CHECK-FAIL %d: %s\n", checks, message);
        return 0;
    }
    printf("CHECK-OK %d: %s\n", checks, message);
    return 1;
}

static int make_face(char *buffer, size_t capacity) {
    size_t used = 0;
    int row;
    int word;

    for (row = 0; row < 48; ++row) {
        for (word = 0; word < 3; ++word) {
            unsigned value = ((row + word) % 2 == 0) ? 0xAAAAu : 0x5555u;
            int written = snprintf(buffer + used, capacity - used,
                                    "0x%04X,%s", value,
                                    word == 2 ? "\n" : "");
            if (written < 0 || (size_t)written >= capacity - used) {
                return 0;
            }
            used += (size_t)written;
        }
    }
    return 1;
}

static int write_text(const char *path, const char *text) {
    FILE *file = fopen(path, "w");
    if (file == NULL) {
        return 0;
    }
    if (fputs(text, file) == EOF) {
        fclose(file);
        return 0;
    }
    return fclose(file) == 0;
}

static int read_text(const char *path, char *buffer, size_t capacity) {
    FILE *file = fopen(path, "r");
    size_t length;
    if (file == NULL) {
        return 0;
    }
    length = fread(buffer, 1, capacity - 1, file);
    if (ferror(file) || fclose(file) != 0) {
        return 0;
    }
    buffer[length] = '\0';
    return length < capacity - 1;
}

static int run_command(const char *format, const char *binary,
                       const char *input, const char *output) {
    char command[BUFFER_SIZE];
    int written = snprintf(command, sizeof(command), format, binary, input,
                            output);
    return written > 0 && (size_t)written < sizeof(command) &&
           system(command) == 0;
}

static int count_hex_values(const char *text) {
    int count = 0;
    const char *cursor = text;
    while ((cursor = strstr(cursor, "0x")) != NULL) {
        ++count;
        cursor += 2;
    }
    return count;
}

int main(int argc, char **argv) {
    char original[BUFFER_SIZE];
    char api_buffer[BUFFER_SIZE];
    char decoded[BUFFER_SIZE];
    char xbm[BUFFER_SIZE];

    if (argc != 3) {
        fprintf(stderr, "usage: test_libcompface <compface> <uncompface>\n");
        return 2;
    }

    if (!check(make_face(original, sizeof(original)),
               "generated deterministic 48x48 face")) {
        return 1;
    }

    strcpy(api_buffer, original);
    if (!check(compface(api_buffer) == 0, "compface API compresses input")) {
        return 1;
    }
    if (!check(uncompface(api_buffer) == 0, "uncompface API decompresses output")) {
        return 1;
    }
    if (!check(strcmp(api_buffer, original) == 0,
               "library API round-trip preserves all pixels")) {
        return 1;
    }

    if (!check(write_text("compface-input.txt", original),
               "writes CLI input fixture")) {
        return 1;
    }
    if (!check(run_command("\"%s\" < %s > compface-output.txt", argv[1],
                          "compface-input.txt", "compface-output.txt"),
               "compface CLI compresses fixture")) {
        return 1;
    }
    if (!check(run_command("\"%s\" < compface-output.txt > compface-decoded.txt",
                          argv[2], "compface-output.txt", "compface-decoded.txt"),
               "uncompface CLI decompresses fixture")) {
        return 1;
    }
    if (!check(read_text("compface-decoded.txt", decoded, sizeof(decoded)),
               "reads CLI round-trip output")) {
        return 1;
    }
    if (!check(strcmp(decoded, original) == 0,
               "CLI round-trip preserves all pixels")) {
        return 1;
    }

    if (!check(run_command("\"%s\" -X < compface-output.txt > compface.xbm",
                          argv[2], "compface-output.txt", "compface.xbm"),
               "uncompface -X emits XBM output")) {
        return 1;
    }
    if (!check(read_text("compface.xbm", xbm, sizeof(xbm)),
               "reads XBM output")) {
        return 1;
    }
    if (!check(strstr(xbm, "#define noname_width 48") != NULL &&
                   strstr(xbm, "#define noname_height 48") != NULL,
               "XBM output declares 48x48 dimensions")) {
        return 1;
    }
    if (!check(count_hex_values(xbm) == 288,
               "XBM output contains 288 pixel bytes")) {
        return 1;
    }

    printf("libcompface consumer test: %d assertions passed\n", checks);
    return 0;
}
