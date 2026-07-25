#include <stdio.h>
#include <string.h>

/* R34: 实质调用被测包 API — mbedTLS 版本检查 */
#include <mbedtls/version.h>

int main(void) {
    const char *version_str = mbedtls_version_get_string_full();
    printf("mbedTLS version: %s\n", version_str);

    unsigned int version_number = mbedtls_version_get_number();
    printf("mbedTLS version number: %u\n", version_number);

    if (version_number > 0) {
        printf("mbedTLS test: OK\n");
        return 0;
    } else {
        printf("mbedTLS test: FAIL (version number is 0)\n");
        return 1;
    }
}
