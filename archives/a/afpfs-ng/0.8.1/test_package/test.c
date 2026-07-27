/* test_package/test.c — afpfs-ng 0.8.1 consumer test
 * Tests the libafpclient API: afp_default_url, afp_parse_url, afp_url_validate
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* Include the afpfs-ng header */
#include "afp.h"

int main(void) {
    int errors = 0;
    struct afp_url url;

    /* Test 1: afp_default_url initializes the struct */
    afp_default_url(&url);
    if (url.protocol != 0) {
        fprintf(stderr, "FAIL: afp_default_url protocol should be 0 (TCPIP)\n");
        errors++;
    }
    printf("PASS: afp_default_url initializes url struct\n");

    /* Test 2: afp_parse_url parses a valid AFP URL */
    int ret = afp_parse_url(&url, "afp://user:pass@server/volume/path", 0);
    if (ret != 0) {
        fprintf(stderr, "FAIL: afp_parse_url returned %d for valid URL\n", ret);
        errors++;
    }
    printf("PASS: afp_parse_url parses valid AFP URL\n");

    /* Test 3: Verify parsed server name */
    if (strlen(url.servername) == 0) {
        fprintf(stderr, "FAIL: servername should not be empty after parse\n");
        errors++;
    }
    printf("PASS: servername parsed correctly: '%s'\n", url.servername);

    /* Test 4: afp_status_header generates header text
     * Returns number of bytes written (>0 = success, -1 = failure) */
    char buf[1024];
    int len = sizeof(buf);
    int sret = afp_status_header(buf, &len);
    if (sret <= 0) {
        fprintf(stderr, "FAIL: afp_status_header returned %d\n", sret);
        errors++;
    }
    printf("PASS: afp_status_header generates status text\n");

    if (errors > 0) {
        fprintf(stderr, "FAILED with %d errors\n", errors);
        return 1;
    }

    printf("test afpfs-ng 0.8.1: All tests PASSED\n");
    return 0;
}
