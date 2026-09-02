#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "linenoise.h"

/* 实质调用被测包 API（R34）：
 * 1.0 版本的 linenoise API 成功返回 1、失败返回 0（与常规约定相反）。
 * 用例：
 *   - linenoiseHistorySetMaxLen(100) 期望返回 1
 *   - linenoiseHistoryAdd("conan test line") 期望返回 1
 *   - 通过 linenoiseHistoryLoad 读回 history 文件验证持久化 API 链路 */
int main(void) {
    const char *hist_file = "linenoise_test_history.log";

    if (linenoiseHistorySetMaxLen(100) != 1) {
        printf("FAIL: linenoiseHistorySetMaxLen\n");
        return 1;
    }
    if (linenoiseHistoryAdd("conan test line") != 1) {
        printf("FAIL: linenoiseHistoryAdd\n");
        return 1;
    }
    if (linenoiseHistorySave(hist_file) != 0) {
        printf("FAIL: linenoiseHistorySave\n");
        return 1;
    }
    if (linenoiseHistoryLoad(hist_file) != 0) {
        printf("FAIL: linenoiseHistoryLoad\n");
        return 1;
    }
    printf("linenoise 1.0 API test: OK\n");
    return 0;
}