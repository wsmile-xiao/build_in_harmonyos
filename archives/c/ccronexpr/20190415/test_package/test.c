#include <stdio.h>
#include <string.h>
#include <time.h>
#include "ccronexpr.h"

int main(void) {
    cron_expr expr;
    const char* err = NULL;
    memset(&expr, 0, sizeof(expr));
    
    /* Test 1: Parse a valid cron expression */
    cron_parse_expr("0 */2 1-4 * * *", &expr, &err);
    if (err) {
        printf("FAIL: parse error: %s\n", err);
        return 1;
    }
    printf("PASS: cron expression parsed successfully\n");
    
    /* Test 2: Calculate next execution time */
    time_t cur = 1341137630; /* 2012-07-01 09:53:50 */
    time_t next = cron_next(&expr, cur);
    if (next == (time_t)(-1)) {
        printf("FAIL: cron_next returned error\n");
        return 1;
    }
    
    struct tm* tm_next = localtime(&next);
    printf("Next execution: %04d-%02d-%02d %02d:%02d:%02d\n",
           tm_next->tm_year + 1900, tm_next->tm_mon + 1, tm_next->tm_mday,
           tm_next->tm_hour, tm_next->tm_min, tm_next->tm_sec);
    
    /* Test 3: Invalid expression should fail */
    cron_parse_expr("invalid cron", &expr, &err);
    if (!err) {
        printf("FAIL: should reject invalid expression\n");
        return 1;
    }
    printf("PASS: invalid expression correctly rejected\n");
    
    printf("test ccronexpr 20190415: ALL TESTS PASSED\n");
    return 0;
}
