/* test_arc.c — consumer test for libarc 2.0.2.
 *
 * Exercises the real library API (not an include-only test):
 *   1. version      — ARC_LIB_VERSION macro + arc_lib_version symbol.
 *   2. archive-type — get_archive_type() extension mapping.
 *   3. wildmat      — arc_wildmat() / arc_case_wildmat() matching.
 *   4. roundtrip    — arc_compress() -> arc_decompress() byte-exact.
 *   5. tar-read     — hand-crafted ustar archive read back through
 *                     url_arc_open(), the same path the arccat tool uses
 *                     (registers the file/dir URL modules first).
 *
 * Each passing group prints one "CHECK-OK: <name>" line; the test
 * conanfile counts these lines for the HMBS_TEST_PACKAGE_RESULT
 * machine-evidence marker (exit-0-alone is not proof: 5 CHECK-OK
 * lines are required for a pass).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libarc/arc.h>

extern char *arc_lib_version;
extern struct URL_module URL_module_file;
extern struct URL_module URL_module_dir;

static int failures = 0;

#define CHECK_OK(name) \
    do { printf("CHECK-OK: %s\n", name); fflush(stdout); } while (0)

#define REQUIRE(cond, msg) \
    do { \
        if (!(cond)) { \
            fprintf(stderr, "FAIL: %s\n", msg); \
            failures++; \
            return 0; \
        } \
    } while (0)

/* 1. Library version reporting. */
static int test_version(void)
{
    REQUIRE(strcmp(ARC_LIB_VERSION, "2.0.2") == 0,
            "ARC_LIB_VERSION is not 2.0.2");
    REQUIRE(arc_lib_version != NULL
            && strcmp(arc_lib_version, "2.0.2") == 0,
            "arc_lib_version symbol mismatch");
    CHECK_OK("version");
    return 1;
}

/* 2. Archive type detection is pure extension/prefix matching. */
static int test_archive_type(void)
{
    REQUIRE(get_archive_type("a.tar") == ARCHIVE_TAR, "tar not detected");
    REQUIRE(get_archive_type("a.tar.gz") == ARCHIVE_TGZ, "tar.gz not detected");
    REQUIRE(get_archive_type("a.tgz") == ARCHIVE_TGZ, "tgz not detected");
    REQUIRE(get_archive_type("a.zip") == ARCHIVE_ZIP, "zip not detected");
    REQUIRE(get_archive_type("a.lzh") == ARCHIVE_LZH, "lzh not detected");
    REQUIRE(get_archive_type("a.lha") == ARCHIVE_LZH, "lha not detected");
    REQUIRE(get_archive_type("mail:mbox") == ARCHIVE_MIME, "mail: not detected");
    CHECK_OK("archive-type");
    return 1;
}

/* 3. Shell-style wildcard matching used for entry selection. */
static int test_wildmat(void)
{
    REQUIRE(arc_wildmat("hello.txt", "*.txt") == 1, "*.txt should match");
    REQUIRE(arc_wildmat("hello.txt", "*.c") == 0, "*.c should not match");
    REQUIRE(arc_case_wildmat("HELLO.TXT", "*.txt") == 1,
            "case-insensitive match failed");
    REQUIRE(arc_case_wildmat("HELLO.TXT", "*.c") == 0,
            "case-insensitive non-match failed");
    CHECK_OK("wildmat");
    return 1;
}

/* 4. Deflate compress -> decompress round-trip must be byte-exact.
 * NOTE: arc_compress/arc_decompress take ownership of the input
 * buffer ONLY when they produce no output (they free(buff) and
 * return NULL). On success the caller frees both buffers. */
static int test_roundtrip(void)
{
    static const char payload[] =
        "The quick brown fox jumps over the lazy dog. "
        "0123456789 abcdefghijklmnopqrstuvwxyz.";
    long inlen = (long)sizeof(payload) - 1;
    char *inbuf = (char *)malloc((size_t)inlen);
    long csize = 0;
    void *compressed;
    long dsize = 0;
    void *plain;

    REQUIRE(inbuf != NULL, "malloc failed");
    memcpy(inbuf, payload, (size_t)inlen);

    compressed = arc_compress(inbuf, inlen, ARC_DEFLATE_LEVEL, &csize);
    /* On NULL the library already freed inbuf; do not touch it. */
    REQUIRE(compressed != NULL && csize > 0, "arc_compress failed");

    plain = arc_decompress(compressed, csize, &dsize);
    /* On NULL the library already freed compressed; do not touch it. */
    REQUIRE(plain != NULL, "arc_decompress failed");
    REQUIRE(dsize == inlen && memcmp(plain, payload, (size_t)inlen) == 0,
            "round-trip bytes differ");

    free(inbuf);
    free(compressed);
    free(plain);
    CHECK_OK("compress-roundtrip");
    return 1;
}

static const char *writable_dir(void)
{
    const char *d = getenv("TMPDIR");
    if (d == NULL || *d == '\0')
        d = getenv("TMP");
    if (d == NULL || *d == '\0')
        d = getenv("TEMP");
    if (d == NULL || *d == '\0')
        d = ".";
    return d;
}

/* Build one minimal ustar block set: 512-byte header + 512-byte data
 * + two zero blocks. Checksum covers the header with the chksum
 * field counted as blanks (tar_checksum accepts both signed and
 * unsigned sums, so this is ARM-safe). */
static void make_ustar(unsigned char *blk, const char *name,
                       const void *data, long size)
{
    char tmp[16];
    unsigned sum = 0;
    int i;

    memset(blk, 0, 1536);
    memcpy(blk, name, strlen(name));
    memcpy(blk + 100, "0000644", 7);
    memcpy(blk + 108, "0000000", 7);
    memcpy(blk + 116, "0000000", 7);
    snprintf(tmp, sizeof(tmp), "%011lo", (unsigned long)size);
    memcpy(blk + 124, tmp, 11);
    memcpy(blk + 136, "00000000000", 11);
    blk[156] = '0';
    memcpy(blk + 257, "ustar", 5);
    memcpy(blk + 263, "00", 2);
    memset(blk + 148, ' ', 8);
    for (i = 0; i < 512; i++)
        sum += blk[i];
    snprintf(tmp, sizeof(tmp), "%06o", sum);
    memcpy(blk + 148, tmp, 6);
    blk[154] = '\0';
    blk[155] = ' ';
    memcpy(blk + 512, data, (size_t)size);
}

/* 5. End-to-end: write the ustar fixture, read the entry back with
 * url_arc_open("test.tar#hi.txt") exactly like arccat does. */
static int test_tar_read(void)
{
    static const char content[] = "hello libarc\n";
    unsigned char blk[1536];
    char path[1024];
    char spec[1100];
    FILE *f;
    URL url;
    char out[64];
    long n = 0;
    int c;

    snprintf(path, sizeof(path), "%s/test_libarc.tar", writable_dir());
    make_ustar(blk, "hi.txt", content, (long)sizeof(content) - 1);

    f = fopen(path, "wb");
    REQUIRE(f != NULL, "cannot create tar fixture");
    REQUIRE(fwrite(blk, 1, sizeof(blk), f) == sizeof(blk),
            "cannot write tar fixture");
    fclose(f);

    url_add_modules(&URL_module_file, &URL_module_dir, NULL);

    snprintf(spec, sizeof(spec), "%s#hi.txt", path);
    url = url_arc_open(spec);
    REQUIRE(url != NULL, "url_arc_open failed for tar entry");

    while ((c = url_getc(url)) != EOF && n < (long)sizeof(out))
        out[n++] = (char)c;
    REQUIRE(n == (long)sizeof(content) - 1
            && memcmp(out, content, (size_t)n) == 0,
            "tar entry content mismatch");
    url_close(url);

    free_archive_files();
    remove(path);
    CHECK_OK("tar-read");
    return 1;
}

int main(void)
{
    test_version();
    test_archive_type();
    test_wildmat();
    test_roundtrip();
    test_tar_read();

    if (failures != 0) {
        fprintf(stderr, "test_arc: %d group(s) FAILED\n", failures);
        return 1;
    }
    printf("test_arc: all 5 groups passed\n");
    return 0;
}
