#include <stdio.h>
#include "linenoise.h"

int main(void) {
    /* 实质调用被测包 API（R34）：
     * linenoiseHistorySetMaxLen / linenoiseHistoryAdd 成功返回 1，失败返回 0 */
    if (linenoiseHistorySetMaxLen(100) != 1) {
        printf("FAIL: linenoiseHistorySetMaxLen\n");
        return 1;
    }
    if (linenoiseHistoryAdd("conan test line") != 1) {
        printf("FAIL: linenoiseHistoryAdd\n");
        return 1;
    }
    printf("linenoise 2.0 API test: OK\n");
    return 0;
}
