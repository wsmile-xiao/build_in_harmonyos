/* Consumer test for the installed minimap library (libminimap.a + headers).
 * Mirrors upstream example.c: build an index, map one query and count hits. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <assert.h>

#include <minimap.h>

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: test_minimap_consumer <target.fa> <query.fa>\n");
        return 2;
    }
    mm_idx_t *mi = mm_idx_build(argv[1], 4, 7, 1); /* w=4, k=7 */
    assert(mi);

    mm_mapopt_t opt;
    mm_mapopt_init(&opt);
    mm_tbuf_t *tbuf = mm_tbuf_init();

    FILE *fp = fopen(argv[2], "r");
    assert(fp);
    char name[256];
    static char seq[1 << 16];
    int total = 0;
    while (fscanf(fp, ">%255s", name) == 1) {
        if (fscanf(fp, "%65535s", seq) != 1) {
            break;
        }
        int n_reg = 0;
        mm_map(mi, (int)strlen(seq), seq, &n_reg, tbuf, &opt, 0);
        total += n_reg;
    }
    fclose(fp);

    mm_tbuf_destroy(tbuf);
    mm_idx_destroy(mi);

    printf("minimap consumer hits=%d\n", total);
    return total > 0 ? 0 : 1;
}
