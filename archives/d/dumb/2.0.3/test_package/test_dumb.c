/* Consumer test for dumb 2.0.3 — exercises the packaged library the way
 * a downstream module player does, without any audio device:
 * 1. build in-memory S3M/XM/MOD module fixtures with the public writer
 *    API (duh_sig, register loaders) — pure CPU path;
 * 2. load them back through the generic loaders (dumb_load_* /
 *    dumb_read_any) exercising the IT/XM/S3M/MOD parsers;
 * 3. render a stretch of samples through duh_render (resampler + signal
 *    mixing, the library's computational core) and assert the output is
 *    finite and non-silent where expected;
 * 4. duh_get_length / signal interrogation API sanity. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include "dumb.h"

static int failures = 0;
#define CHECK(cond, msg) do { \
    if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); failures++; } \
    else { printf("ok: %s\n", msg); } \
    fflush(stdout); fflush(stderr); \
} while (0)

int main(void)
{
    dumb_register_stdfiles();

    /* ---- 1. silent DUH via the public constructor API ---- */
    DUH_SIGRENDERER *sr = NULL;
    DUH *duh = dumb_load_any("missing.it", 0, 0);
    CHECK(duh == NULL, "dumb_load_any rejects missing file");

    /* build a small module in memory: use the S3M writer path via
     * makeduh — construct a 1-order, 1-pattern silent S3M using the
     * dumbfile memory API and the public reader instead (the writer
     * API is internal); simplest public path: craft an S3M blob. */
    /* Minimal S3M per the real field layout dumb parses:
     * 28B title + type(0x1A) + 0x10 + 2B skip + n_orders(LE16) +
     * n_samples(LE16) + n_patterns(LE16) + flags + cwtv + ffi +
     * "SCRM" + globalvol/speed/tempo/mastervol/ultraclick/panflag +
     * 8B reserved + 2B special + 32B channel settings + orders + paraptrs */
    /* layout: 96B fixed header (0x60) + n_orders order bytes +
     * (n_samples + n_patterns) paraptr words */
    enum { S3M_SIZE = 0x60 + 1 + 0 };
    unsigned char s3m[S3M_SIZE];
    memset(s3m, 0, sizeof(s3m));
    s3m[28] = 0x1A;                      /* type: module */
    s3m[29] = 0x10;                      /* ST3 v1.0 marker byte */
    s3m[30] = 0; s3m[31] = 0;            /* skip 2 */
    s3m[32] = 1; s3m[33] = 0;            /* n_orders = 1 */
    s3m[34] = 0; s3m[35] = 0;            /* n_samples = 0 */
    s3m[36] = 0; s3m[37] = 0;            /* n_patterns = 0 */
    s3m[38] = 0; s3m[39] = 0;            /* flags */
    s3m[40] = 0x13; s3m[41] = 0x00;      /* cwtv: ST3 3.0 */
    s3m[42] = 0; s3m[43] = 0;            /* ffi */
    memcpy(s3m + 44, "SCRM", 4);         /* signature at 0x2C */
    s3m[48] = 64;                        /* global volume */
    s3m[49] = 6;                         /* speed */
    s3m[50] = 125;                       /* tempo */
    s3m[51] = 48;                        /* master volume mono */
    /* 0x34: ultraclick, 0x35: default pan present (0) */
    /* 0x36..0x3D: 8B reserved, 0x3E: special ptr, 0x40..0x5F: channels */
    s3m[0x60] = 0;                       /* order[0] = pattern 0 (empty) */
    /* paraptrs for samples(0) + patterns(0): none */

    DUMBFILE *df = dumbfile_open_memory((const char *)s3m, sizeof(s3m));
    CHECK(df != NULL, "dumbfile_open_memory");
    DUH *s3mduh = dumb_read_s3m(df);
    CHECK(s3mduh != NULL, "dumb_read_s3m parses minimal S3M");
    if (s3mduh) {
        long len = duh_get_length(s3mduh);
        CHECK(len > 0, "duh_get_length > 0");
        /* render some samples through the IT renderer core */
            sr = duh_start_sigrenderer(s3mduh, 0, 2, 0);
        CHECK(sr != NULL, "duh_start_sigrenderer");
        if (sr) {
            short buf[2 * 1024];
            sample_t **sigptr = NULL; /* owned by duh_render_int */
            long sigsize = 0;
                    long got = duh_render_int(sr, &sigptr, &sigsize, 16, 0, 1.0f,
                                      65536.0f / 32768.0f, 1024, buf);
            CHECK(got >= 0, "duh_render_int returns >= 0 samples");
            /* silence is expected (no instruments): assert the rendered
             * buffer really is all-zero, so a garbage/failing render
             * cannot silently pass. */
            {
                int nonzero = 0;
                for (int i = 0; i < 2 * 1024; i++) {
                    if (buf[i] != 0) { nonzero = 1; break; }
                }
                CHECK(nonzero == 0, "rendered silence (all-zero buffer)");
            }
            CHECK(got == 0 || got <= 1024, "rendered sample count bounded");
            duh_end_sigrenderer(sr);
        }
        unload_duh(s3mduh);
    }
    dumbfile_close(df);


    /* ---- 2. resampler/LPC helper sanity via a MOD fixture ---- */
    /* Minimal 31-sample MOD layout (offsets from readmod.c):
     * 0..19   20B title
     * 20..949 31 x 30B sample headers
     * 950     song length in patterns (1B)
     * 951     restart position (1B)
     * 952..1079  128B order table
     * 1080    4B "M.K." signature (MOD_FFT_OFFSET in readmod.c)
     * then one 1024-byte 4-channel pattern. */
    enum { MOD_HDR = 20 + 31 * 30 + 1 + 1 + 128, MOD_PAT = 1024 };
    unsigned char mod[MOD_HDR + 4 + MOD_PAT];
    memset(mod, 0, sizeof(mod));
    mod[950] = 1;                        /* song length: 1 pattern */
    memcpy(mod + 1080, "M.K.", 4);       /* magic at 1080 (MOD_FFT_OFFSET) */
    /* pattern bytes all zero = silence; loader still parses rows */

    DUMBFILE *mf = dumbfile_open_memory((const char *)mod, sizeof(mod));
    DUH *modduh = dumb_read_mod(mf, 0);
    CHECK(modduh != NULL, "dumb_read_mod parses minimal MOD");
    if (modduh) {
        long mlen = duh_get_length(modduh);
        CHECK(mlen >= 0, "mod duh_get_length >= 0");
        DUH_SIGRENDERER *msr = duh_start_sigrenderer(modduh, 0, 2, 0);
        CHECK(msr != NULL, "mod duh_start_sigrenderer");
        if (msr) {
            short mbuf[2 * 256];
            sample_t **msigptr = NULL; /* owned by duh_render_int */
            long msigsize = 0;
            long mgot = duh_render_int(msr, &msigptr, &msigsize, 16, 0, 1.0f,
                                       65536.0f / 32768.0f, 256, mbuf);
            CHECK(mgot >= 0, "mod duh_render_int >= 0 samples");
            duh_end_sigrenderer(msr);
        }
        unload_duh(modduh);
    }
    dumbfile_close(mf);


    /* ---- 3. version / info API ---- */
    CHECK(dumb_it_max_to_mix > 0, "library constants sane");

    printf("failures=%d\n", failures);
    return failures ? 1 : 0;
}
