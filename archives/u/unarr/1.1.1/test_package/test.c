// Consumer test for unarr (test_package).
//
// Builds a minimal ustar archive in memory, opens it through the public API
// (ar_open_memory/ar_open_tar_archive), parses the entry and decompresses it, then
// asserts the entry metadata and payload. Negative cases assert that non-archive
// input is rejected.

#include <unarr.h>

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

static int failures = 0;

static void check(bool cond, const char *what) {
    if (cond) {
        printf("ok  : %s\n", what);
    } else {
        printf("FAIL: %s\n", what);
        ++failures;
    }
}

// Minimal ustar archive: one regular entry "hello.txt" with a known payload.
static size_t build_tar(unsigned char *buf, size_t cap) {
    const char *name = "hello.txt";
    const char *data = "hello unarr\n";
    const size_t dlen = strlen(data);
    unsigned i;
    unsigned sum = 0;

    if (cap < 1536)
        return 0;
    memset(buf, 0, 1536);
    memcpy(buf, name, strlen(name));
    snprintf((char *)buf + 100, 8, "%07o", 0644);                 // mode
    snprintf((char *)buf + 108, 8, "%07o", 0);                    // uid
    snprintf((char *)buf + 116, 8, "%07o", 0);                    // gid
    snprintf((char *)buf + 124, 12, "%011o", (unsigned)dlen);     // size
    snprintf((char *)buf + 136, 12, "%011o", 0);                  // mtime
    memset(buf + 148, ' ', 8);                                    // checksum field
    buf[156] = '0';                                               // regular file
    memcpy(buf + 257, "ustar", 5);

    for (i = 0; i < 512; ++i)
        sum += buf[i];
    snprintf((char *)buf + 148, 7, "%06o", sum);
    buf[154] = '\0';
    buf[155] = ' ';

    memcpy(buf + 512, data, dlen);
    return 1024;  // header + one data block; the rest is the EOF padding
}

int main(void) {
    static unsigned char tar[1536];
    const size_t tar_len = build_tar(tar, sizeof tar);

    check(tar_len == 1024, "test fixture built");

    ar_stream *stream = ar_open_memory(tar, tar_len);
    check(stream != NULL, "ar_open_memory() returns a stream");

    if (stream) {
        ar_archive *ar = ar_open_tar_archive(stream);
        check(ar != NULL, "ar_open_tar_archive() accepts the fixture");

        if (ar) {
            check(ar_parse_entry(ar) == true, "ar_parse_entry() finds the entry");
            check(ar_entry_get_name(ar) != NULL &&
                      strcmp(ar_entry_get_name(ar), "hello.txt") == 0,
                  "entry name is hello.txt");
            check(ar_entry_get_size(ar) == 12, "entry size is 12 bytes");

            char out[64];
            memset(out, 0, sizeof out);
            check(ar_entry_uncompress(ar, out, 12) == true,
                  "ar_entry_uncompress() succeeds");
            check(memcmp(out, "hello unarr\n", 12) == 0,
                  "decompressed payload matches the input");
            check(ar_parse_entry(ar) == false, "archive has no second entry");
            ar_close_archive(ar);
        }
        ar_close(stream);
    }

    // Negative path: zero-filled data must not be accepted as a tar archive.
    {
        static const unsigned char junk[64] = {0};
        ar_stream *s2 = ar_open_memory(junk, sizeof junk);
        check(s2 != NULL, "ar_open_memory() accepts arbitrary data");
        if (s2) {
            ar_archive *a2 = ar_open_tar_archive(s2);
            check(a2 == NULL, "garbage is rejected by ar_open_tar_archive()");
            if (a2)
                ar_close_archive(a2);
            ar_close(s2);
        }
    }

    if (failures == 0) {
        printf("unarr consumer test: all checks passed\n");
        return 0;
    }
    printf("unarr consumer test: %d check(s) FAILED\n", failures);
    return 1;
}
