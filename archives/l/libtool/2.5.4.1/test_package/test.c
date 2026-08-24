/* libtool test_package 测试源（L0 no_test_sources + L1 真实验证要求）——
 * 真实验证 libtool 工具可执行：执行 libtool --version 并检查返回码与输出（R34——非空壳测试）。 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    /* 真实执行被测包二进制 libtool --version（R34——必须执行被测包二进制） */
    int rc = system("libtool --version >/tmp/libtool_version.txt 2>&1");
    if (rc != 0) {
        fprintf(stderr, "FAIL: libtool --version 执行失败 (rc=%d)\n", rc);
        return 1;
    }
    /* 检查输出非空（--version 必须产生版本输出——输出为空视为失败） */
    FILE *fp = fopen("/tmp/libtool_version.txt", "r");
    if (fp == NULL) {
        fprintf(stderr, "FAIL: 无法读取 libtool --version 输出\n");
        return 1;
    }
    char buf[128] = {0};
    if (fgets(buf, sizeof(buf), fp) == NULL || strlen(buf) == 0) {
        fclose(fp);
        fprintf(stderr, "FAIL: libtool --version 输出为空\n");
        return 1;
    }
    fclose(fp);
    printf("libtool test_package OK: libtool --version 输出 = %s", buf);
    return 0;
}
