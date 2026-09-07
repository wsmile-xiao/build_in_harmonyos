/* libarchive test_package — real API round-trip verification (R34).
 *
 * Writes a tar.gz archive containing two files via archive_write_* API
 * (archive_write_open_filename / archive_write_header / archive_write_data),
 * then reads it back via archive_read_* API (archive_read_open_filename /
 * archive_read_next_header / archive_read_data) and asserts the contents
 * match byte-for-byte. Also verifies gzip/zlib filter support is compiled in.
 */
#include <archive.h>
#include <archive_entry.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static const char *archive_path = "roundtrip.tar.gz";

/* Last live archive handle for diagnostics; may be NULL early in main().
 * archive_error_string(a) dereferences a without NULL guard (archive.c),
 * so never call it with NULL — fall back to a static hint instead. */
static struct archive *g_last_archive = NULL;

static const char *content_a =
    "libarchive OHOS round-trip test payload A\n"
    "HarmonyOS PC aarch64 musl clang\n";
static const char *content_b =
    "libarchive OHOS round-trip test payload B\n"
    "tar.gz write then read verify\n";

static int fail(const char *msg, int r)
{
    const char *err = g_last_archive ? archive_error_string(g_last_archive) : NULL;
    fprintf(stderr, "FAIL: %s (r=%d, last_error=%s)\n", msg, r, err ? err : "()");
    return 1;
}

int main(void)
{
    int r;
    printf("libarchive version: %s (number %d)\n",
           archive_version_string(), (int)archive_version_number());

    /* ---------- write a tar.gz with two entries ---------- */
    struct archive *a = archive_write_new();
    if (!a) return fail("archive_write_new", -1);
    g_last_archive = a;
    r = archive_write_set_format_pax_restricted(a);
    if (r != ARCHIVE_OK) return fail("archive_write_set_format_pax_restricted", r);
    r = archive_write_add_filter_gzip(a);
    if (r != ARCHIVE_OK) return fail("archive_write_add_filter_gzip (zlib filter compiled in?)", r);
    r = archive_write_open_filename(a, archive_path);
    if (r != ARCHIVE_OK) return fail("archive_write_open_filename", r);

    const char *names[2] = {"payload_a.txt", "dir/payload_b.txt"};
    const char *datas[2] = {content_a, content_b};
    for (int i = 0; i < 2; i++) {
        struct archive_entry *entry = archive_entry_new();
        archive_entry_set_pathname(entry, names[i]);
        archive_entry_set_size(entry, strlen(datas[i]));
        archive_entry_set_filetype(entry, AE_IFREG);
        archive_entry_set_perm(entry, 0644);
        r = archive_write_header(a, entry);
        if (r != ARCHIVE_OK) return fail("archive_write_header", r);
        size_t written = archive_write_data(a, datas[i], strlen(datas[i]));
        if (written != strlen(datas[i])) {
            fprintf(stderr, "FAIL: archive_write_data wrote %zu of %zu\n",
                    written, strlen(datas[i]));
            return 1;
        }
        archive_entry_free(entry);
    }
    r = archive_write_close(a);
    if (r != ARCHIVE_OK) return fail("archive_write_close", r);
    r = archive_write_free(a);
    if (r != ARCHIVE_OK) return fail("archive_write_free", r);
    printf("write: %s written (2 entries, gzip filter)\n", archive_path);

    /* ---------- read it back and verify ---------- */
    struct archive *ar = archive_read_new();
    if (!ar) return fail("archive_read_new", -1);
    g_last_archive = ar;
    r = archive_read_support_format_tar(ar);
    if (r != ARCHIVE_OK) return fail("archive_read_support_format_tar", r);
    r = archive_read_support_filter_gzip(ar);
    if (r != ARCHIVE_OK) return fail("archive_read_support_filter_gzip", r);
    r = archive_read_open_filename(ar, archive_path, 10240);
    if (r != ARCHIVE_OK) return fail("archive_read_open_filename", r);

    int checked = 0;
    for (int i = 0; i < 2; i++) {
        struct archive_entry *entry = NULL;
        r = archive_read_next_header(ar, &entry);
        if (r != ARCHIVE_OK) return fail("archive_read_next_header", r);
        const char *name = archive_entry_pathname(entry);
        if (strcmp(name, names[i]) != 0) {
            fprintf(stderr, "FAIL: entry %d name '%s' != '%s'\n", i, name, names[i]);
            return 1;
        }
        la_int64_t esize = archive_entry_size(entry);
        if (esize != (la_int64_t)strlen(datas[i])) {
            fprintf(stderr, "FAIL: entry %d size %lld != %zu\n", i, (long long)esize, strlen(datas[i]));
            return 1;
        }
        char buf[512];
        memset(buf, 0, sizeof(buf));
        la_ssize_t nread = archive_read_data(ar, buf, sizeof(buf) - 1);
        if (nread != (la_ssize_t)strlen(datas[i])) {
            fprintf(stderr, "FAIL: entry %d read %lld of %zu\n", i, (long long)nread, strlen(datas[i]));
            return 1;
        }
        if (memcmp(buf, datas[i], nread) != 0) {
            fprintf(stderr, "FAIL: entry %d content mismatch\n", i);
            return 1;
        }
        checked++;
        printf("read: %s -> %lld bytes, content matches\n", name, (long long)nread);
    }
    struct archive_entry *eof = NULL;
    r = archive_read_next_header(ar, &eof);
    if (r != ARCHIVE_EOF) return fail("expected ARCHIVE_EOF after last entry", r);
    r = archive_read_free(ar);
    if (r != ARCHIVE_OK) return fail("archive_read_free", r);

    if (checked != 2) {
        fprintf(stderr, "FAIL: checked %d entries, expected 2\n", checked);
        return 1;
    }
    unlink(archive_path);
    printf("ALL PASS: libarchive tar.gz write/read round-trip verified (2 entries)\n");
    return 0;
}
