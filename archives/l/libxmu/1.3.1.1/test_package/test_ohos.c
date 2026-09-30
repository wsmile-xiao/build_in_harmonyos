/*
 * libxmu 1.3.1.1 Conan test_package — HarmonyOS-specific assertions (rule12).
 *
 * Exercises XmuReadBitmapDataFromFile() (libXmu, Xt-linked component) on the
 * platform behaviours HarmonyOS changes with respect to glibc/Linux:
 *
 *   A1  a well-formed X11 bitmap must be parsed back with the declared size;
 *   A2  malformed content must yield the deterministic BitmapFileInvalid
 *       code — the function must not abort or leave garbage in *datap;
 *   A3  a path that does not exist must yield the deterministic
 *       BitmapOpenFailed code.  This is the HarmonyOS-relevant case: the
 *       HMFS root filesystem is read-only and there is no
 *       /usr/share/X11/bitmaps, so every lookup misses and the library has to
 *       degrade to an error code instead of calling abort()/exiting.
 *
 * Upstream coverage: test/ReadBitmapData.c only ever feeds the three bundled
 * bitmaps (plaid/star/xlogo64) from a writable source dir, so it never reaches
 * the open-failure or malformed-input paths above.
 */
#include <stdio.h>
#include <stdlib.h>

#include <X11/Xmu/Drawing.h>
#include <X11/Xutil.h>

#define BITMAP_PATH "./libxmu-ohos-bitmap.xbm"

static const char valid_bitmap[] =
    "#define ohos_probe_width 8\n"
    "#define ohos_probe_height 8\n"
    "static unsigned char ohos_probe_bits[] = {\n"
    "   0x81, 0x42, 0x24, 0x18, 0x18, 0x24, 0x42, 0x81 };\n";

static int failures;

static void check(int ok, const char *label, int rc, int expected)
{
    if (ok) {
        printf("ok - %s (rc=%d)\n", label, rc);
    } else {
        printf("not ok - %s (rc=%d, expected %d)\n", label, rc, expected);
        failures++;
    }
}

static void report(const char *msg, int rc, int expected)
{
    printf("not ok - %s (rc=%d, expected %d)\n", msg, rc, expected);
    failures++;
}

int main(void)
{
    unsigned int width = 0;
    unsigned int height = 0;
    unsigned char *data = NULL;
    int x_hot = -1;
    int y_hot = -1;
    int rc;
    FILE *stream;

    /* A1 — well-formed bitmap is parsed back at the declared size. */
    stream = fopen(BITMAP_PATH, "w");
    if (stream == NULL) {
        report("A1 create fixture bitmap", 0, 0);
        return 1;
    }
    fputs(valid_bitmap, stream);
    fclose(stream);

    rc = XmuReadBitmapDataFromFile(BITMAP_PATH, &width, &height, &data,
                                   &x_hot, &y_hot);
    check(rc == BitmapSuccess && width == 8 && height == 8 && data != NULL,
          "A1 parse 8x8 X11 bitmap from a writable path", rc, BitmapSuccess);
    free(data);
    data = NULL;
    remove(BITMAP_PATH);

    /* A2 — malformed content degrades to BitmapFileInvalid. */
    stream = fopen(BITMAP_PATH, "w");
    if (stream == NULL) {
        report("A2 create fixture bitmap", 0, 0);
        return 1;
    }
    fputs("this is not an X11 bitmap\n", stream);
    fclose(stream);

    width = 0;
    height = 0;
    rc = XmuReadBitmapDataFromFile(BITMAP_PATH, &width, &height, &data,
                                   &x_hot, &y_hot);
    check(rc == BitmapFileInvalid,
          "A2 malformed bitmap returns BitmapFileInvalid", rc,
          BitmapFileInvalid);
    free(data);
    data = NULL;
    remove(BITMAP_PATH);

    /* A3 — missing path on the read-only root degrades to BitmapOpenFailed. */
    rc = XmuReadBitmapDataFromFile("/libxmu-no-such-bitmap.xbm", &width,
                                   &height, &data, &x_hot, &y_hot);
    check(rc == BitmapOpenFailed,
          "A3 absent bitmap path returns BitmapOpenFailed", rc,
          BitmapOpenFailed);
    free(data);

    if (failures != 0) {
        printf("FAIL: %d HarmonyOS assertion(s) failed\n", failures);
        return 1;
    }
    printf("PASS: libXmu HarmonyOS bitmap-degradation assertions\n");
    return 0;
}
