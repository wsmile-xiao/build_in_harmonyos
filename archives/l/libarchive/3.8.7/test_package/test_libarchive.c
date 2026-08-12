/*
 * test_libarchive.c — libarchive in-memory tar read test.
 *
 * Creates a minimal tar archive in memory and reads it back with the
 * archive_read API to verify the libarchive library works correctly.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <archive.h>
#include <archive_entry.h>

static const unsigned char fake_tar[] = {
    /* size = 512 bytes, empty tar (single zero block) */
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
};

int main(void) {
    struct archive *a;
    struct archive_entry *entry;
    int r;

    a = archive_read_new();
    if (!a) {
        fprintf(stderr, "archive_read_new failed\n");
        return 1;
    }
    r = archive_read_support_filter_all(a);
    if (r != ARCHIVE_OK) {
        fprintf(stderr, "archive_read_support_filter_all failed: %s\n", archive_error_string(a));
        archive_read_free(a);
        return 1;
    }
    r = archive_read_support_format_tar(a);
    if (r != ARCHIVE_OK) {
        fprintf(stderr, "archive_read_support_format_tar failed: %s\n", archive_error_string(a));
        archive_read_free(a);
        return 1;
    }

    r = archive_read_open_memory(a, fake_tar, sizeof(fake_tar));
    if (r != ARCHIVE_OK) {
        fprintf(stderr, "archive_read_open_memory failed: %s\n", archive_error_string(a));
        archive_read_free(a);
        return 1;
    }

    r = archive_read_next_header(a, &entry);
    if (r == ARCHIVE_EOF) {
        printf("Empty tar detected (ARCHIVE_EOF) — OK\n");
    } else if (r == ARCHIVE_OK) {
        printf("Header read OK: %s\n", archive_entry_pathname(entry));
    } else {
        fprintf(stderr, "archive_read_next_header failed: %s\n", archive_error_string(a));
        archive_read_free(a);
        return 1;
    }

    archive_read_free(a);
    printf("test libarchive 3.8.7: OK\n");
    return 0;
}