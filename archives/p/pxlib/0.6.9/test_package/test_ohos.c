#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>

#include "paradox.h"

/*
 * OHOS-native test (HarmonyOS PC, OHOS aarch64).
 *
 * pxlib upstream ships no test suite, so this executable covers the
 * HarmonyOS-specific behaviors the adaptation depends on:
 *
 *   1. OHOS toolchain identity — the conan OHOS profile maps os=OHOS to
 *      CMAKE_SYSTEM_NAME=HarmonyOS (conan CMakeToolchain); CMakeLists
 *      turns that on into the OHOS_TARGET compile definition.  It is
 *      absent on every other platform, where this whole test skips.
 *   2. HMDFS /tmp is read-only — scratch files must not target /tmp.
 *   3. $HOME/tmp fallback works end-to-end — pxlib opens a minimal
 *      Paradox 4.x header through the OHOS scratch path.
 */

/* Minimal *valid* Paradox database header, same layout as test_pxlib.c
 * (recordSize/headerSize/fileType/maxTableSize/fileVersionID set to
 * plausible Paradox 4.x values, rest zero). */
static int write_min_paradox(const char *path)
{
    FILE *fp = fopen(path, "wb");
    if (!fp)
        return -1;

    unsigned char hdr[512];
    memset(hdr, 0, sizeof(hdr));

    hdr[0x00] = 0x00; /* recordSize  = 512 (non-zero)   */
    hdr[0x01] = 0x02;
    hdr[0x02] = 0x00; /* headerSize  = 512 (non-zero)   */
    hdr[0x03] = 0x02;
    hdr[0x04] = 0;    /* fileType    = 0 (in [0, 8])    */
    hdr[0x05] = 16;   /* maxTableSize = 16 (in [1, 32]) */
    hdr[0x39] = 5;    /* fileVersionID = 5 (in [3, 15]) */

    fwrite(hdr, 1, sizeof(hdr), fp);
    fclose(fp);
    return 0;
}

static const char *ohos_scratch_path(void)
{
    const char *home = getenv("HOME");
    if (!home)
        home = ".";
    static char buf[512];
    snprintf(buf, sizeof(buf), "%s/tmp/pxlib_ohos_min.par", home);

    /* $HOME/tmp may not exist on CI workers; create best-effort. */
    static char tmpdir[256];
    snprintf(tmpdir, sizeof(tmpdir), "%s/tmp", home);
    mkdir(home, 0700);
    mkdir(tmpdir, 0700);
    return buf;
}

/* [1/3] Build-time platform identification. */
static int test_ohos_identity(void)
{
#if defined(OHOS_TARGET)
    printf("  [1/3] OHOS toolchain identity: CMAKE_SYSTEM_NAME=HarmonyOS "
           "-> OHOS_TARGET=1\n");
    return 0;
#else
    printf("  [1/3] SKIP: not an OHOS (HarmonyOS) build\n");
    return -1;
#endif
}

/* [2/3] The HMDFS /tmp partition of HarmonyOS PC is read-only. */
static int test_tmp_readonly(void)
{
    char probe[256];
    snprintf(probe, sizeof(probe), "/tmp/pxlib_ohos_probe.%d", (int)getpid());

    int fd = open(probe, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    int saved = errno;
    if (fd >= 0)
    {
        close(fd);
        remove(probe);
        printf("  [2/3] FAIL: /tmp is writable, expected read-only (HMDFS)\n");
        return 1;
    }
    if (saved != EROFS)
    {
        printf("  [2/3] FAIL: /tmp open failed with errno=%d, "
               "expected EROFS(%d)\n", saved, EROFS);
        return 1;
    }
    printf("  [2/3] HMDFS /tmp read-only: open(O_CREAT) -> EROFS\n");
    return 0;
}

/* [3/3] The $HOME/tmp fallback path works end-to-end with pxlib. */
static int test_home_tmp_pxlib(void)
{
    const char *path = ohos_scratch_path();

    if (0 != write_min_paradox(path))
    {
        printf("  [3/3] FAIL: cannot create scratch file at %s (errno=%d)\n",
               path, errno);
        return 1;
    }

    pxdoc_t *px = PX_new();
    if (!px)
    {
        printf("  [3/3] FAIL: PX_new\n");
        remove(path);
        return 1;
    }

    int rc = PX_open_file(px, path);
    int fileversion = (px->px_head) ? px->px_head->px_fileversion : -1;
    PX_close(px);
    remove(path);

    if (0 != rc)
    {
        printf("  [3/3] FAIL: PX_open_file rc=%d on OHOS scratch path\n", rc);
        return 1;
    }
    /* pxlib maps the raw fileVersionID to its internal scale
     * (src/px_head.c): Paradox 4.0 (fileVersionID=5) -> 40. */
    if (40 != fileversion)
    {
        printf("  [3/3] FAIL: fileversion=%d, expected 40 (Paradox 4.0)\n",
               fileversion);
        return 1;
    }
    printf("  [3/3] $HOME/tmp scratch + PX_open_file OK (Paradox 4.0 -> 40)\n");
    return 0;
}

int main(void)
{
    printf("test_ohos: HarmonyOS PC native checks\n");

    if (test_ohos_identity() < 0)
    {
        printf("test_ohos: SKIP (non-OHOS platform)\n");
        return 0;
    }

    int failures = test_tmp_readonly() + test_home_tmp_pxlib();
    if (failures)
    {
        printf("test_ohos: FAIL (%d check(s))\n", failures);
        return 1;
    }

    printf("test_ohos: PASS\n");
    return 0;
}
