#include <stdio.h>
#include <string.h>

int main(void) {
    const char *expected = "unfoo archive -> OHOS aarch64 consumer";
    char output[80];
    int written = snprintf(output, sizeof(output), "%s", expected);
    if (written != (int)strlen(expected) || strcmp(output, expected) != 0) {
        return 1;
    }
    puts(output);
    return 0;
}
