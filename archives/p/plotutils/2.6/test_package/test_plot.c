#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <plot.h>

int main(void) {
    if (strcmp(pl_libplot_ver, PL_LIBPLOT_VER_STRING) != 0) {
        fprintf(stderr, "version mismatch: runtime=%s headers=%s\n",
                pl_libplot_ver, PL_LIBPLOT_VER_STRING);
        return 1;
    }

    plPlotterParams *params = pl_newplparams();
    if (params == NULL) {
        fprintf(stderr, "FAIL: pl_newplparams returned NULL\n");
        return 2;
    }

    pl_setplparam(params, "PAGESIZE", "letter");

    FILE *null_in = fopen("/dev/null", "r");
    if (!null_in) {
        null_in = fopen("test_probe_null.bin", "w+");
    }
    FILE *out = fopen("test_probe_png.bin", "w+");
    FILE *err = fopen("test_probe_err.txt", "w+");
    if (!null_in || !out || !err) {
        fprintf(stderr, "FAIL: could not open streams (null_in=%p out=%p err=%p)\n",
                (void *)null_in, (void *)out, (void *)err);
        if (null_in) fclose(null_in);
        if (out) fclose(out);
        if (err) fclose(err);
        pl_deleteplparams(params);
        return 3;
    }

    plPlotter *plotter = pl_newpl_r("png", null_in, out, err, params);
    if (plotter == NULL) {
        fprintf(stderr, "FAIL: pl_newpl_r returned NULL (PNG driver unavailable)\n");
        fclose(null_in);
        fclose(out);
        fclose(err);
        pl_deleteplparams(params);
        return 4;
    }

    if (pl_openpl_r(plotter) < 0) {
        fprintf(stderr, "FAIL: pl_openpl_r failed\n");
        pl_deletepl_r(plotter);
        pl_deleteplparams(params);
        fclose(null_in);
        fclose(out);
        fclose(err);
        return 5;
    }

    pl_space_r(plotter, 0, 0, 100, 100);
    pl_move_r(plotter, 10, 10);
    pl_line_r(plotter, 10, 10, 90, 90);
    pl_box_r(plotter, 20, 20, 80, 80);
    pl_label_r(plotter, "test");

    if (pl_closepl_r(plotter) < 0) {
        fprintf(stderr, "FAIL: pl_closepl_r failed\n");
        pl_deletepl_r(plotter);
        pl_deleteplparams(params);
        fclose(null_in);
        fclose(out);
        fclose(err);
        return 6;
    }

    if (pl_deletepl_r(plotter) < 0) {
        fprintf(stderr, "FAIL: pl_deletepl_r failed\n");
        pl_deleteplparams(params);
        fclose(null_in);
        fclose(out);
        fclose(err);
        return 7;
    }

    pl_deleteplparams(params);
    fclose(null_in);

    fflush(out);
    fseek(out, 0, SEEK_SET);
    unsigned char hdr[8];
    size_t n = fread(hdr, 1, 8, out);
    fclose(out);
    fclose(err);

    if (n < 8) {
        fprintf(stderr, "FAIL: PNG output too short (%zu bytes)\n", n);
        return 8;
    }
    unsigned char png_sig[8] = {0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A};
    if (memcmp(hdr, png_sig, 8) != 0) {
        fprintf(stderr, "FAIL: output is not a valid PNG (bad signature)\n");
        return 9;
    }

    printf("PASS: plotutils 2.6 libplot PNG smoke test OK (version %s)\n", pl_libplot_ver);
    return 0;
}
