#include <stdio.h>
#include <stdlib.h>
#include <histedit.h>

int main(void) {
    /* Test 1: Initialize history */
    History *hist = history_init();
    if (hist == NULL) {
        fprintf(stderr, "FAIL: history_init() returned NULL\n");
        return 1;
    }

    HistEvent ev;

    /* Test 2: Enter a history entry (H_ENTER adds and returns entry number) */
    int rc = history(hist, &ev, H_ENTER, "test command");
    if (rc == -1) {
        fprintf(stderr, "FAIL: history(H_ENTER) returned -1\n");
        history_end(hist);
        return 1;
    }

    /* Verify the entry was assigned a number */
    if (ev.num <= 0) {
        fprintf(stderr, "FAIL: history entry number is %d (expected > 0)\n", ev.num);
        history_end(hist);
        return 1;
    }

    /* Test 3: Add another entry */
    rc = history(hist, &ev, H_ADD, "second command");
    if (rc == -1) {
        fprintf(stderr, "FAIL: history(H_ADD) returned -1\n");
        history_end(hist);
        return 1;
    }

    /* Test 4: Clean up */
    history_end(hist);

    printf("test libedit 20240808: OK (history API works, entries added)\n");
    return 0;
}
