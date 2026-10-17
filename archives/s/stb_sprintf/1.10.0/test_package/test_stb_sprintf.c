#include <assert.h>
#include <string.h>

#define STB_SPRINTF_IMPLEMENTATION
#include <stb_sprintf.h>

int main(void) {
    char buffer[64];
    int length = stbsp_snprintf(buffer, (int)sizeof(buffer), "%s:%d:%.2f", "ohos", 42, 3.5);
    assert(length == 12);
    assert(strcmp(buffer, "ohos:42:3.50") == 0);
    return 0;
}
