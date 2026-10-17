#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "camellia.h"

#define CHECK(cond) do { \
    if (!(cond)) { printf("CHECK FAILED at line %d: %s\n", __LINE__, #cond); exit(1); } \
    printf("ok line %d\n", __LINE__); \
} while (0)

int main(void) {
    /* 1. image allocation and header setup */
    CamImage img;
    CHECK(camAllocateImage(&img, 64, 48, CAM_DEPTH_8U) == 1);
    CHECK(img.width == 64 && img.height == 48);
    camFreeImage(&img);

    /* 2. draw, save PGM, load PGM round trip */
    CamImage src;
    CHECK(camAllocateImage(&src, 32, 32, CAM_DEPTH_8U) == 1);
    memset(src.imageData, 0, src.imageSize);
    CHECK(camDrawRectangle(&src, 8, 8, 23, 23, 255) == 1);
    CHECK(camFillColor(&src, 12, 12, 255, -1) == 196);
    CHECK(src.imageData[12 * src.width + 12] == 255);
    CHECK(src.imageData[9 * src.width + 9] == 255);
    CHECK(camSavePGM(&src, "camellia_test_in.pgm") == 1);

    CamImage dst;
    CHECK(camLoadPGM(&dst, "camellia_test_in.pgm") == 1);
    CHECK(dst.width == 32 && dst.height == 32);
    CHECK(dst.imageData[16 * dst.width + 16] == 255);
    CHECK(dst.imageData[0] == 0);

    /* 3. RLE encode/decode round trip with identity LUT */
    CamRLEImage rle;
    memset(&rle, 0, sizeof(rle));
    CHECK(camRLEEncode(&dst, &rle) == 1);
    CamImage decoded;
    CHECK(camAllocateImage(&decoded, 32, 32, CAM_DEPTH_8U) == 1);
    CamTable lut;
    memset(&lut, 0, sizeof(lut));
    int i;
    for (i = 0; i < 256; i++) lut.t[i] = i;
    CHECK(camRLEDecode(&rle, &decoded, &lut) == 1);
    CHECK(decoded.imageData[16 * decoded.width + 16] == 255);
    CHECK(decoded.imageData[0] == 0);

    /* 4. labeling + blob analysis: background and the 16x16 square */
    CamImage dest;
    CHECK(camAllocateImage(&dest, 32, 32, CAM_DEPTH_16U) == 1);
    CamLabelingResults info;
    memset(&info, 0, sizeof(info));
    CHECK(camLabeling(&dst, &dest, &info) == 1);
    CamBlobs blobs;
    memset(&blobs, 0, sizeof(blobs));
    CHECK(camBlobAnalysis1stScan(&dest, &dst, &info, &blobs) == 1);
    printf("nbBlobs=%d\n", blobs.nbBlobs);
    CHECK(blobs.nbBlobs == 2);
    int square = -1;
    for (i = 0; i < blobs.nbBlobs; i++) {
        if (blobs.blobInfo[i].value == 255) square = i;
    }
    CHECK(square >= 0);
    printf("square surface=%d\n", blobs.blobInfo[square].surface);
    CHECK(blobs.blobInfo[square].surface == 16 * 16);
    CHECK(blobs.blobInfo[square].min == 255 && blobs.blobInfo[square].max == 255);

    camFreeImage(&src); camFreeImage(&dst); camFreeImage(&decoded);
    camFreeImage(&dest); camRLEFree(&rle);
    printf("CAMELLIA TEST OK\n");
    return 0;
}
