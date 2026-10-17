#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "hdcpapi.h"

/* Real API calls against libhdcpsdk: parameter validation paths return
 * deterministic errors without requiring a running hdcpd daemon. */
int main(void)
{
    int failed = 0;

    /* NULL handle must be rejected with INVALID_PARAMETER. */
    HDCP_STATUS st = HDCPCreate(NULL, NULL, NULL);
    if (st != HDCP_STATUS_ERROR_INVALID_PARAMETER) {
        fprintf(stderr, "FAIL: HDCPCreate(NULL) returned %d, expected %d\n",
                (int)st, (int)HDCP_STATUS_ERROR_INVALID_PARAMETER);
        failed = 1;
    } else {
        printf("PASS: HDCPCreate(NULL) rejected with INVALID_PARAMETER\n");
    }

    /* NULL port status buffer must be rejected with INVALID_PARAMETER. */
    st = HDCPGetStatus(0, 0, NULL);
    if (st != HDCP_STATUS_ERROR_INVALID_PARAMETER) {
        fprintf(stderr, "FAIL: HDCPGetStatus(NULL status) returned %d, expected %d\n",
                (int)st, (int)HDCP_STATUS_ERROR_INVALID_PARAMETER);
        failed = 1;
    } else {
        printf("PASS: HDCPGetStatus(NULL) rejected with INVALID_PARAMETER\n");
    }

    if (failed) {
        return 1;
    }
    printf("intel-hdcp SDK API smoke test OK\n");
    return 0;
}