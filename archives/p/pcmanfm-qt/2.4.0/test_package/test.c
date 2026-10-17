/* pcmanfm-qt 2.4.0 consumer smoke test
 *
 * 可编译测试源文件（CI L0c no_test_sources 门禁要求 test_package 内含
 * .c/.cpp/.sh/.py 测试源）。以消费者视角验证安装制品：
 *   1) 打包的 bin/pcmanfm-qt 存在（由 conanfile.py 检查）
 *   2) pcmanfm-qt --version 可正常运行（退出码 0）
 *   3) pcmanfm-qt --help 可正常运行（退出码 0）
 *
 * GUI 程序通过 QT_QPA_PLATFORM=offscreen 运行，无需显示服务器。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int check_cmd(const char *what, const char *cmd) {
    char buf[512];
    snprintf(buf, sizeof(buf), "%s > /dev/null 2>&1", cmd);
    int ret = system(buf);
    if (ret != 0) {
        fprintf(stderr, "FAIL: %s exited with code %d\n", what, ret);
        return 1;
    }
    printf("PASS: %s\n", what);
    return 0;
}

int main(void) {
    int failures = 0;
    const char *pcman = getenv("PCMANFM_QT_BIN");
    char cmd[600];

    if (!pcman) {
        /* 默认从 PATH 查找（conanrun 环境已注入依赖 bin 目录） */
        pcman = "pcmanfm-qt";
    }

    snprintf(cmd, sizeof(cmd), "%s --version", pcman);
    failures += check_cmd("pcmanfm-qt --version", cmd);

    snprintf(cmd, sizeof(cmd), "%s --help", pcman);
    failures += check_cmd("pcmanfm-qt --help", cmd);

    if (failures != 0) {
        fprintf(stderr, "pcmanfm-qt smoke test FAILED (%d)\n", failures);
        return 1;
    }
    printf("pcmanfm-qt smoke test PASSED\n");
    return 0;
}