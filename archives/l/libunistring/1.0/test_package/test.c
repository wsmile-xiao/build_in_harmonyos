#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistr.h>

int main(void) {
    const uint8_t text[] = "HarmonyOS";
    size_t length = u8_strlen(text);
    if (length != strlen((const char *)text)) {
        return 1;
    }
    if (u8_check(text, length) != NULL) {
        return 2;
    }
    printf("libunistring smoke test passed: %zu\n", length);
    return 0;
}
