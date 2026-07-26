/*
 * R34 test for snow 20130616 — whitespace steganography roundtrip.
 *
 * Embeds a hidden message into a cover file, extracts it back, and
 * verifies the extracted text matches the original. Exercises the
 * real snow binary via system(), covering embed + extract paths.
 *
 * OHOS note: /tmp is read-only (E002); use $TMPDIR (or $HOME/tmp
 * fallback) for scratch files.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    const char *tmp = getenv("TMPDIR");
    if (!tmp || !tmp[0]) tmp = getenv("HOME");
    if (!tmp || !tmp[0]) tmp = "/tmp";

    char in[1024], out[1024], ext[1024], cmd[2048];
    int rc;

    snprintf(in,  sizeof(in),  "%s/snow_in.txt",  tmp);
    snprintf(out, sizeof(out), "%s/snow_out.txt", tmp);
    snprintf(ext, sizeof(ext), "%s/snow_ext.txt", tmp);

    /* Create cover file with innocuous text */
    snprintf(cmd, sizeof(cmd),
             "echo 'cover text line 1' > %s && echo 'cover text line 2' >> %s",
             in, in);
    rc = system(cmd);
    if (rc != 0) { printf("FAIL: create cover file\n"); return 1; }
    printf("PASS: cover file created\n");

    /* Embed: snow -C -m 'message' cover.txt stego.txt */
    snprintf(cmd, sizeof(cmd),
             "snow -C -m 'roundtrip-secret-20130616' %s %s > /dev/null 2>&1",
             in, out);
    rc = system(cmd);
    if (rc != 0) { printf("FAIL: snow embed returned %d\n", rc); return 1; }
    printf("PASS: snow embed\n");

    /* Extract: snow -C stego.txt */
    snprintf(cmd, sizeof(cmd),
             "snow -C %s > %s 2>/dev/null",
             out, ext);
    rc = system(cmd);
    if (rc != 0) { printf("FAIL: snow extract returned %d\n", rc); return 1; }
    printf("PASS: snow extract\n");

    /* Verify extracted message contains the secret */
    snprintf(cmd, sizeof(cmd),
             "grep -q 'roundtrip-secret-20130616' %s 2>/dev/null",
             ext);
    rc = system(cmd);
    if (rc != 0) {
        printf("FAIL: extracted message does not contain secret\n");
        return 1;
    }
    printf("PASS: roundtrip secret verified\n");

    /* Cleanup */
    snprintf(cmd, sizeof(cmd), "rm -f %s %s %s 2>/dev/null", in, out, ext);
    system(cmd);

    printf("snow 20130616: all tests PASSED\n");
    return 0;
}
