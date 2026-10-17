#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistr.h>

int main(void) {
    const uint8_t text[] = "HarmonyOS";
    size_t length = u8_strlen(text);
    size_t byte_length = strlen((const char *)text);
    if (length != byte_length) {
        return 1;
    }
    if (u8_check(text, byte_length) != NULL) {
        return 2;
    }
    printf("libunistring smoke test passed: %zu\n", length);
    return 0;
}
