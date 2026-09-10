/* Consumer of the actual decompressed PARI modular-polynomial data. */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int check(FILE *input, unsigned level, uint64_t expected_size, uint32_t expected_crc)
{
    unsigned char buffer[65536];
    uint32_t table[256];
    uint32_t crc = UINT32_MAX;
    uint64_t count = 0;
    char expected_prefix[40];
    size_t size;
    for (unsigned i = 0; i < 256; ++i) {
        uint32_t value = i;
        for (unsigned j = 0; j < 8; ++j)
            value = (value >> 1) ^ ((value & 1) ? UINT32_C(0xedb88320) : 0);
        table[i] = value;
    }
    snprintf(expected_prefix, sizeof(expected_prefix), "[%u, \"A\", [1,", level);
    while ((size = fread(buffer, 1, sizeof(buffer), input)) != 0) {
        if (count == 0 && (size < strlen(expected_prefix)
                || memcmp(buffer, expected_prefix, strlen(expected_prefix)) != 0)) {
            fprintf(stderr, "Unexpected polynomial header\n");
            return 1;
        }
        for (size_t i = 0; i < size; ++i)
            crc = table[(crc ^ buffer[i]) & 255] ^ (crc >> 8);
        count += size;
    }
    if (ferror(input) || count != expected_size || (crc ^ UINT32_MAX) != expected_crc) {
        fprintf(stderr, "Polynomial %u: size/CRC mismatch (%" PRIu64 ")\n", level, count);
        return 1;
    }
    return 0;
}

static int sandbox(const char *source, uint64_t size, uint32_t crc)
{
#if defined(__OHOS__)
    const char *temporary = getenv("TMPDIR");
    char directory[4096], first[4096] = {0}, moved[4096] = {0};
    unsigned char buffer[65536];
    FILE *input = NULL, *output = NULL;
    size_t length;
    int result = 1;
    if (!temporary || temporary[0] != '/') {
        fprintf(stderr, "HarmonyOS test requires an absolute writable TMPDIR\n");
        return 1;
    }
    if (snprintf(directory, sizeof(directory), "%s/pari-seadata-XXXXXX", temporary)
            >= (int)sizeof(directory) || !mkdtemp(directory)) {
        perror("mkdtemp");
        return 1;
    }
    if (snprintf(first, sizeof(first), "%s/sea 503.data", directory) >= (int)sizeof(first)
            || snprintf(moved, sizeof(moved), "%s/relocated 503.data", directory) >= (int)sizeof(moved))
        goto cleanup;
    input = fopen(source, "rb");
    output = fopen(first, "wb");
    if (!input || !output)
        goto cleanup;
    while ((length = fread(buffer, 1, sizeof(buffer), input)) != 0)
        if (fwrite(buffer, 1, length, output) != length)
            goto cleanup;
    if (ferror(input))
        goto cleanup;
    fclose(input);
    input = NULL;
    if (fclose(output) != 0) {
        output = NULL;
        goto cleanup;
    }
    output = NULL;
    if (rename(first, moved) != 0)
        goto cleanup;
    input = fopen(moved, "rb");
    if (!input || check(input, 503, size, crc) != 0)
        goto cleanup;
    result = 0;
    puts("[ok] HarmonyOS sandbox relocation: writable TMPDIR, space path, rename, full data CRC");
cleanup:
    if (input) fclose(input);
    if (output) fclose(output);
    if (first[0]) unlink(first);
    if (moved[0]) unlink(moved);
    rmdir(directory);
    return result;
#else
    (void)source; (void)size; (void)crc;
    fputs("HarmonyOS sandbox test requires an OHOS-compiled consumer\n", stderr);
    return 1;
#endif
}

int main(int argc, char **argv)
{
    if (argc == 5 && strcmp(argv[1], "--sandbox") == 0)
        return sandbox(argv[2], strtoull(argv[3], NULL, 10), (uint32_t)strtoul(argv[4], NULL, 16));
    if (argc != 4) {
        fprintf(stderr, "usage: test_seadata LEVEL BYTES CRC32 < polynomial\n");
        return 2;
    }
    unsigned level = (unsigned)strtoul(argv[1], NULL, 10);
    if (check(stdin, level, strtoull(argv[2], NULL, 10), (uint32_t)strtoul(argv[3], NULL, 16)) != 0)
        return 1;
    printf("[ok] target polynomial %u\n", level);
    return 0;
}
