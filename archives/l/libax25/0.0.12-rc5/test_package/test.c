/*
 * test_libax25.c — L1 consumer test for libax25
 *
 * Calls actual libax25 API functions to verify the library is functional:
 *   - ax25_aton_entry(): convert ASCII callsign to network format
 *   - ax25_ntoa(): convert network format back to ASCII
 *   - ax25_validate(): validate a callsign
 */
#include <stdio.h>
#include <string.h>
#include <netax25/axlib.h>

int main(void)
{
    /* Test 1: Convert ASCII callsign to network format and back */
    char callsign[] = "VK2ABC-5";
    char network[7] = {0};  /* ax25_address is 7 bytes */

    int ret = ax25_aton_entry(callsign, network);
    if (ret < 0) {
        fprintf(stderr, "FAIL: ax25_aton_entry returned %d\n", ret);
        return 1;
    }
    printf("ax25_aton_entry(\"%s\") -> OK\n", callsign);

    /* Test 2: Convert back to ASCII */
    char *result = ax25_ntoa((const ax25_address *)network);
    if (result == NULL) {
        fprintf(stderr, "FAIL: ax25_ntoa returned NULL\n");
        return 1;
    }
    printf("ax25_ntoa() -> \"%s\"\n", result);

    /* Test 3: Validate a callsign (in network format) */
    int valid = ax25_validate(network);
    printf("ax25_validate(network) -> %s\n", valid ? "TRUE" : "FALSE");
    if (!valid) {
        fprintf(stderr, "FAIL: ax25_validate returned FALSE for valid callsign\n");
        return 1;
    }

    printf("All tests passed.\n");
    return 0;
}
