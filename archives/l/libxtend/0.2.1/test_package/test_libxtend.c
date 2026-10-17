#include <string.h>

#include <xtend/string.h>

int main(void) {
    char buffer[8];
    size_t copied = xt_strlcpy(buffer, "abc", sizeof(buffer));
    if (copied != 3) {
        return 1;
    }
    return strcmp(buffer, "abc") == 0 ? 0 : 2;
}

