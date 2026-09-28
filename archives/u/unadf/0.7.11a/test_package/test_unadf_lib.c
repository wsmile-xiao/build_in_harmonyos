/*
 * unadf test_package consumer — links libadf (the packaged static library)
 * and drives a real roundtrip:
 *
 *   1. adfEnvInitDefault()          — the LP64 guard upstream added an abort
 *                                     for; on a 64-bit target it exits 1 here
 *                                     if the on-disk structures are not
 *                                     fixed-width. This is the single most
 *                                     important assertion in the test.
 *   2. adfCreateDumpDevice()        — 80-cylinder standard ADF geometry.
 *   3. adfCreateHdFile()            — writes a real FFS volume + bitmap +
 *                                     root block to disk.
 *   4. adfReleaseDumpDevice().
 *   5. adfCreateDumpDevice() again  — re-open the file we just wrote.
 *   6. adfMount()                   — read back the boot block, validate the
 *                                     FFS signature and the volume name.
 *
 * The script then feeds that image to the unadf CLI, so both the packaged
 * library and the packaged binary are exercised against one artifact.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "adflib.h"
#include "adf_env.h"
#include "adf_str.h"
#include "adf_blk.h"
#include "adf_dump.h"
#include "adf_disk.h"

#define CYL 80

/* Swallow the library's own progress/warning chatter so that anything on
 * stdout is a test verdict. */
static void mute(char *s) { (void)s; }

int main(int argc, char **argv)
{
    struct Device *dev;
    struct Volume *vol;
    const char *path = (argc > 1) ? argv[1] : "test.adf";
    const char *volname = "Empty";
    int rc = 0;

    /* 1. LP64 guard: aborts (exit 1) on a non-fixed-width 64-bit build. */
    adfEnvInitDefault();

    adfEnv.useProgressBar = FALSE;
    adfEnv.vFct = mute;
    adfEnv.wFct = mute;

    /* 2 + 3. Format a standard 880-block (80 cyl x 2 heads x 11 sect x 512)
     * Amiga floppy image with an FFS volume. */
    dev = adfCreateDumpDevice((char *)path, CYL, 2, 11);
    if (dev == NULL) {
        fprintf(stderr, "FAIL: adfCreateDumpDevice(%s) returned NULL\n", path);
        return 1;
    }
    if (adfCreateHdFile(dev, (char *)volname, FSMASK_FFS) != RC_OK) {
        fprintf(stderr, "FAIL: adfCreateHdFile failed\n");
        return 1;
    }
    adfReleaseDumpDevice(dev);
    printf("PASS: formatted %s as FFS volume \"%s\"\n", path, volname);

    /* 4. Re-open the file we just wrote and mount it. */
    dev = adfCreateDumpDevice((char *)path, CYL, 2, 11);
    if (dev == NULL) {
        fprintf(stderr, "FAIL: re-open of %s returned NULL\n", path);
        return 1;
    }
    vol = adfMount(dev, 0, TRUE);
    if (vol == NULL) {
        fprintf(stderr, "FAIL: adfMount returned NULL\n");
        return 1;
    }
    if (vol->volName == NULL || strcmp(vol->volName, volname) != 0) {
        fprintf(stderr, "FAIL: volume name mismatch, got \"%s\"\n",
                vol->volName ? vol->volName : "(null)");
        rc = 1;
    } else {
        printf("PASS: mount read back volume name \"%s\"\n", vol->volName);
    }
    if (!isFFS(vol->dosType)) {
        fprintf(stderr, "FAIL: dosType 0x%02x is not FFS\n", (unsigned)vol->dosType);
        rc = 1;
    } else {
        printf("PASS: dosType 0x%02x reads as FFS\n", (unsigned)vol->dosType);
    }
    adfUnMount(vol);
    adfReleaseDumpDevice(dev);
    adfEnvCleanUp();

    if (rc == 0)
        printf("LIB_ASSERTIONS_OK\n");
    return rc;
}
