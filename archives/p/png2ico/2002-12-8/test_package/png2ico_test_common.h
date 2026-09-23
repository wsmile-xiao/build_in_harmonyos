#ifndef PNG2ICO_TEST_COMMON_H
#define PNG2ICO_TEST_COMMON_H

#define _XOPEN_SOURCE 700

#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#if defined(_WIN32)
#include <direct.h>
#define mkdir(path, mode) _mkdir(path)
#endif

static const unsigned char png_8x8_rgb[] = {
    0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a,
    0x00, 0x00, 0x00, 0x0d, 0x49, 0x48, 0x44, 0x52,
    0x00, 0x00, 0x00, 0x08, 0x00, 0x00, 0x00, 0x08,
    0x08, 0x02, 0x00, 0x00, 0x00, 0x4b, 0x6d, 0x29,
    0xdc, 0x00, 0x00, 0x00, 0x11, 0x49, 0x44, 0x41,
    0x54, 0x78, 0xda, 0x63, 0xf8, 0xcf, 0xc0, 0x80,
    0x15, 0x31, 0x0c, 0x2d, 0x09, 0x00, 0x28, 0xff,
    0x3f, 0xc1, 0xce, 0x77, 0xc8, 0x4f, 0x00, 0x00,
    0x00, 0x00, 0x49, 0x45, 0x4e, 0x44, 0xae, 0x42,
    0x60, 0x82,
};

static int append_text(char *buffer, size_t capacity, size_t *length,
                       const char *text)
{
    size_t text_length = strlen(text);
    if (*length + text_length + 1 > capacity)
        return 1;
    memcpy(buffer + *length, text, text_length);
    *length += text_length;
    buffer[*length] = '\0';
    return 0;
}

static int append_quoted(char *buffer, size_t capacity, size_t *length,
                         const char *value)
{
    const char *cursor;
    if (append_text(buffer, capacity, length, "'"))
        return 1;
    for (cursor = value; *cursor != '\0'; ++cursor) {
        if (*cursor == '\'' && append_text(buffer, capacity, length, "'\\''"))
            return 1;
        if (*cursor != '\'' && append_text(buffer, capacity, length,
                                             (char[]){*cursor, '\0'}))
            return 1;
    }
    return append_text(buffer, capacity, length, "'");
}

static int write_png(const char *path)
{
    FILE *file = fopen(path, "wb");
    if (file == NULL)
        return 1;
    if (fwrite(png_8x8_rgb, 1, sizeof(png_8x8_rgb), file) !=
        sizeof(png_8x8_rgb)) {
        fclose(file);
        return 1;
    }
    return fclose(file) != 0;
}

static unsigned int read_le16(const unsigned char *data)
{
    return (unsigned int)data[0] | ((unsigned int)data[1] << 8);
}

static unsigned long read_le32(const unsigned char *data)
{
    return (unsigned long)data[0] |
           ((unsigned long)data[1] << 8) |
           ((unsigned long)data[2] << 16) |
           ((unsigned long)data[3] << 24);
}

static int verify_ico(const char *path, unsigned int expected_count,
                      unsigned int expected_colors)
{
    unsigned char header[22];
    unsigned long file_size;
    unsigned int count;
    FILE *file = fopen(path, "rb");
    if (file == NULL) {
        fprintf(stderr, "FAIL: ICO output cannot be opened: %s\n", path);
        return 1;
    }
    if (fseek(file, 0, SEEK_END) != 0 || (file_size = (unsigned long)ftell(file)) <
        sizeof(header) || fseek(file, 0, SEEK_SET) != 0 ||
        fread(header, 1, sizeof(header), file) != sizeof(header)) {
        fprintf(stderr, "FAIL: ICO output is truncated: %s\n", path);
        fclose(file);
        return 1;
    }
    fclose(file);

    if (read_le16(header) != 0 || read_le16(header + 2) != 1) {
        fprintf(stderr, "FAIL: invalid ICO header\n");
        return 1;
    }
    count = read_le16(header + 4);
    if (count != expected_count) {
        fprintf(stderr, "FAIL: expected %u ICO images, got %u\n",
                expected_count, count);
        return 1;
    }
    if (header[6] != 8 || header[7] != 8 || header[8] != expected_colors) {
        fprintf(stderr, "FAIL: unexpected ICO directory dimensions/colors\n");
        return 1;
    }
    if (read_le32(header + 18) + read_le32(header + 14) > file_size) {
        fprintf(stderr, "FAIL: ICO directory points beyond output\n");
        return 1;
    }
    return 0;
}

static int run_png2ico_case(const char *binary, const char *root,
                            const char *directory_prefix)
{
    char directory[PATH_MAX];
    char input_one[PATH_MAX];
    char input_two[PATH_MAX];
    char output[PATH_MAX];
    char command[PATH_MAX * 5];
    size_t command_length = 0;
    int written;
    unsigned int attempt;
    int return_code;

    written = -1;
    for (attempt = 0; attempt < 100 && written < 0; ++attempt) {
        int candidate = snprintf(
            directory, sizeof(directory), "%s/%s-%lu-%u", root,
            directory_prefix, (unsigned long)getpid(), attempt);
        if (candidate >= 0 && (size_t)candidate < sizeof(directory) &&
            mkdir(directory, 0700) == 0)
            written = candidate;
    }
    if (written < 0) {
        fprintf(stderr, "FAIL: cannot create private test directory under %s\n",
                root);
        return 1;
    }
    written = snprintf(input_one, sizeof(input_one), "%s/input-one.png",
                       directory);
    if (written < 0 || (size_t)written >= sizeof(input_one))
        return 1;
    written = snprintf(input_two, sizeof(input_two), "%s/input-two.png",
                       directory);
    if (written < 0 || (size_t)written >= sizeof(input_two))
        return 1;
    written = snprintf(output, sizeof(output), "%s/output.ico", directory);
    if (written < 0 || (size_t)written >= sizeof(output))
        return 1;

    if (write_png(input_one) != 0 || write_png(input_two) != 0) {
        fprintf(stderr, "FAIL: cannot write PNG fixture\n");
        return 1;
    }

    command[0] = '\0';
    if (append_quoted(command, sizeof(command), &command_length, binary) ||
        append_text(command, sizeof(command), &command_length, " ") ||
        append_quoted(command, sizeof(command), &command_length, output) ||
        append_text(command, sizeof(command), &command_length,
                    " --colors 16 ") ||
        append_quoted(command, sizeof(command), &command_length, input_one) ||
        append_text(command, sizeof(command), &command_length, " ") ||
        append_quoted(command, sizeof(command), &command_length, input_two)) {
        fprintf(stderr, "FAIL: converter command is too long\n");
        return 1;
    }

    return_code = system(command);
    if (return_code != 0) {
        fprintf(stderr, "FAIL: png2ico execution failed\n");
        return 1;
    }
    if (verify_ico(output, 2, 16) != 0)
        return 1;

    unlink(input_one);
    unlink(input_two);
    unlink(output);
    rmdir(directory);
    return 0;
}

#endif
