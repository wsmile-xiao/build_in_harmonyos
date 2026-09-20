#include <stdio.h>
#include <hugetlbfs.h>

int main(void) {
    /* Consumer contract test: link libhugetlbfs and exercise the page-size
     * query API. OHOS has no hugetlbfs (/proc/meminfo has no HugePages_*), so
     * gethugepagesize()/getpagesizes() are expected to report failure — the
     * contract verified here is that the symbols resolve and the calls return
     * without crashing (R34: real API calls, not a print-only stub). */
    long hps = gethugepagesize();
    long pagesizes[16];
    int n = getpagesizes(pagesizes, 16);

    printf("libhugetlbfs 2.24: gethugepagesize=%ld, getpagesizes=%d\n", hps, n);
    return 0;
}
