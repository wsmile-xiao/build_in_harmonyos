#include <stdio.h>
#include <stdlib.h>
#include <ffcall-version.h>

int main(void) {
    /* 实质调用被测库 API：ffcall_get_version() 返回 libffcall 版本号 */
    int version = ffcall_get_version();
    printf("libffcall version: %d\n", version);
    if (version <= 0) {
        fprintf(stderr, "FAIL: ffcall_get_version() returned %d\n", version);
        return 1;
    }
    return 0;
}
