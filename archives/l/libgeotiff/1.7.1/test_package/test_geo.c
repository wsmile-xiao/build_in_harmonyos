/*
 * libgeotiff functional test — creates and reads a GeoTIFF file.
 * Tests: GTIFNew, GTIFKeySet, GTIFWriteKeys, GTIFKeyGet, GTIFFree, XTIFFOpen, XTIFFClose
 */
#include <geotiff.h>
#include <geo_normalize.h>
#include <geotiffio.h>
#include <xtiffio.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
    printf("=== libgeotiff functional test ===\n");

    /* --- Create a GeoTIFF file --- */
    printf("Creating test GeoTIFF file...\n");

    TIFF *tif = XTIFFOpen("test_geotiff_output.tif", "w");
    if (!tif) {
        printf("ERROR: Cannot create TIFF file\n");
        return 1;
    }

    /* Set basic TIFF tags */
    TIFFSetField(tif, TIFFTAG_IMAGEWIDTH, 100);
    TIFFSetField(tif, TIFFTAG_IMAGELENGTH, 100);
    TIFFSetField(tif, TIFFTAG_BITSPERSAMPLE, 8);
    TIFFSetField(tif, TIFFTAG_SAMPLESPERPIXEL, 1);
    TIFFSetField(tif, TIFFTAG_ROWSPERSTRIP, 100);
    TIFFSetField(tif, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK);
    TIFFSetField(tif, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);

    /* Create GeoTIFF handle */
    GTIF *gtif = GTIFNew(tif);
    if (!gtif) {
        printf("ERROR: GTIFNew failed\n");
        XTIFFClose(tif);
        return 1;
    }
    printf("GTIFNew: OK\n");

    /* Set a GeoTIFF key — PCS WGS84 UTM zone 33N */
    if (!GTIFKeySet(gtif, ProjectedCSTypeGeoKey, TYPE_SHORT, 1, PCS_WGS84_UTM_zone_33N)) {
        printf("ERROR: GTIFKeySet failed\n");
        GTIFFree(gtif);
        XTIFFClose(tif);
        return 1;
    }
    printf("GTIFKeySet ProjectedCSTypeGeoKey=PCS_WGS84_UTM_zone_33N: OK\n");

    /* Write pixel data */
    unsigned char *buf = (unsigned char *)calloc(100 * 100, 1);
    if (!buf) {
        printf("ERROR: calloc failed\n");
        GTIFFree(gtif);
        XTIFFClose(tif);
        return 1;
    }
    for (int i = 0; i < 100; i++) {
        memset(buf + i * 100, (unsigned char)(i * 2), 100);
    }
    for (int row = 0; row < 100; row++) {
        if (TIFFWriteScanline(tif, buf + row * 100, row, 0) < 0) {
            printf("ERROR: TIFFWriteScanline failed at row %d\n", row);
            free(buf);
            GTIFFree(gtif);
            XTIFFClose(tif);
            return 1;
        }
    }
    free(buf);

    /* Write GeoTIFF keys to the TIFF file */
    if (!GTIFWriteKeys(gtif)) {
        printf("ERROR: GTIFWriteKeys failed\n");
        GTIFFree(gtif);
        XTIFFClose(tif);
        return 1;
    }
    printf("GTIFWriteKeys: OK\n");

    /* Free resources */
    GTIFFree(gtif);
    XTIFFClose(tif);
    printf("GeoTIFF file created successfully.\n");

    /* --- Read back and verify --- */
    printf("\nReading back GeoTIFF file for verification...\n");

    tif = XTIFFOpen("test_geotiff_output.tif", "r");
    if (!tif) {
        printf("ERROR: Cannot reopen TIFF file\n");
        return 1;
    }

    gtif = GTIFNew(tif);
    if (!gtif) {
        printf("ERROR: GTIFNew (read) failed\n");
        XTIFFClose(tif);
        return 1;
    }
    printf("GTIFNew (read): OK\n");

    /* Read the GeoTIFF key back */
    unsigned short pcs = 0;
    int ret = GTIFKeyGet(gtif, ProjectedCSTypeGeoKey, &pcs, 0, 1);
    printf("GTIFKeyGet ProjectedCSTypeGeoKey: ret=%d, PCS=%d\n", ret, (int)pcs);

    if (ret > 0 && pcs == PCS_WGS84_UTM_zone_33N) {
        printf("VERIFY: PCS value correct (%d == %d)\n", (int)pcs, (int)PCS_WGS84_UTM_zone_33N);
        printf("\n=== FUNCTIONAL TEST: PASSED ===\n");
    } else {
        printf("VERIFY: PCS value mismatch (got %d, expected %d)\n", (int)pcs, (int)PCS_WGS84_UTM_zone_33N);
        printf("\n=== FUNCTIONAL TEST: FAILED ===\n");
        GTIFFree(gtif);
        XTIFFClose(tif);
        return 1;
    }

    GTIFFree(gtif);
    XTIFFClose(tif);
    return 0;
}
