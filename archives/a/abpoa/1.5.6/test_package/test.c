#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <abpoa.h>

/* nt4 lookup: AaCcGgTtNn -> 0,1,2,3,4 */
static unsigned char nt4_table[256] = {
    0, 1, 2, 3,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 0, 4, 1,  4, 4, 4, 2,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 4, 4, 4,  3, 3, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 0, 4, 1,  4, 4, 4, 2,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 4, 4, 4,  3, 3, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
    4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4
};

int main(void) {
    int i, j, ret;
    int n_seqs = 3;
    char seqs[3][100] = {
        "CGATCGATCGATCGATCGATCGATCGATCGAT",
        "CGATCGATCGATCGATCGATCGATCGATCGATCGAT",
        "CGATCGATCGATCGATCGATCGATCGAT"
    };

    /* abpoa_init_para(): allocate and initialize default parameters */
    abpoa_para_t *abpt = abpoa_init_para();
    if (abpt == NULL) {
        fprintf(stderr, "FAIL: abpoa_init_para() returned NULL\n");
        return 1;
    }

    /* abpoa_init(): allocate and initialize abpoa object */
    abpoa_t *ab = abpoa_init();
    if (ab == NULL) {
        fprintf(stderr, "FAIL: abpoa_init() returned NULL\n");
        abpoa_free_para(abpt);
        return 1;
    }

    /* set output options */
    abpt->out_msa  = 1;
    abpt->out_cons = 1;
    abpt->w = 6; abpt->k = 9; abpt->min_w = 10;
    abpt->progressive_poa = 0;
    abpt->max_n_cons = 1;
    abpoa_post_set_para(abpt);

    /* convert sequences to internal representation */
    int *seq_lens = (int*)malloc(sizeof(int) * n_seqs);
    if (seq_lens == NULL) {
        fprintf(stderr, "FAIL: malloc(seq_lens) returned NULL\n");
        abpoa_free(ab); abpoa_free_para(abpt);
        return 1;
    }
    uint8_t **bseqs = (uint8_t**)malloc(sizeof(uint8_t*) * n_seqs);
    if (bseqs == NULL) {
        fprintf(stderr, "FAIL: malloc(bseqs) returned NULL\n");
        free(seq_lens);
        abpoa_free(ab); abpoa_free_para(abpt);
        return 1;
    }
    for (i = 0; i < n_seqs; ++i) {
        seq_lens[i] = (int)strlen(seqs[i]);
        bseqs[i] = (uint8_t*)malloc(sizeof(uint8_t) * seq_lens[i]);
        if (bseqs[i] == NULL) {
            fprintf(stderr, "FAIL: malloc(bseqs[%d]) returned NULL\n", i);
            for (j = 0; j < i; ++j) free(bseqs[j]);
            free(bseqs); free(seq_lens);
            abpoa_free(ab); abpoa_free_para(abpt);
            return 1;
        }
        for (j = 0; j < seq_lens[i]; ++j)
            bseqs[i][j] = nt4_table[(int)seqs[i][j]];
    }

    /* run abpoa_msa: perform partial order alignment */
    ret = abpoa_msa(ab, abpt, n_seqs, NULL, seq_lens, bseqs, NULL, NULL);
    if (ret != 0) {
        fprintf(stderr, "FAIL: abpoa_msa() returned %d\n", ret);
        for (i = 0; i < n_seqs; ++i) free(bseqs[i]);
        free(bseqs); free(seq_lens);
        abpoa_free(ab); abpoa_free_para(abpt);
        return 1;
    }

    /* verify that consensus was generated */
    if (ab->abc == NULL || ab->abc->n_cons < 1) {
        fprintf(stderr, "FAIL: no consensus sequence generated\n");
        for (i = 0; i < n_seqs; ++i) free(bseqs[i]);
        free(bseqs); free(seq_lens);
        abpoa_free(ab); abpoa_free_para(abpt);
        return 1;
    }

    /* cleanup */
    for (i = 0; i < n_seqs; ++i) free(bseqs[i]);
    free(bseqs); free(seq_lens);
    abpoa_free(ab); abpoa_free_para(abpt);

    printf("test abpoa 1.5.6: OK\n");
    return 0;
}
