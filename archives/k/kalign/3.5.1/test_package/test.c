#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "kalign/kalign.h"

int main(void) {
    /* Two short protein sequences for a minimal alignment test */
    char *seq[] = {
        "MKVLWAITAIL",
        "MKVLYITAIL",
    };
    int len[] = { 11, 10 };
    int numseq = 2;

    char **aligned = NULL;
    int out_aln_len = 0;

    int ret = kalign(seq, len, numseq,
                     1,            /* n_threads */
                     KALIGN_TYPE_PROTEIN,
                     -1.53f,       /* gpo */
                     -0.0f,        /* gpe */
                     -0.0f,        /* tgpe */
                     &aligned,
                     &out_aln_len);

    if (ret != 0) {
        fprintf(stderr, "kalign() returned %d\n", ret);
        return 1;
    }
    if (!aligned || out_aln_len <= 0) {
        fprintf(stderr, "kalign() produced no alignment\n");
        return 1;
    }

    printf("aligned length: %d\n", out_aln_len);
    for (int i = 0; i < numseq; i++) {
        printf("seq %d: %.*s\n", i, out_aln_len, aligned[i]);
    }

    free(aligned[0]);
    free(aligned[1]);
    free(aligned);

    printf("OK\n");
    return 0;
}
