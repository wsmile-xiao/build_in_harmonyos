/* test.c — Smoke test for voacapl 0.7.7 (OHOS/aarch64)
 *
 * voacapl 是 CLI 工具（无库 API），R34 要求测试真实执行被测包二进制。
 * `voacapl --version` 是唯一不依赖 itshfbc 数据目录即可运行的 CLI 路径，
 * 校验版本输出 "voacapl - release 0.7.7" 即通过。
 * conanfile.py 的 test() 同时直接运行 `voacapl --version`。
 */
#include <stdio.h>
#include <string.h>

int main(void) {
    FILE *fp;
    char buf[256];
    size_t n;

    fp = popen("voacapl --version 2>/dev/null", "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run voacapl\n");
        return 1;
    }
    n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    pclose(fp);

    if (strstr(buf, "voacapl - release") == NULL) {
        fprintf(stderr, "FAIL: voacapl version output mismatch, got: %s\n", buf);
        return 1;
    }

    printf("voacapl smoke test: PASSED (%s)", buf);
    return 0;
}
