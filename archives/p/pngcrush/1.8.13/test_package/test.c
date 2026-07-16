/*
 * test_package/test.c — functional smoke test for the pngcrush executable.
 *
 * pngcrush is a command-line application with no public library API, so the
 * test drives the installed binary: it writes a tiny valid PNG, asks pngcrush
 * to losslessly recompress it, and verifies that the result is still a PNG.
 */
#include <stdio.h>
#include <stdlib.h>

/* minimal valid 1x1 RGB PNG (69 bytes) */
static const unsigned char png_in[] = {
    0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a,0x00,0x00,0x00,0x0d,0x49,0x48,0x44,0x52,
    0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x01,0x08,0x02,0x00,0x00,0x00,0x90,0x77,0x53,
    0xde,0x00,0x00,0x00,0x0c,0x49,0x44,0x41,0x54,0x78,0x9c,0x63,0xf8,0xcf,0xc0,0x00,
    0x00,0x03,0x01,0x01,0x00,0xc9,0xfe,0x92,0xef,0x00,0x00,0x00,0x00,0x49,0x45,0x4e,
    0x44,0xae,0x42,0x60,0x82
};

int main(void) {
    FILE *fp = fopen("pc_test_in.png", "wb");
    if (!fp) {
        fprintf(stderr, "cannot create input PNG\n");
        return 1;
    }
    if (fwrite(png_in, 1, sizeof(png_in), fp) != sizeof(png_in)) {
        fprintf(stderr, "short write\n");
        fclose(fp);
        return 1;
    }
    fclose(fp);

    /* pngcrush: losslessly recompress pc_test_in.png -> pc_test_out.png */
    int rc = system("pngcrush -q pc_test_in.png pc_test_out.png");
    if (rc != 0) {
        fprintf(stderr, "pngcrush recompression failed\n");
        return 1;
    }

    FILE *out = fopen("pc_test_out.png", "rb");
    if (!out) {
        fprintf(stderr, "pngcrush produced no output\n");
        return 1;
    }
    unsigned char sig[8];
    size_t n = fread(sig, 1, 8, out);
    fclose(out);
    /* PNG signature: 89 50 4E 47 0D 0A 1A 0A */
    if (n != 8 || sig[0] != 0x89 || sig[1] != 0x50 || sig[2] != 0x4e ||
        sig[3] != 0x47 || sig[4] != 0x0d || sig[5] != 0x0a ||
        sig[6] != 0x1a || sig[7] != 0x0a) {
        fprintf(stderr, "output is not a PNG\n");
        return 1;
    }

    printf("pngcrush functional test passed\n");
    return 0;
}
