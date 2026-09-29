#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/stat.h>
#include <sys/types.h>

#include "paradox.h"

/*
 * The OHOS aarch64 /tmp is read-only (HMDFS); the test scratch file must
 * live under $HOME/tmp instead.  $HOME/tmp itself may not exist on CI
 * workers, so create it (and $HOME if needed) before opening the file.
 */
static const char *scratch_path(void)
{
    const char *home = getenv("HOME");
    if (!home)
        home = ".";
    static char buf[512];
    snprintf(buf, sizeof(buf), "%s/tmp/pxlib_test_min.par", home);

    /* Ensure $HOME/tmp exists (best-effort, ignore EEXIST). */
    static char tmpdir[256];
    snprintf(tmpdir, sizeof(tmpdir), "%s/tmp", home);
    mkdir(home, 0700);          /* best-effort, ignore EEXIST/EPERM */
    mkdir(tmpdir, 0700);        /* best-effort, ignore EEXIST/EPERM */
    return buf;
}

/*
 * Minimal *valid* Paradox database header for pxlib's get_px_head().
 *
 * Offsets follow struct _TPxHeader (src/fileformat.h), packed LE layout
 * (word=2B, byte=1B, longint=4B, integer=2B, pointer=4B):
 *
 *   0x00 recordSize  word   — must be != 0
 *   0x02 headerSize  word   — must be != 0
 *   0x04 fileType    byte   — must be in [0, 8]
 *   0x05 maxTableSize byte  — must be in [1, 32]
 *   0x06 numRecords  longint (4B)
 *   0x0A nextBlock   word
 *   0x0C fileBlocks  word
 *   0x0E firstBlock  word
 *   0x10 lastBlock   word
 *   0x12 unknown12x13 word
 *   0x14 modifiedFlags1 byte
 *   0x15 indexFieldNumber byte
 *   0x16 primaryIndexWorkspace pointer (4B)
 *   0x1A unknownPtr1A pointer (4B)
 *   0x1E indexRoot word
 *   0x20 numIndexLevels byte
 *   0x21 numFields integer (2B)
 *   0x23 primaryKeyFields integer (2B)
 *   0x25 encryption1 longint (4B)
 *   0x29 sortOrder byte
 *   0x2A modifiedFlags2 byte
 *   0x2B unknown2Bx2C [2]
 *   0x2D changeCount1 byte
 *   0x2E changeCount2 byte
 *   0x2F unknown2F byte
 *   0x30 tableNamePtrPtr pointer (4B)
 *   0x34 fldInfoPtr pointer (4B)
 *   0x38 writeProtected byte
 *   0x39 fileVersionID byte  — must be in [3, 15]
 *   ...
 *
 * We fill every field get_px_head() validates with plausible Paradox 4.x
 * values; the remaining 512-byte header stays zero (zero fields, zero
 * records).  If PX_open_file() succeeds, the packaged libpxlib.a links
 * and its C ABI is intact — the smoke this test provides.
 */
static int write_min_paradox(const char *path)
{
    FILE *fp = fopen(path, "wb");
    if (!fp)
        return -1;

    unsigned char hdr[512];
    memset(hdr, 0, sizeof(hdr));

    /* recordSize = 512 (non-zero) */
    hdr[0x00] = 0x00;
    hdr[0x01] = 0x02;
    /* headerSize = 512 (non-zero) */
    hdr[0x02] = 0x00;
    hdr[0x03] = 0x02;
    /* fileType = 0 (database, in [0, 8]) */
    hdr[0x04] = 0;
    /* maxTableSize = 16 (in [1, 32]) */
    hdr[0x05] = 16;
    /* numRecords = 0 (offset 0x06..0x09 LE, already zero) */
    /* fileVersionID = 5 (Paradox 4.0, in [3, 15]) at offset 0x39 */
    hdr[0x39] = 5;

    fwrite(hdr, 1, sizeof(hdr), fp);
    fclose(fp);
    return 0;
}

int main(void)
{
    const char *path = scratch_path();
    if (0 != write_min_paradox(path))
    {
        fprintf(stderr, "test_pxlib: cannot create minimal paradox file\n");
        return 1;
    }

    pxdoc_t *px = PX_new();
    if (!px)
    {
        fprintf(stderr, "test_pxlib: PX_new failed\n");
        return 1;
    }

    int rc = PX_open_file(px, path);
    if (0 != rc)
    {
        fprintf(stderr, "test_pxlib: PX_open_file failed, rc=%d\n", rc);
        PX_close(px);
        remove(path);
        return 1;
    }

    int fileversion = (px->px_head) ? px->px_head->px_fileversion : -1;
    int numrecords = (px->px_head) ? px->px_head->px_numrecords : -1;
    printf("test_pxlib: PX_open_file OK, fileversion=%d, numrecords=%d\n",
           fileversion, numrecords);
    PX_close(px);
    remove(path);
    printf("test_pxlib: PASS\n");
    return 0;
}
