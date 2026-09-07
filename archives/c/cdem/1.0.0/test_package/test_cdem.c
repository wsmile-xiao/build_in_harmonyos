#include <cdem/cdem.h>

#include <stdio.h>
#include <string.h>

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s\n", msg); \
        failures++; \
    } \
} while (0)

int main(void) {
    int failures = 0;

    CHECK(cdem_version_major() == 1, "version major should be 1");
    CHECK(cdem_version_minor() == 0, "version minor should be 0");
    CHECK(cdem_version_patch() == 0, "version patch should be 0");
    CHECK(strcmp(cdem_version_string(), "1.0.0") == 0, "version string should be 1.0.0");

    cdem_meter_t *meter = cdem_create();
    CHECK(meter != NULL, "cdem_create should return non-null");
    if (meter) {
        const char *telegram = "1-0:1.8.0*255(001234.567*kWh)\n0-0:96.1.4*255(12345678901234567890123456789012)\n!ABCD\n";
        unsigned int lines = 0;
        int rc = cdem_parse_telegram(meter, telegram, &lines);
        CHECK(rc == 0, "cdem_parse_telegram should succeed");
        CHECK(lines == 3, "telegram line count should be 3");
        CHECK(cdem_get_line_count(meter) == 3, "cdem_get_line_count should be 3");
        cdem_destroy(meter);
        CHECK(cdem_get_line_count(NULL) == -1, "NULL meter should return -1");
    }

    if (failures != 0) {
        fprintf(stderr, "cdem consumer test failed: %d assertion(s)\n", failures);
        return 1;
    }
    puts("cdem consumer test passed: 9 assertions");
    return 0;
}
