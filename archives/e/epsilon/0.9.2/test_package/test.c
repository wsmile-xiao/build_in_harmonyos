#include <stdio.h>
#include <stdlib.h>
#include <epsilon.h>

int main(void) {
    /* Query the list of available wavelet filterbanks via the epsilon API */
    char **fb_names = eps_get_fb_info(EPS_FB_NAME);
    if (!fb_names) {
        fprintf(stderr, "FAIL: eps_get_fb_info returned NULL\n");
        return 1;
    }

    /* Count available filterbanks and verify the Haar filterbank is present */
    int count = 0;
    int found_haar = 0;
    for (int i = 0; fb_names[i]; i++) {
        count++;
        if (fb_names[i][0] != '\0') {
            printf("filterbank[%d]: %s\n", i, fb_names[i]);
            /* Check for the Haar filterbank which should always be available */
            if (fb_names[i][0] == 'H' && fb_names[i][1] == 'a' &&
                fb_names[i][2] == 'a' && fb_names[i][3] == 'r') {
                found_haar = 1;
            }
        }
    }

    eps_free_fb_info(fb_names);

    if (count == 0) {
        fprintf(stderr, "FAIL: no filterbanks found\n");
        return 1;
    }

    if (!found_haar) {
        fprintf(stderr, "FAIL: Haar filterbank not found\n");
        return 1;
    }

    /* Verify the maximum block size constant is defined correctly */
    if (EPS_MAX_BLOCK_SIZE != 1024) {
        fprintf(stderr, "FAIL: EPS_MAX_BLOCK_SIZE != 1024 (got %d)\n",
                EPS_MAX_BLOCK_SIZE);
        return 1;
    }

    /* Verify the minimum block size constant */
    if (EPS_MIN_BLOCK_SIZE != 32) {
        fprintf(stderr, "FAIL: EPS_MIN_BLOCK_SIZE != 32 (got %d)\n",
                EPS_MIN_BLOCK_SIZE);
        return 1;
    }

    printf("epsilon test PASSED: %d filterbanks found, Haar present, "
           "block size constants OK\n", count);
    return 0;
}
