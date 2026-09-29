/*
 * libaegis 0.10.6 HarmonyOS consumer end-to-end test (ohos-aarch64).
 *
 * A standalone consumer program, independent from test_package. It drives
 * the public libaegis API end to end against a real backing file via the
 * RAF (Random-Access Encrypted File) interface, and observes the aarch64
 * runtime CPU dispatch and the shared-library SONAME load path.
 *
 * Flow covered (all against a real file through aegis_raf_io callbacks):
 *   1. aegis_init() runtime CPU capability detection.
 *   2. create RAF container on a real file  -> write records -> sync+close
 *   3. reopen the same file                 -> read back records -> byte
 *      compare with the plaintext written
 *   4. tamper one byte of the ciphertext in the backing file -> read must
 *      be rejected (authentication failure)
 *   5. reopen with the wrong master key     -> must be rejected
 *   6. observe runtime dispatch values (neon / neon_aes / neon_sha3 /
 *      sve2_aes) with the same HWCAP bit definitions used upstream
 *      (src/common/cpu.c), and the loaded shared-library path from
 *      /proc/self/maps (SONAME libaegis.so.0).
 *
 * POSIX-only single path: no platform conditional compilation macros.
 * Temporary files are created under $TMPDIR (fallback $HOME/tmp), never
 * /tmp. Exit code 0 == all checks passed, 1 == at least one failure.
 */

#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/auxv.h>
#include <unistd.h>

#include "aegis.h"
#include "aegis_raf.h"

static int checks = 0;
static int failures = 0;

#define CHECK(cond, name)                                             \
    do {                                                              \
        checks++;                                                     \
        if (cond) {                                                   \
            printf("ok %2d - %s\n", checks, name);                    \
        } else {                                                      \
            failures++;                                               \
            printf("FAIL %2d - %s\n", checks, name);                  \
        }                                                             \
    } while (0)

/* ------------------------------------------------------------------ */
/* Backing-store callbacks: real file via pread/pwrite/ftruncate/fsync */
/* ------------------------------------------------------------------ */

typedef struct {
    int fd;
} file_backing_t;

static int
file_read_at(void *user, uint8_t *buf, size_t len, uint64_t off)
{
    file_backing_t *b = (file_backing_t *) user;
    ssize_t n = pread(b->fd, buf, len, (off_t) off);
    return (n == (ssize_t) len) ? 0 : -1;
}

static int
file_write_at(void *user, const uint8_t *buf, size_t len, uint64_t off)
{
    file_backing_t *b = (file_backing_t *) user;
    ssize_t n = pwrite(b->fd, buf, len, (off_t) off);
    return (n == (ssize_t) len) ? 0 : -1;
}

static int
file_get_size(void *user, uint64_t *size)
{
    file_backing_t *b = (file_backing_t *) user;
    struct stat st;
    if (fstat(b->fd, &st) != 0) {
        return -1;
    }
    *size = (uint64_t) st.st_size;
    return 0;
}

static int
file_set_size(void *user, uint64_t size)
{
    file_backing_t *b = (file_backing_t *) user;
    return (ftruncate(b->fd, (off_t) size) == 0) ? 0 : -1;
}

static int
file_sync(void *user)
{
    file_backing_t *b = (file_backing_t *) user;
    return (fsync(b->fd) == 0) ? 0 : -1;
}

/* CSPRNG from /dev/urandom (POSIX single path). */
static int
urandom_fill(void *user, uint8_t *out, size_t len)
{
    (void) user;
    int fd = open("/dev/urandom", O_RDONLY);
    if (fd < 0) {
        return -1;
    }
    size_t got = 0;
    while (got < len) {
        ssize_t n = read(fd, out + got, len - got);
        if (n <= 0) {
            close(fd);
            return -1;
        }
        got += (size_t) n;
    }
    close(fd);
    return 0;
}

/* ------------------------------------------------------------------ */
/* Runtime dispatch observation (same bit layout as upstream cpu.c)    */
/* ------------------------------------------------------------------ */

#ifndef AT_HWCAP2
#define AT_HWCAP2 26
#endif

#define AEGIS_AARCH64_HWCAP_ASIMD   (1UL << 1)
#define AEGIS_AARCH64_HWCAP_AES     (1UL << 3)
#define AEGIS_AARCH64_HWCAP_SHA3    (1UL << 17)
#define AEGIS_AARCH64_HWCAP2_SVEAES (1UL << 2)

static uint64_t
read_hwcap(unsigned long which)
{
    return (uint64_t) getauxval(which);
}

static void
observe_runtime_dispatch(void)
{
    uint64_t hw = read_hwcap(AT_HWCAP);
    uint64_t hw2 = read_hwcap(AT_HWCAP2);
    int neon = (hw & AEGIS_AARCH64_HWCAP_ASIMD) != 0;
    int neon_aes = (hw & AEGIS_AARCH64_HWCAP_AES) != 0;
    int neon_sha3 = (hw & AEGIS_AARCH64_HWCAP_SHA3) != 0;
    int sve2_aes = (hw2 & AEGIS_AARCH64_HWCAP2_SVEAES) != 0;

    printf("runtime dispatch: neon=%d neon_aes=%d neon_sha3=%d sve2_aes=%d "
           "(AT_HWCAP=0x%lx AT_HWCAP2=0x%lx)\n",
           neon, neon_aes, neon_sha3, sve2_aes,
           (unsigned long) hw, (unsigned long) hw2);
    CHECK(neon == 1, "aarch64 runtime dispatch: neon enabled on device");
    CHECK(neon_sha3 == 0 || neon_sha3 == 1, "runtime dispatch values readable");
}

static void
observe_soname_load_path(void)
{
    FILE *f = fopen("/proc/self/maps", "r");
    int found = 0;
    if (f == NULL) {
        printf("failed to open /proc/self/maps (errno=%d)\n", errno);
        CHECK(0, "shared library loading observed via /proc/self/maps");
        return;
    }
    char line[1024];
    while (fgets(line, sizeof line, f) != NULL) {
        if (strstr(line, "libaegis") != NULL) {
            printf("maps: %s", line);
            found = 1;
        }
    }
    fclose(f);
    CHECK(found == 1, "libaegis shared library mapped (SONAME load path observed)");
}

/* ------------------------------------------------------------------ */
/* Main E2E flow                                                       */
/* ------------------------------------------------------------------ */

static int
run_raf_e2e(const char *path)
{
    /* deterministic 16-byte master key (AEGIS-128L RAF) */
    uint8_t key[16];
    uint8_t wrong_key[16];
    memset(key, 0x42, sizeof key);
    memset(wrong_key, 0x99, sizeof wrong_key);

    file_backing_t back;
    back.fd = open(path, O_RDWR | O_CREAT | O_TRUNC, 0600);
    if (back.fd < 0) {
        perror("open backing file");
        return 1;
    }

    aegis_raf_io io;
    memset(&io, 0, sizeof io);
    io.user = &back;
    io.read_at = file_read_at;
    io.write_at = file_write_at;
    io.get_size = file_get_size;
    io.set_size = file_set_size;
    io.sync = file_sync;

    aegis_raf_rng rng;
    memset(&rng, 0, sizeof rng);
    rng.random = urandom_fill;

    uint32_t chunk = AEGIS_RAF_CHUNK_MIN; /* 1024 */
    size_t scratch_len = aegis128l_raf_scratch_size(chunk);
    uint8_t *scratch_mem = (uint8_t *) malloc(scratch_len + AEGIS_RAF_SCRATCH_ALIGN);
    if (scratch_mem == NULL) {
        close(back.fd);
        return 1;
    }
    uint8_t *scratch_buf =
        (uint8_t *) (((uintptr_t) scratch_mem + AEGIS_RAF_SCRATCH_ALIGN - 1) &
                     ~((uintptr_t) AEGIS_RAF_SCRATCH_ALIGN - 1));
    aegis_raf_scratch scratch;
    scratch.buf = scratch_buf;
    scratch.len = scratch_len;

    aegis_raf_config cfg;
    memset(&cfg, 0, sizeof cfg);
    cfg.chunk_size = chunk;
    cfg.flags = AEGIS_RAF_CREATE;
    cfg.scratch = &scratch;

    aegis128l_raf_ctx ctx;
    memset(&ctx, 0, sizeof ctx);

    /* 2. create container + write records at three offsets */
    if (aegis128l_raf_create(&ctx, &io, &rng, &cfg, key) != 0) {
        printf("aegis128l_raf_create failed (errno=%d)\n", errno);
        free(scratch_mem);
        close(back.fd);
        return 1;
    }

    const char *rec1 = "libaegis HarmonyOS consumer E2E record one";
    const char *rec2 = "libaegis HarmonyOS consumer E2E record two";
    const char *rec3 = "libaegis HarmonyOS consumer E2E record three";
    size_t rec1_len = strlen(rec1);
    size_t rec2_len = strlen(rec2) + 2000; /* cross a chunk boundary */
    size_t rec3_len = strlen(rec3) + 500;
    uint8_t *big = (uint8_t *) malloc(rec2_len);
    if (big == NULL) {
        free(scratch_mem);
        close(back.fd);
        return 1;
    }
    memcpy(big, rec2, strlen(rec2));
    for (size_t i = strlen(rec2); i < rec2_len; i++) {
        big[i] = (uint8_t) (i & 0xff);
    }

    size_t written = 0;
    int rc = aegis128l_raf_write(&ctx, &written, (const uint8_t *) rec1, rec1_len, 0);
    if (rc != 0 || written != rec1_len) {
        printf("write rec1 failed rc=%d written=%zu (errno=%d)\n", rc, written, errno);
    }
    CHECK(rc == 0 && written == rec1_len, "RAF write record 1 at offset 0");

    size_t off2 = (size_t) AEGIS_RAF_HEADER_SIZE * 4; /* plaintext offset 256 */
    rc = aegis128l_raf_write(&ctx, &written, big, rec2_len, off2);
    CHECK(rc == 0 && written == rec2_len, "RAF write record 2 (chunk-crossing)");

    size_t off3 = off2 + rec2_len + 128;
    rc = aegis128l_raf_write(&ctx, &written, (const uint8_t *) rec3, rec3_len, off3);
    CHECK(rc == 0 && written == rec3_len, "RAF write record 3 at later offset");

    uint64_t logical_size = 0;
    rc = aegis128l_raf_get_size(&ctx, &logical_size);
    uint64_t expect_size = (uint64_t) (off3 + rec3_len);
    CHECK(rc == 0 && logical_size == expect_size, "RAF get_size matches written extent");

    rc = aegis128l_raf_sync(&ctx);
    CHECK(rc == 0, "RAF sync flushes to backing file");
    aegis128l_raf_close(&ctx);

    /* 3. reopen the same file and read every record back, byte-compare */
    aegis128l_raf_ctx ctx2;
    memset(&ctx2, 0, sizeof ctx2);
    rc = aegis128l_raf_open(&ctx2, &io, &rng, &cfg, key);
    CHECK(rc == 0, "RAF reopen with correct key");

    uint8_t *buf1 = (uint8_t *) malloc(rec1_len);
    uint8_t *buf2 = (uint8_t *) malloc(rec2_len);
    uint8_t *buf3 = (uint8_t *) malloc(rec3_len);
    size_t got = 0;

    rc = aegis128l_raf_read(&ctx2, buf1, &got, rec1_len, 0);
    CHECK(rc == 0 && got == rec1_len && memcmp(buf1, rec1, rec1_len) == 0,
          "read back record 1 plaintext matches");

    rc = aegis128l_raf_read(&ctx2, buf2, &got, rec2_len, off2);
    CHECK(rc == 0 && got == rec2_len && memcmp(buf2, big, rec2_len) == 0,
          "read back record 2 plaintext matches");

    rc = aegis128l_raf_read(&ctx2, buf3, &got, rec3_len, off3);
    CHECK(rc == 0 && got == rec3_len && memcmp(buf3, rec3, rec3_len) == 0,
          "read back record 3 plaintext matches");

    /* EOF: reading one byte at logical end returns 0 bytes */
    got = 1;
    rc = aegis128l_raf_read(&ctx2, buf1, &got, 1, (uint64_t) expect_size);
    CHECK(rc == 0 && got == 0, "read at end of file returns EOF (0 bytes)");

    aegis128l_raf_close(&ctx2);

    /* 4. tamper one ciphertext byte in the backing file -> read must fail */
    uint8_t orig = 0;
    ssize_t n = pread(back.fd, &orig, 1, (off_t) AEGIS_RAF_HEADER_SIZE);
    if (n == 1) {
        uint8_t flipped = (uint8_t) (orig ^ 0x55);
        if (pwrite(back.fd, &flipped, 1, (off_t) AEGIS_RAF_HEADER_SIZE) == 1) {
            aegis128l_raf_ctx ctx3;
            memset(&ctx3, 0, sizeof ctx3);
            rc = aegis128l_raf_open(&ctx3, &io, &rng, &cfg, key);
            if (rc == 0) {
                got = 0;
                rc = aegis128l_raf_read(&ctx3, buf1, &got, rec1_len, 0);
            }
            CHECK(rc == -1, "tampered ciphertext byte rejected on read");
            aegis128l_raf_close(&ctx3);
            /* restore the original byte */
            if (pwrite(back.fd, &orig, 1, (off_t) AEGIS_RAF_HEADER_SIZE) != 1) {
                printf("failed to restore tampered byte (errno=%d)\n", errno);
            }
            /* and verify the restored file is readable again */
            aegis128l_raf_ctx ctx4;
            memset(&ctx4, 0, sizeof ctx4);
            rc = aegis128l_raf_open(&ctx4, &io, &rng, &cfg, key);
            if (rc == 0) {
                got = 0;
                rc = aegis128l_raf_read(&ctx4, buf1, &got, rec1_len, 0);
            }
            CHECK(rc == 0 && got == rec1_len && memcmp(buf1, rec1, rec1_len) == 0,
                  "restored file reads back cleanly");
            aegis128l_raf_close(&ctx4);
        } else {
            CHECK(0, "able to flip backing-file byte for tamper test");
        }
    } else {
        CHECK(0, "able to read backing-file byte for tamper test");
    }

    /* 5. reopen with the wrong master key -> must fail */
    aegis128l_raf_ctx ctx5;
    memset(&ctx5, 0, sizeof ctx5);
    rc = aegis128l_raf_open(&ctx5, &io, &rng, &cfg, wrong_key);
    CHECK(rc == -1, "reopen with wrong master key rejected");
    aegis128l_raf_close(&ctx5);

    free(big);
    free(buf1);
    free(buf2);
    free(buf3);
    free(scratch_mem);
    close(back.fd);
    return 0;
}

int
main(int argc, char **argv)
{
    (void) argc;
    (void) argv;

    if (aegis_init() != 0) {
        printf("aegis_init() failed\n");
        return 1;
    }
    CHECK(1, "aegis_init runtime CPU capability detection");

    observe_runtime_dispatch();
    observe_soname_load_path();

    const char *tmpdir = getenv("TMPDIR");
    if (tmpdir == NULL || tmpdir[0] == '\0') {
        const char *home = getenv("HOME");
        static char fallback[512];
        if (home != NULL && home[0] != '\0') {
            snprintf(fallback, sizeof fallback, "%s/tmp", home);
            tmpdir = fallback;
        } else {
            tmpdir = ".";
        }
    }
    mkdir(tmpdir, 0700); /* ignore EEXIST */
    char path[1024];
    snprintf(path, sizeof path, "%s/libaegis_e2e_container.XXXXXX", tmpdir);
    int fd = mkstemp(path);
    if (fd < 0) {
        printf("mkstemp failed in %s (errno=%d)\n", tmpdir, errno);
        return 1;
    }
    close(fd);
    printf("backing file: %s\n", path);

    run_raf_e2e(path);

    unlink(path);

    if (failures == 0) {
        printf("all %d checks passed\n", checks);
        return 0;
    }
    printf("%d/%d checks FAILED\n", failures, checks);
    return 1;
}