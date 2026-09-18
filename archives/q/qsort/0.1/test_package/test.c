#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "qsort.h"

/* 消费者用例：使用 qsort.h 的 QSORT 宏对整数数组排序（Sedgewick 1978 宏实现） */
static int verify_sorted(const int *A, size_t n)
{
    size_t i;
    for (i = 1; i < n; i++) {
        if (A[i - 1] > A[i]) {
            return -1;
        }
    }
    return 0;
}

int main(void)
{
    int A[10] = {9, 2, 7, 1, 5, 8, 3, 6, 4, 0};
    int tmp;
    size_t n = sizeof(A) / sizeof(A[0]);

#define LESS(i, j) A[i] < A[j]
#define SWAP(i, j) tmp = A[i], A[i] = A[j], A[j] = tmp
    QSORT(n, LESS, SWAP);
#undef LESS
#undef SWAP

    if (verify_sorted(A, n) != 0) {
        fprintf(stderr, "qsort test FAILED: array not sorted\n");
        return 1;
    }
    printf("qsort consumer test OK: sorted %zu ints, first=%d last=%d\n",
           n, A[0], A[n - 1]);
    return 0;
}
