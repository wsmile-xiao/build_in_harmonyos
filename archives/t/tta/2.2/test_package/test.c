/*
 * test_package/test.c — tta 2.2 Conan test_package (OpenHarmony/aarch64)
 *
 * Upstream libtta 2.2 ships no automated tests (no TESTS/check_PROGRAMS in
 * Makefile.am, no test source or test directory in the tarball). This
 * consumer test therefore validates the installed libtta.a with a real
 * encode -> decode roundtrip over a memory/stdio-backed TTA_io_callback,
 * plus a few structural checks on the codec API.
 *
 * The harness prints the two hmbs hard-gate JSON markers at the end of
 * main(), sourced from the same tests_run / tests_failed counters as the
 * "Results:" summary line. Exit 0 on all-pass, 1 on any failure.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>

#include "libtta.h"

static int tests_run = 0;
static int tests_failed = 0;

#define RUN(fn) do { \
    printf("[run] %s\n", #fn); \
    tests_run++; \
    int _rc = (fn)(); \
    if (_rc != 0) { \
        tests_failed++; \
        printf("        [FAIL] %s\n", #fn); \
    } else { \
        printf("        [ok] %s\n", #fn); \
    } \
} while (0)

/* ------------------------------------------------------------------ *
 * stdio-backed TTA_io_callback (absolute seeks, byte counts).
 * Mirrors console/tta.c's TTA_io_callback_wrapper usage but uses FILE*.
 * ------------------------------------------------------------------ */
typedef struct {
    TTA_io_callback iocb;
    FILE *f;
} FileIo;

static TTAint32 file_read(TTA_io_callback *io, TTAuint8 *buf, TTAuint32 size) {
    FileIo *self = (FileIo *)io;
    return (TTAint32)fread(buf, 1, (size_t)size, self->f);
}

static TTAint32 file_write(TTA_io_callback *io, TTAuint8 *buf, TTAuint32 size) {
    FileIo *self = (FileIo *)io;
    return (TTAint32)fwrite(buf, 1, (size_t)size, self->f);
}

static TTAint64 file_seek(TTA_io_callback *io, TTAint64 offset) {
    FileIo *self = (FileIo *)io;
    if (fseek(self->f, (long)offset, SEEK_SET) != 0) return -1;
    return (TTAint64)ftell(self->f);
}

/* Create a unique writable temp file; returns an open FILE* ("w+b") and
 * leaves *tmpl holding the path so the caller can unlink() it. Prefer the
 * HMBS-injected TMPDIR; fall back to "." . */
static FILE *make_temp(const char *tdir, char *tmpl, size_t tmpl_sz) {
    const char *td = (tdir && *tdir) ? tdir : ".";
    snprintf(tmpl, tmpl_sz, "%s/tta_test_XXXXXX", td);
    int fd = mkstemp(tmpl);
    if (fd < 0) return NULL;
    FILE *f = fdopen(fd, "w+b");
    if (!f) { close(fd); unlink(tmpl); return NULL; }
    return f;
}

/* ------------------------------------------------------------------ *
 * Test cases
 * ------------------------------------------------------------------ */

/* 1. The binary-version query returns a value within the CPU_ARCH_TYPE
 *    enum contract (the public API is callable and returns a well-formed
 *    result). On non-x86 builds the codec reports CPU_ARCH_UNDEFINED, which
 *    is a valid enum value; callers branch on it before using x86 specifics. */
static int test_binary_version(void) {
    CPU_ARCH_TYPE v = tta_binary_version();
    printf("        tta_binary_version() = %d\n", (int)v);
    return (v < CPU_ARCH_UNDEFINED || v > CPU_ARCH_IX86_SSE4_2) ? 1 : 0;
}

/* 2-4. Full encode -> decode roundtrip.
 *    Encode a deterministic PCM waveform to a TTA1 stream, decode it back
 *    and require bit-exact reconstruction. */
static int test_roundtrip(void) {
    const TTAuint32 sps     = 8000;
    const TTAuint32 samples = 10000;   /* > MUL_FRAME_TIME(8000)=8359 -> 2 frames */
    const TTAuint32 nch     = 1;
    const TTAuint32 bps     = 16;
    const TTAuint32 smp     = nch * (bps / 8);
    const TTAuint32 pcm_bytes = samples * smp;

    int16_t *pcm = (int16_t *)malloc((size_t)pcm_bytes + 4);
    if (!pcm) return 1;
    for (TTAuint32 i = 0; i < samples; i++)
        pcm[i] = (int16_t)(((int)(i * 3)) % 20001 - 10000);

    const char *td = getenv("TMPDIR");
    if (!td || !*td) td = getenv("HMBS_TMPDIR");
    char tmpl[512];
    FILE *f = make_temp(td, tmpl, sizeof tmpl);
    if (!f) { free(pcm); return 1; }

    /* ---- encode ---- */
    FileIo io;
    memset(&io, 0, sizeof io);
    io.iocb.write = file_write;
    io.iocb.seek  = file_seek;
    io.iocb.read  = NULL;
    io.f = f;

    tta_encoder_new((TTA_io_callback *)&io);
    {
        TTA_info info;
        memset(&info, 0, sizeof info);
        info.format  = TTA_FORMAT_SIMPLE;
        info.nch     = nch;
        info.bps     = bps;
        info.sps     = sps;
        info.samples = samples;
        if (tta_encoder_init_set_info(&info, 0) != 0) {
            fprintf(stderr, "encoder init failed, status=%d\n", tta_encoder_get_error());
            tta_encoder_done(); fclose(f); unlink(tmpl); free(pcm);
            return 1;
        }
    }
    if (tta_encoder_process_stream((TTAuint8 *)pcm, pcm_bytes, NULL) != 0) {
        fprintf(stderr, "encoder process_stream failed, status=%d\n", tta_encoder_get_error());
        tta_encoder_done(); fclose(f); unlink(tmpl); free(pcm);
        return 1;
    }
    if (tta_encoder_finalize() != 0) {
        fprintf(stderr, "encoder finalize failed, status=%d\n", tta_encoder_get_error());
        tta_encoder_done(); fclose(f); unlink(tmpl); free(pcm);
        return 1;
    }
    tta_encoder_done();

    fflush(f);
    long enc_size = ftell(f);
    printf("        encoded %u bytes -> %ld-byte TTA1 stream\n",
           (unsigned)pcm_bytes, enc_size);
    /* A valid stream must at least contain the 22-byte TTA1 header + seek
     * table + some compressed payload. */
    if (enc_size <= 22) {
        fclose(f); unlink(tmpl); free(pcm);
        return 1;
    }

    /* ---- decode ---- */
    if (fseek(f, 0, SEEK_SET) != 0) { fclose(f); unlink(tmpl); free(pcm); return 1; }
    memset(&io, 0, sizeof io);
    io.iocb.read  = file_read;
    io.iocb.seek  = file_seek;
    io.iocb.write = NULL;
    io.f = f;

    tta_decoder_new((TTA_io_callback *)&io);
    {
        TTA_info dinfo;
        memset(&dinfo, 0, sizeof dinfo);
        if (tta_decoder_init_get_info(&dinfo) != 0) {
            fprintf(stderr, "decoder init_get_info failed, status=%d\n", tta_decoder_get_error());
            tta_decoder_done(); fclose(f); unlink(tmpl); free(pcm);
            return 1;
        }
        /* header must round-trip the stream parameters */
        if (dinfo.nch != nch || dinfo.bps != bps ||
            dinfo.sps != sps || dinfo.samples != samples) {
            fprintf(stderr, "decoded header mismatch: nch=%u bps=%u sps=%u samples=%u\n",
                    (unsigned)dinfo.nch, (unsigned)dinfo.bps,
                    (unsigned)dinfo.sps, (unsigned)dinfo.samples);
            tta_decoder_done(); fclose(f); unlink(tmpl); free(pcm);
            return 1;
        }
    }

    TTAuint32 out_cap = pcm_bytes + 8;
    TTAuint8 *dec = (TTAuint8 *)malloc((size_t)out_cap);
    if (!dec) { tta_decoder_done(); fclose(f); unlink(tmpl); free(pcm); return 1; }
    TTAuint32 dec_bytes = 0;
    for (;;) {
        TTAint32 n = tta_decoder_process_stream(dec + dec_bytes,
                                                (TTAuint32)(out_cap - dec_bytes), NULL);
        if (n < 0) {
            fprintf(stderr, "decoder process_stream failed, status=%d\n", tta_decoder_get_error());
            free(dec); tta_decoder_done(); fclose(f); unlink(tmpl); free(pcm);
            return 1;
        }
        if (n == 0) break;
        dec_bytes += (TTAuint32)n * smp;
        if (dec_bytes > pcm_bytes) break; /* guard against overrun */
    }
    tta_decoder_done();

    int ok = 1;
    if (dec_bytes != pcm_bytes) {
        fprintf(stderr, "decoded %u bytes, expected %u\n", (unsigned)dec_bytes, (unsigned)pcm_bytes);
        ok = 0;
    } else if (memcmp(dec, pcm, pcm_bytes) != 0) {
        fprintf(stderr, "decoded PCM does not match original\n");
        ok = 0;
    } else {
        printf("        roundtrip: %u/%u bytes bit-exact\n", (unsigned)dec_bytes, (unsigned)pcm_bytes);
    }

    fclose(f); unlink(tmpl);
    free(dec); free(pcm);
    return ok ? 0 : 1;
}

int main(void) {
    printf("=== tta 2.2 Conan test_package (OpenHarmony/aarch64) ===\n");
    printf("=== Verifying installed libtta.a via encode/decode roundtrip ===\n\n");

    RUN(test_binary_version);
    RUN(test_roundtrip);

    printf("\n=== Results: %d/%d passed, %d failed ===\n",
           tests_run - tests_failed, tests_run, tests_failed);

    {
        int discovered = tests_run;
        int passed     = tests_run - tests_failed;
        int failed     = tests_failed;
        const char *status = (failed == 0) ? "true" : "false";
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,\"command\":\"test_tta\",\"discovered\":%d,\"passedCount\":%d}\n",
               status, discovered, passed);
    }

    if (tests_failed == 0) {
        printf("\nAll tta consumer tests PASSED.\n");
        return 0;
    }
    printf("\n%d test(s) FAILED.\n", tests_failed);
    return 1;
}
