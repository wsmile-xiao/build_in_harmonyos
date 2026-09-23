/* Consumer test: AIFF metadata attribute round-trip and error paths.
 *
 * Exercises SetAttribute/GetAttribute (NAME/AUTH/COPY), the instrument
 * query entry, and the NULL-on-missing-file error contract. Each stage
 * prints one CHECK-OK line counted by the conanfile marker.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libaiff/libaiff.h>

int main(void)
{
    AIFF_Ref w;
    AIFF_Ref r;
    Instrument inst;
    char *name;
    char *auth;
    char *copy;
    const char *path;
    char tmp[256];
    int32_t one = 7;

    path = getenv("LIBAIFF_TEST_TMP");
    if (path == NULL || path[0] == '\0') {
        path = "libaiff_metadata.aiff";
    }
    snprintf(tmp, sizeof(tmp), "%s_md.aiff", path);

    w = AIFF_OpenFile(tmp, F_WRONLY);
    if (w == NULL) {
        printf("FAIL open-write\n");
        return 1;
    }
    if (!AIFF_SetAudioFormat(w, 1, 22050.0, 16)) {
        printf("FAIL set-audio-format\n");
        AIFF_CloseFile(w);
        return 1;
    }
    if (!AIFF_SetAttribute(w, AIFF_NAME, "hmbs-title")) {
        printf("FAIL set-name\n");
        AIFF_CloseFile(w);
        return 1;
    }
    if (!AIFF_SetAttribute(w, AIFF_AUTH, "hmbs-artist")) {
        printf("FAIL set-auth\n");
        AIFF_CloseFile(w);
        return 1;
    }
    if (!AIFF_SetAttribute(w, AIFF_COPY, "(c) hmbs")) {
        printf("FAIL set-copy\n");
        AIFF_CloseFile(w);
        return 1;
    }
    printf("CHECK-OK: set-attributes\n");

    if (!AIFF_StartWritingSamples(w)) {
        printf("FAIL start-writing\n");
        AIFF_CloseFile(w);
        return 1;
    }
    if (AIFF_WriteSamples32Bit(w, &one, 1) != 1) {
        printf("FAIL write-one-sample\n");
        AIFF_CloseFile(w);
        return 1;
    }
    /* AIFF_CloseFile returns 1 on successful write-close (see
     * AIFF_WriteClose: ret=1 when stat==3, -1 on I/O error). */
    if (!AIFF_EndWritingSamples(w)) {
        printf("FAIL end-writing\n");
        AIFF_CloseFile(w);
        return 1;
    }
    {
        int closeRc = AIFF_CloseFile(w);
        if (closeRc != 1) {
            printf("FAIL close-write rc=%d\n", closeRc);
            return 1;
        }
    }
    printf("CHECK-OK: write-close\n");

    r = AIFF_OpenFile(tmp, F_RDONLY);
    if (r == NULL) {
        printf("FAIL open-read\n");
        return 1;
    }
    name = AIFF_GetAttribute(r, AIFF_NAME);
    auth = AIFF_GetAttribute(r, AIFF_AUTH);
    copy = AIFF_GetAttribute(r, AIFF_COPY);
    if (name == NULL || strcmp(name, "hmbs-title") != 0) {
        printf("FAIL name-attr got=%s\n", name ? name : "(null)");
        AIFF_CloseFile(r);
        return 1;
    }
    if (auth == NULL || strcmp(auth, "hmbs-artist") != 0) {
        printf("FAIL auth-attr got=%s\n", auth ? auth : "(null)");
        AIFF_CloseFile(r);
        return 1;
    }
    if (copy == NULL || strcmp(copy, "(c) hmbs") != 0) {
        printf("FAIL copy-attr got=%s\n", copy ? copy : "(null)");
        AIFF_CloseFile(r);
        return 1;
    }
    printf("CHECK-OK: get-attributes\n");

    /* Instrument query must be callable on a plain AIFF file (returns
     * 0 when no instrument chunk exists, non-crash is the contract). */
    memset(&inst, 0, sizeof(inst));
    (void)AIFF_GetInstrumentData(r, &inst);
    AIFF_CloseFile(r);
    remove(tmp);
    printf("CHECK-OK: instrument-query\n");

    /* Error contract: opening a missing file for read must fail. */
    r = AIFF_OpenFile("/nonexistent-hmbs-path/missing.aiff", F_RDONLY);
    if (r != NULL) {
        printf("FAIL missing-file-opened\n");
        AIFF_CloseFile(r);
        return 1;
    }
    /* Deliberately no CHECK-OK here would undercount; the NULL contract
     * itself is the checked behavior. */
    printf("CHECK-OK: missing-file-null\n");
    return 0;
}
