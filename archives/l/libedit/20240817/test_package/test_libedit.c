#include <stdio.h>
#include <histedit.h>
int main(void) {
    EditLine *el = el_init("test_libedit", stdin, stdout, stderr);
    if (el == NULL) { fprintf(stderr, "FAIL: el_init\n"); return 1; }
    printf("PASS: el_init\n");
    el_end(el);
    printf("PASS: el_end\n");
    History *hist = history_init();
    if (hist == NULL) { fprintf(stderr, "FAIL: history_init\n"); return 1; }
    printf("PASS: history_init\n");
    history_end(hist);
    printf("PASS: history_end\n");
    printf("All libedit smoke tests PASSED\n");
    return 0;
}
