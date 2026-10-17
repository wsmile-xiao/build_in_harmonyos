/*
 * test_libarchive_api.c — consumer test for the libarchive shipped with
 * libarchive-tools 3.8.8.
 *
 * Writes a one-file ustar archive fully in memory with the archive_write
 * API, then reads it back with the archive_read API and asserts pathname,
 * size and content. Pure memory I/O: independent of filesystem quirks.
 */
#include <stdio.h>
#include <string.h>

#include <archive.h>
#include <archive_entry.h>

static const char payload[] = "Hello, OHOS!\n";

int main(void) {
    struct archive *w = NULL;
    struct archive *r = NULL;
    struct archive_entry *entry = NULL;
    static char membuf[32768];
    size_t used = 0;
    char readback[64];
    la_ssize_t n = 0;
    int rc = 1;

    w = archive_write_new();
    if (w == NULL) {
        fprintf(stderr, "archive_write_new failed\n");
        return 1;
    }
    if (archive_write_add_filter_none(w) != ARCHIVE_OK) {
        fprintf(stderr, "add_filter_none failed: %s\n", archive_error_string(w));
        goto done;
    }
    if (archive_write_set_format_ustar(w) != ARCHIVE_OK) {
        fprintf(stderr, "set_format_ustar failed: %s\n", archive_error_string(w));
        goto done;
    }
    if (archive_write_open_memory(w, membuf, sizeof(membuf), &used) != ARCHIVE_OK) {
        fprintf(stderr, "open_memory(write) failed: %s\n", archive_error_string(w));
        goto done;
    }
    entry = archive_entry_new();
    if (entry == NULL) {
        fprintf(stderr, "archive_entry_new failed\n");
        goto done;
    }
    archive_entry_set_pathname(entry, "hello.txt");
    archive_entry_set_size(entry, (la_int64_t)(sizeof(payload) - 1));
    archive_entry_set_filetype(entry, AE_IFREG);
    archive_entry_set_perm(entry, 0644);
    if (archive_write_header(w, entry) != ARCHIVE_OK) {
        fprintf(stderr, "write_header failed: %s\n", archive_error_string(w));
        goto done;
    }
    if (archive_write_data(w, payload, sizeof(payload) - 1) < 0) {
        fprintf(stderr, "write_data failed: %s\n", archive_error_string(w));
        goto done;
    }
    if (archive_write_finish_entry(w) != ARCHIVE_OK) {
        fprintf(stderr, "finish_entry failed: %s\n", archive_error_string(w));
        goto done;
    }
    if (archive_write_close(w) != ARCHIVE_OK) {
        fprintf(stderr, "write_close failed: %s\n", archive_error_string(w));
        goto done;
    }
    if (used == 0) {
        fprintf(stderr, "writer produced zero bytes\n");
        goto done;
    }
    printf("write: %lu bytes of ustar in memory\n", (unsigned long)used);

    r = archive_read_new();
    if (r == NULL) {
        fprintf(stderr, "archive_read_new failed\n");
        goto done;
    }
    if (archive_read_support_filter_all(r) != ARCHIVE_OK) {
        fprintf(stderr, "support_filter_all failed: %s\n", archive_error_string(r));
        goto done;
    }
    if (archive_read_support_format_all(r) != ARCHIVE_OK) {
        fprintf(stderr, "support_format_all failed: %s\n", archive_error_string(r));
        goto done;
    }
    if (archive_read_open_memory(r, membuf, used) != ARCHIVE_OK) {
        fprintf(stderr, "open_memory(read) failed: %s\n", archive_error_string(r));
        goto done;
    }
    if (archive_read_next_header(r, &entry) != ARCHIVE_OK) {
        fprintf(stderr, "next_header failed: %s\n", archive_error_string(r));
        goto done;
    }
    if (strcmp(archive_entry_pathname(entry), "hello.txt") != 0) {
        fprintf(stderr, "pathname mismatch: %s\n", archive_entry_pathname(entry));
        goto done;
    }
    if (archive_entry_size(entry) != (la_int64_t)(sizeof(payload) - 1)) {
        fprintf(stderr, "size mismatch: %lld\n", (long long)archive_entry_size(entry));
        goto done;
    }
    n = archive_read_data(r, readback, sizeof(payload) - 1);
    if (n != (la_ssize_t)(sizeof(payload) - 1)) {
        fprintf(stderr, "short read: %lld\n", (long long)n);
        goto done;
    }
    if (memcmp(readback, payload, sizeof(payload) - 1) != 0) {
        fprintf(stderr, "content mismatch\n");
        goto done;
    }
    printf("read: hello.txt size=%lld content identical\n",
           (long long)archive_entry_size(entry));
    printf("test libarchive-tools 3.8.8 api: OK\n");
    rc = 0;

done:
    if (entry != NULL && r == NULL) {
        archive_entry_free(entry);
    }
    if (w != NULL) {
        archive_write_free(w);
    }
    if (r != NULL) {
        archive_read_free(r);
    }
    return rc;
}
