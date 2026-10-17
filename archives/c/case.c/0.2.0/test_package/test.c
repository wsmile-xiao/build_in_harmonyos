#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "case.h"

/* 消费者测试：只通过 case.c 已安装/导出的公开头文件与公开 API
 * (case_lower / case_upper / case_camel) 编译、链接并运行。 */
static int failures = 0;

static void expect(const char *got, const char *want, const char *api) {
    if (0 != strcmp(got, want)) {
        fprintf(stderr, "FAIL %s: got \"%s\", want \"%s\"\n", api, got, want);
        failures++;
    } else {
        printf("OK   %s -> \"%s\"\n", api, got);
    }
}

int main(void) {
    char lower_buf[] = "HeLLo WoRLD";
    char upper_buf[] = "HeLLo WoRLD";
    char camel_buf[] = "hello world-case_example";

    expect(case_lower(lower_buf), "hello world", "case_lower");
    expect(case_upper(upper_buf), "HELLO WORLD", "case_upper");
    expect(case_camel(camel_buf), "helloWorldCaseExample", "case_camel");

    printf("consumer test: %s\n", failures ? "FAILED" : "PASSED");
    return failures ? 1 : 0;
}
