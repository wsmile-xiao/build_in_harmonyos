/* sample_consumer.c — consumer feasibility input for the lgrind test_package.
 * Exercises C procedure recognition, types, control flow and comments,
 * which the consumer test asserts via \Proc{main} in the generated LaTeX. */
#include <stdio.h>

/* compute the n-th triangular number */
static long triangular(int n)
{
    long sum = 0;
    for (int i = 1; i <= n; ++i) {
        sum += i;           /* accumulate */
    }
    return sum;
}

int main(void)
{
    printf("tri(10)=%ld\n", triangular(10));
    return 0;
}
