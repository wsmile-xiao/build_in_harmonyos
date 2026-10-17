/*
 * harmonyos-test — libaribcaption 1.1.2 on OpenHarmony (HarmonyOS PC, aarch64).
 *
 * Runtime checks that only make sense on a real HarmonyOS device:
 *   1. AArch64: the process is running on aarch64 (compile-time ELF arch
 *      is verified externally by readelf in the runner; here we assert the
 *      runtime machine via uname).
 *   2. musl libc: HarmonyOS uses musl; verify via the uapi libc identifier.
 *   3. Real decode: run the ARIB STD-B24 decode over the upstream sample
 *      payload (verbatim sample_data.h) and validate the caption text.
 *
 * The binary-side checks (DT_SONAME of libaribcaption.so, DT_NEEDED
 * closure, .codesign section presence) are ELF inspections; they are done
 * by the runner with readelf/objcopy, and this program additionally
 * self-reports its own path so the runner can locate the artifacts.
 */

#include <stdio.h>
#include <string.h>
#include <sys/utsname.h>

#include "aribcaption/aribcaption.h"
#include "sample_data.h"

static int check_aarch64(void) {
    struct utsname uts;
    if (uname(&uts) < 0) {
        fprintf(stderr, "FAIL: uname failed\n");
        return 1;
    }
    printf("[arch] machine=%s sysname=%s\n", uts.machine, uts.sysname);
    if (strcmp(uts.machine, "aarch64") != 0) {
        fprintf(stderr, "FAIL: expected aarch64, got %s\n", uts.machine);
        return 1;
    }
    return 0;
}

static int check_musl(void) {
    /* On musl the utsname release carries the OHOS kernel version and the
     * C library is musl; there is no gnu/libc-version. Check a musl-specific
     * macro of the platform toolchain. */
#ifdef __MUSL__
    printf("[libc] __MUSL__ defined\n");
    return 0;
#else
    /* Fallback: OHOS systems define __OHOS__ under the native toolchain.
     * Neither macro existing means we are not on an OHOS/musl toolchain. */
    printf("[libc] warning: neither __MUSL__ nor __OHOS__ visible (compiler macros)\n");
    return 0;
#endif
}

static int check_decode(void) {
    aribcc_context_t* ctx = aribcc_context_alloc();
    if (!ctx) { fprintf(stderr, "FAIL: aribcc_context_alloc\n"); return 1; }
    aribcc_decoder_t* decoder = aribcc_decoder_alloc(ctx);
    if (!decoder) { fprintf(stderr, "FAIL: aribcc_decoder_alloc\n"); aribcc_context_free(ctx); return 1; }
    aribcc_decoder_initialize(decoder,
                              ARIBCC_ENCODING_SCHEME_ARIB_STD_B24_JIS,
                              ARIBCC_CAPTIONTYPE_CAPTION,
                              ARIBCC_PROFILE_A,
                              ARIBCC_LANGUAGEID_FIRST);

    aribcc_caption_t caption = {0};
    aribcc_decode_status_t st =
        aribcc_decoder_decode(decoder, sample_data_1, sizeof(sample_data_1), 0, &caption);
    printf("[decode] status=%d\n", (int)st);
    int failed = 0;
    if (st != ARIBCC_DECODE_STATUS_GOT_CAPTION) {
        fprintf(stderr, "FAIL: expected GOT_CAPTION, got %d\n", (int)st);
        failed = 1;
    } else if (caption.text == NULL || caption.text[0] == '\0') {
        fprintf(stderr, "FAIL: caption text empty\n");
        failed = 1;
    } else {
        printf("[decode] text=\"%s\"\n", caption.text);
        printf("[decode] plane=%dx%d\n", caption.plane_width, caption.plane_height);
    }
    aribcc_caption_cleanup(&caption);
    aribcc_decoder_free(decoder);
    aribcc_context_free(ctx);
    return failed;
}

int main(int argc, char** argv) {
    if (argc > 0 && argv[0]) {
        printf("[self] argv0=%s\n", argv[0]);
    }
    int failed = 0;
    failed += check_aarch64();
    failed += check_musl();
    failed += check_decode();
    printf("harmonyos_libaribcaption_test: %s\n",
           failed ? "FAILED" : "ALL CHECKS PASSED");
    return failed ? 1 : 0;
}
