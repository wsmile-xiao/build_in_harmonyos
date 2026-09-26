/* naive-tsearch consumer entry point: runs both packaged flavours and
 * prints a machine-readable summary line for the PR statistics. */
#include <stdio.h>

#define CONSUMER_TOTAL_CHECKS 10

int run_static_checks(void);
int run_hdronly_checks(void);

int main(void)
{
    int static_failures;
    int hdronly_failures;
    int failures;

    printf("# naive-tsearch consumer assertions (static + header-only)\n");

    static_failures = run_static_checks();
    hdronly_failures = run_hdronly_checks();
    failures = static_failures + hdronly_failures;

    if (failures) {
        printf("FAIL: naive-tsearch consumer assertions %d/%d "
               "(static %d/5, hdronly %d/5)\n",
               CONSUMER_TOTAL_CHECKS - failures, CONSUMER_TOTAL_CHECKS,
               5 - static_failures, 5 - hdronly_failures);
        return 1;
    }

    printf("PASS: naive-tsearch consumer assertions %d/%d "
           "(static 5/5, hdronly 5/5)\n",
           CONSUMER_TOTAL_CHECKS, CONSUMER_TOTAL_CHECKS);
    return 0;
}
