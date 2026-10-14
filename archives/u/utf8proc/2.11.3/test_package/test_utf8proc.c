#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <utf8proc.h>

int main(void) {
    const utf8proc_uint8_t input[] = "Ae\xCC\x81";
    utf8proc_uint8_t *normalized = 0;
    const utf8proc_option_t options =
        UTF8PROC_STABLE | UTF8PROC_COMPOSE | UTF8PROC_NULLTERM;
    int length = utf8proc_map(input, 0, &normalized, options);
    if (length < 0 || normalized == 0) return 1;
    if (length != 3) return 2;
    if (strcmp((const char *)normalized, "A\xC3\xA9") != 0) return 3;
    free(normalized);
    return 0;
}
