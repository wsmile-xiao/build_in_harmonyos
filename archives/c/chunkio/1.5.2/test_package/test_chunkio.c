/*
 * test_chunkio.c — consumer-view test for the packaged chunkio 1.5.2.
 *
 * Compiled by test_package/CMakeLists.txt against the *installed* package
 * (find_package(chunkio)), i.e. it only sees what a real downstream
 * consumer sees: the public headers under include/chunkio and the packaged
 * archives libchunkio-static.a + libcio-crc32.a.
 *
 * Covers both storage backends shipped by the recipe:
 *   - memfs (memory only), and
 *   - fs (memory mapped files), which is the path that exercises the
 *     OHOS fallocate()/posix_fallocate() -> ftruncate() fallback from
 *     patch 0004 on a real file system.
 *
 * Exit code 0 = every check passed, 1 = at least one failure.
 */

#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include <chunkio/chunkio.h>
#include <chunkio/cio_chunk.h>
#include <chunkio/cio_stream.h>
#include <chunkio/cio_version.h>

#define PAYLOAD_SIZE 4096
#define FS_ROOT      "cio-tp-root/"

static int g_checks;
static int g_failures;

static void check(int cond, const char *what)
{
    g_checks++;
    printf("%s: %s\n", cond ? "PASS" : "FAIL", what);
    if (!cond) {
        g_failures++;
        fprintf(stderr, "FAIL: %s\n", what);
    }
}

/* keep chunkio quiet but prove the log callback path links */
static int log_cb(struct cio_ctx *ctx, int level, const char *file, int line,
                  char *str)
{
    (void) ctx;
    (void) level;
    (void) file;
    (void) line;
    (void) str;
    return 0;
}

static int dir_entries(const char *path)
{
    DIR *dir;
    struct dirent *ent;
    int count = 0;

    dir = opendir(path);
    if (dir == NULL) {
        return -1;
    }
    while ((ent = readdir(dir)) != NULL) {
        if (strcmp(ent->d_name, ".") == 0 || strcmp(ent->d_name, "..") == 0) {
            continue;
        }
        count++;
    }
    closedir(dir);
    return count;
}

int main(void)
{
    static char payload[PAYLOAD_SIZE];
    int err = 0;
    char *buf = NULL;
    size_t size = 0;
    ssize_t content_size;
    struct cio_options opts;
    struct cio_ctx *ctx;
    struct cio_stream *stream;
    struct cio_chunk *chunk;

    memset(payload, 'A', sizeof(payload));

    /* ── packaged version fingerprints ─────────────────────────────── */
    check(strcmp(CIO_VERSION_STR, "1.5.2") == 0,
          "installed cio_version.h self-reports 1.5.2");
    check(cio_version() != NULL && strcmp(cio_version(), "1.5.2") == 0,
          "linked library self-reports 1.5.2 through cio_version()");

    /* ── memfs backend: write, read back, compare ──────────────────── */
    cio_options_init(&opts);
    opts.log_level = CIO_LOG_INFO;
    opts.log_cb = log_cb;
    opts.flags = CIO_CHECKSUM;

    ctx = cio_create(&opts);
    check(ctx != NULL, "cio_create() without root_path (memory context)");
    if (ctx == NULL) {
        goto done;
    }

    stream = cio_stream_create(ctx, "tp-mem", CIO_STORE_MEM);
    check(stream != NULL, "cio_stream_create(CIO_STORE_MEM)");

    chunk = cio_chunk_open(ctx, stream, "blob", CIO_OPEN, PAYLOAD_SIZE, &err);
    check(chunk != NULL, "cio_chunk_open()");

    if (chunk != NULL) {
        check(cio_chunk_write(chunk, payload, PAYLOAD_SIZE) == CIO_OK,
              "cio_chunk_write() accepts 4096 bytes");

        content_size = cio_chunk_get_content_size(chunk);
        check(content_size == (ssize_t) PAYLOAD_SIZE,
              "content size equals bytes written");

        check(cio_chunk_get_content(chunk, &buf, &size) == CIO_OK,
              "cio_chunk_get_content() succeeds");
        check(size == (ssize_t) PAYLOAD_SIZE && buf != NULL
                  && memcmp(buf, payload, PAYLOAD_SIZE) == 0,
              "in-memory content matches what was written");

        check(cio_chunk_sync(chunk) == CIO_OK, "cio_chunk_sync() succeeds");
    }

    cio_destroy(ctx);

    /* ── fs backend: memory mapped files on a real directory ───────── */
    cio_options_init(&opts);
    opts.root_path = FS_ROOT;
    opts.log_level = CIO_LOG_INFO;
    opts.log_cb = log_cb;
    opts.flags = CIO_CHECKSUM;

    ctx = cio_create(&opts);
    check(ctx != NULL,
          "cio_create(root_path=" FS_ROOT ") creates the root directory");
    if (ctx == NULL) {
        goto done;
    }

    stream = cio_stream_create(ctx, "tp-fs", CIO_STORE_FS);
    check(stream != NULL, "cio_stream_create(CIO_STORE_FS)");

    chunk = cio_chunk_open(ctx, stream, "fs-blob", CIO_OPEN, PAYLOAD_SIZE,
                           &err);
    check(chunk != NULL, "cio_chunk_open() on the fs backend");

    if (chunk != NULL) {
        check(cio_chunk_write(chunk, payload, PAYLOAD_SIZE) == CIO_OK,
              "fs chunk write (fallocate -> ftruncate fallback path)");
        check(cio_chunk_sync(chunk) == CIO_OK, "fs chunk sync");

        content_size = cio_chunk_get_content_size(chunk);
        check(content_size == (ssize_t) PAYLOAD_SIZE,
              "fs chunk content size equals bytes written");
    }

    cio_destroy(ctx);

    check(dir_entries(FS_ROOT "tp-fs") > 0,
          "chunk file materialised on disk under " FS_ROOT "tp-fs");

done:
    printf("assertions=%d failures=%d\n", g_checks, g_failures);
    return g_failures == 0 && g_checks > 0 ? 0 : 1;
}
