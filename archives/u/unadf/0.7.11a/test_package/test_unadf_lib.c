/*
 * unadf test_package consumer -- links libadf (the packaged static library)
 * and drives a real roundtrip through the PUBLIC API only:
 *
 *   1. adfEnvInitDefault()          -- the LP64 guard upstream added an abort
 *                                     for; on a 64-bit target it exits 1 here
 *                                     if the on-disk structures are not
 *                                     fixed-width. This is the single most
 *                                     important assertion in the test.
 *   2. adfCreateDumpDevice()        -- 80-cylinder standard ADF geometry.
 *   3. adfCreateHdFile()            -- writes a real FFS volume + bitmap +
 *                                     root block to disk.
 *   4. adfReleaseDumpDevice().
 *   5. adfMountDev(path, TRUE)      -- re-open the file we just wrote.
 *   6. adfMount()                   -- read back the boot block, validate the
 *                                     FFS signature and the volume name.
 *
 * Step 5 deliberately uses adfMountDev() and not a second
 * adfCreateDumpDevice(): the latter opens the file with fopen(...,"wb") and
 * fseeks to the last block, so calling it a second time truncates the image
 * that step 3 just wrote. adfMountDev() opens "rb" and calls
 * adfMountFlop(), which fills the geometry and the one-entry volume list that
 * adfMount() indexes.
 *
 * Deliberately NOT used: `adfEnv`, the library's global environment struct.
 * adf_str.h only offers it as the ENV_DECLARATION macro, which the library's
 * own .c files expand; no header declares it extern, so a consumer cannot
 * reach it. adf_env.h is likewise private -- it redeclares adfSetEnvFct with
 * four parameters where adflib.h declares it with three, so including both
 * headers is a hard compile error, and calling the 3-arg prototype would
 * pass a garbage fourth argument into the real 4-arg definition. Everything
 * the test needs is reachable from adflib.h + adf_blk.h + adf_dump.h.
 *
 * The script then feeds that image to the unadf CLI, so both the packaged
 * library and the packaged binary are exercised against one artifact.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "adflib.h"
#include "adf_blk.h"
#include "adf_dump.h"
#include "adf_err.h"

#define CYL 80
#define FNAME "roundtrip.bin"
#define NSECT 8
#define SECT_BYTES 512

int main(int argc, char **argv)
{
    struct Device *dev;
    struct Volume *vol;
    struct File *file;
    unsigned char payload[SECT_BYTES];
    unsigned char buf[SECT_BYTES];
    const char *path = (argc > 1) ? argv[1] : "test.adf";
    const char *volname = "Empty";
    int rc = 0;
    int i, j;

    /* 1. LP64 guard: aborts (exit 1) on a non-fixed-width 64-bit build. */
    adfEnvInitDefault();

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

    /* 5. Re-open the file we just wrote. adfMountDev() opens "rb" (a second
     * adfCreateDumpDevice() would fopen "wb" and truncate the image) and
     * calls adfMountFlop(), which fills dev->nVol for step 6. */
    dev = adfMountDev((char *)path, TRUE);
    if (dev == NULL) {
        fprintf(stderr, "FAIL: adfMountDev(%s) returned NULL\n", path);
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
        fprintf(stderr, "FAIL: dosType 0x%02x is not FFS\n",
                (unsigned char)vol->dosType);
        rc = 1;
    } else {
        printf("PASS: dosType 0x%02x reads as FFS\n",
               (unsigned char)vol->dosType);
    }
    adfUnMount(vol);
    adfReleaseDumpDevice(dev);

    /* 7. Write a real file into the volume, so the CLI extraction the script
     * performs afterwards has content to extract. An empty volume would make
     * "extraction exits 0" vacuous -- a real unzip-like tool must be proven
     * to write bytes out, not merely to walk an empty directory tree. */
    dev = adfMountDev((char *)path, FALSE);
    if (dev == NULL) {
        fprintf(stderr, "FAIL: adfMountDev(%s, rw) returned NULL\n", path);
        return 1;
    }
    vol = adfMount(dev, 0, FALSE);
    if (vol == NULL) {
        fprintf(stderr, "FAIL: adfMount(rw) returned NULL\n");
        return 1;
    }
    file = adfOpenFile(vol, (char *)FNAME, (char *)"w");
    if (file == NULL) {
        fprintf(stderr, "FAIL: adfOpenFile(%s) returned NULL\n", FNAME);
        rc = 1;
    } else {
        for (i = 0; i < NSECT; i++) {
            for (j = 0; j < (int)sizeof(payload); j++)
                payload[j] = (unsigned char)(i + j);
            if (adfWriteFile(file, (int32_t)sizeof(payload), payload) < 0) {
                fprintf(stderr, "FAIL: adfWriteFile at sector %d\n", i);
                rc = 1;
                break;
            }
        }
        adfCloseFile(file);
        if (rc == 0)
            printf("PASS: wrote %s (%d x %d bytes) into the volume\n",
                   FNAME, NSECT, (int)sizeof(payload));
    }
    adfUnMount(vol);
    adfReleaseDumpDevice(dev);

    /* 8. Re-mount read-only and read the bytes back, proving the write was
     * really committed to the on-disk image and not just to a cache. */
    dev = adfMountDev((char *)path, TRUE);
    if (dev == NULL) {
        fprintf(stderr, "FAIL: final adfMountDev returned NULL\n");
        return 1;
    }
    vol = adfMount(dev, 0, TRUE);
    if (vol == NULL) {
        fprintf(stderr, "FAIL: final adfMount returned NULL\n");
        return 1;
    }
    file = adfOpenFile(vol, (char *)FNAME, (char *)"r");
    if (file == NULL) {
        fprintf(stderr, "FAIL: adfOpenFile(%s, r) returned NULL\n", FNAME);
        rc = 1;
    } else {
        for (i = 0; i < NSECT; i++) {
            int32_t got = adfReadFile(file, (int32_t)sizeof(buf), buf);
            if (got != (int32_t)sizeof(buf)) {
                fprintf(stderr, "FAIL: adfReadFile at sector %d got %d\n",
                        i, (int)got);
                rc = 1;
                break;
            }
            for (j = 0; j < (int)sizeof(buf); j++) {
                if (buf[j] != (unsigned char)(i + j)) {
                    fprintf(stderr,
                            "FAIL: payload mismatch at sector %d byte %d\n",
                            i, j);
                    rc = 1;
                    break;
                }
            }
        }
        adfCloseFile(file);
        if (rc == 0)
            printf("PASS: read back %s byte-for-byte from the image\n", FNAME);
    }
    adfUnMount(vol);
    adfReleaseDumpDevice(dev);
    adfEnvCleanUp();

    if (rc == 0)
        printf("LIB_ASSERTIONS_OK\n");
    return rc;
}
