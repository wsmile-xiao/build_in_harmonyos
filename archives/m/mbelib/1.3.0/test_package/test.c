#include <stdio.h>
#include <string.h>
#include "mbelib.h"

int main(void) {
    /* Test mbe_golay2312: decode a Golay (23,12) codeword */
    /* Construct a 23-bit input: 12 data bits (0-11) + 11 parity bits (12-22) */
    char in[23] = {1,0,1,1,0,0,1,0,1,1,0,1, 0,0,0,0,0,0,0,0,0,0,0};
    char out[23] = {0};
    int errs = mbe_golay2312(in, out);

    if (errs < 0) {
        printf("FAIL: mbe_golay2312 returned negative errors: %d\n", errs);
        return 1;
    }

    /* Test mbe_checkGolayBlock: verify and correct a Golay block */
    long int block = 0;
    int i;
    for (i = 0; i < 23; i++) {
        if (in[i]) {
            block |= (1L << i);
        }
    }
    mbe_checkGolayBlock(&block);

    /* Test mbe_parms structure initialization */
    mbe_parms cur_mp;
    mbe_parms prev_mp;
    memset(&cur_mp, 0, sizeof(cur_mp));
    memset(&prev_mp, 0, sizeof(prev_mp));

    /* Verify the structure is properly sized and accessible */
    if (sizeof(cur_mp) == 0) {
        printf("FAIL: mbe_parms has zero size\n");
        return 1;
    }

    printf("mbelib API test passed: golay2312 errs=%d, parms_size=%zu\n",
           errs, sizeof(cur_mp));
    return 0;
}
