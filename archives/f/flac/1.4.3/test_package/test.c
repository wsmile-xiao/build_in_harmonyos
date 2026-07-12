/* test_flac — Consumer test for flac conan package.
 * Verifies libFLAC is linkable and OGG support is enabled.
 */
#include <FLAC/format.h>
#include <FLAC/export.h>
#include <stdio.h>

int main(void) {
    printf("FLAC version: %s\n", FLAC__VERSION_STRING);
    printf("FLAC API version: %d\n", FLAC_API_VERSION_CURRENT);

    /* Verify OGG support is compiled in */
    if (FLAC_API_SUPPORTS_OGG_FLAC) {
        printf("OGG support: enabled\n");
    } else {
        printf("OGG support: disabled\n");
        return 1;
    }

    /* Verify format API works */
    if (FLAC__format_sample_rate_is_valid(44100)) {
        printf("Sample rate 44100: valid\n");
    } else {
        return 1;
    }

    printf("All tests passed.\n");
    return 0;
}
