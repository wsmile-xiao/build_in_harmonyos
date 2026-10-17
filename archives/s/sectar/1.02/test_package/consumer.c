#include <stdint.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    const char *message = "sectar OHOS aarch64 consumer OK";
    if (sizeof(uint32_t) != 4 || strlen(message) != 31)
        return 1;
    puts(message);
    return 0;
}
