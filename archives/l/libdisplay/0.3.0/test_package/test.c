#include <stddef.h>
#include <libdisplay-info/info.h>

/*
 * Test: verify libdisplay-info API is callable and behaves correctly.
 * Calls di_info_parse_edid with invalid data (all zeros) and a too-small
 * buffer, checking that it correctly returns NULL for invalid input.
 * This proves the library is properly linked and the API functions work.
 */
int main(void)
{
    /* Test 1: Invalid EDID (all zeros) should return NULL */
    unsigned char invalid_edid[128] = {0};
    struct di_info *info = di_info_parse_edid(invalid_edid, sizeof(invalid_edid));
    if (info != NULL) {
        di_info_destroy(info);
        return 1;
    }

    /* Test 2: Too-small buffer should return NULL */
    info = di_info_parse_edid(invalid_edid, 10);
    if (info != NULL) {
        di_info_destroy(info);
        return 1;
    }

    return 0;
}
