/*
 * test_package consumer test for libharu 2.3.0.
 *
 * Uses the real libharu public API: create an in-memory PDF document,
 * add a page and a text block, then save it to a file and verify the
 * file exists and has non-zero size. This is a genuine API call chain
 * (HPDF_New / HPDF_AddPage / HPDF_Page_BeginText / HPDF_SaveToFile),
 * not a print-only stub.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "hpdf.h"

int main(void) {
    const char *out = "test_libharu.pdf";
    HPDF_Doc pdf;
    HPDF_Page page;

    pdf = HPDF_New(NULL, NULL);
    if (!pdf) {
        fprintf(stderr, "libharu: HPDF_New failed\n");
        return 1;
    }

    page = HPDF_AddPage(pdf);
    if (!page) {
        fprintf(stderr, "libharu: HPDF_AddPage failed\n");
        HPDF_Free(pdf);
        return 1;
    }
    HPDF_Page_SetWidth(page, 210);
    HPDF_Page_SetHeight(page, 297);

    if (HPDF_Page_BeginText(page) != HPDF_OK) {
        fprintf(stderr, "libharu: HPDF_Page_BeginText failed\n");
        HPDF_Free(pdf);
        return 1;
    }
    HPDF_Page_EndText(page);

    if (HPDF_SaveToFile(pdf, out) != HPDF_OK) {
        fprintf(stderr, "libharu: HPDF_SaveToFile failed\n");
        HPDF_Free(pdf);
        return 1;
    }
    HPDF_Free(pdf);

    {
        FILE *f = fopen(out, "rb");
        long size = 0;
        if (!f) {
            fprintf(stderr, "libharu: output file %s not found\n", out);
            return 1;
        }
        fseek(f, 0, SEEK_END);
        size = ftell(f);
        fclose(f);
        if (size <= 0) {
            fprintf(stderr, "libharu: output file %s is empty\n", out);
            return 1;
        }
        printf("libharu 2.3.0 consumer test OK: %s %ld bytes\n", out, size);
    }
    return 0;
}