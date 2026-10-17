/* Consumer test: real 2x2x2 C2C round trip through the packaged SpFFT
 * (backward with scaling, then forward without scaling => the frequency
 * data must come back multiplied by the total number of points). */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "spfft/spfft.h"

int main(void) {
    const int dimX = 2, dimY = 2, dimZ = 2;
    const int numFreq = dimX * dimY * dimZ;
    const int localZ = dimZ;
    int fails = 0;

    double *freq = malloc(2 * sizeof(double) * numFreq);
    int *indices = malloc(3 * sizeof(int) * numFreq);
    double init = 0.0;
    size_t c = 0;
    for (int x = 0; x < dimX; ++x)
        for (int y = 0; y < dimY; ++y)
            for (int z = 0; z < dimZ; ++z, ++c) {
                freq[2 * c] = init;
                freq[2 * c + 1] = -init;
                indices[3 * c] = x;
                indices[3 * c + 1] = y;
                indices[3 * c + 2] = z;
                init += 1.0;
            }

    SpfftGrid grid;
    SpfftTransform transform;
    SpfftError st = SPFFT_SUCCESS;

    st = spfft_grid_create(&grid, dimX, dimY, dimZ, dimX * dimY,
                           SPFFT_PU_HOST, -1);
    if (st != SPFFT_SUCCESS) { printf("FAIL: grid create %d\n", (int)st); return 1; }
    st = spfft_transform_create(&transform, grid, SPFFT_PU_HOST,
                                SPFFT_TRANS_C2C, dimX, dimY, dimZ, localZ,
                                numFreq, SPFFT_INDEX_TRIPLETS, indices);
    if (st != SPFFT_SUCCESS) { printf("FAIL: transform create %d\n", (int)st); return 1; }
    st = spfft_grid_destroy(grid);
    if (st != SPFFT_SUCCESS) { printf("FAIL: grid destroy %d\n", (int)st); return 1; }
    printf("[1] grid + transform created via packaged lib/headers\n");

    double *space = NULL;
    st = spfft_transform_get_space_domain(transform, SPFFT_PU_HOST, &space);
    if (st != SPFFT_SUCCESS) { printf("FAIL: get space domain %d\n", (int)st); return 1; }

    st = spfft_transform_backward(transform, freq, SPFFT_PU_HOST);
    if (st != SPFFT_SUCCESS) { printf("FAIL: backward %d\n", (int)st); return 1; }

    st = spfft_transform_forward_ptr(transform, space, freq, SPFFT_NO_SCALING);
    if (st != SPFFT_SUCCESS) { printf("FAIL: forward %d\n", (int)st); return 1; }
    printf("[2] backward + forward executed (round trip, no scaling)\n");

    /* round trip without forward scaling: freq' == freq * (dimX*dimY*dimZ) */
    for (size_t i = 0; i < (size_t)numFreq; ++i) {
        if (fabs(freq[2 * i] - 8.0 * (double)i) > 1e-9 ||
            fabs(freq[2 * i + 1] + 8.0 * (double)i) > 1e-9) {
            printf("FAIL: value mismatch at %zu\n", i);
            fails++;
        }
    }
    printf("[3] round-trip values exact (8x expected, tolerance 1e-9)\n");

    st = spfft_transform_destroy(transform);
    if (st != SPFFT_SUCCESS) { printf("FAIL: transform destroy\n"); fails++; }
    free(freq);
    free(indices);
    printf("[4] transform destroyed cleanly\n");

    if (fails == 0) {
        printf("consumer assertions: 4/4 PASS\n");
        return 0;
    }
    printf("consumer assertions: FAILED (%d)\n", fails);
    return 1;
}
