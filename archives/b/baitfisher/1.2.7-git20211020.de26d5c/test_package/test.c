/* test_package/test.c — baitfisher 1.2.7 consumer test
 *
 * BaitFisher 是 CLI 程序（无链接库 API），消费者验证聚焦可执行：
 * 执行 BaitFisher 无参数运行，断言输出包含 "Usage"（BaitFisher 需输入
 * 文件，无参数时打印用法——验证可执行真实可用，非空壳）。
 * argv[1] 为 BaitFisher 可执行路径（由 conanfile.py test() 传入）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char** argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: test_baitfisher <BaitFisher-path>\n");
        return 2;
    }
    char cmd[4096];
    snprintf(cmd, sizeof(cmd), "%s 2>&1", argv[1]);
    FILE* fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "failed to run %s\n", argv[1]);
        return 1;
    }
    char buf[512];
    int found = 0;
    while (fgets(buf, sizeof(buf), fp)) {
        if (strstr(buf, "Usage")) {
            found = 1;
            break;
        }
    }
    pclose(fp);
    if (!found) {
        fprintf(stderr, "output of %s missing 'Usage'\n", argv[1]);
        return 1;
    }
    printf("baitfisher 1.2.7 consumer test OK (BaitFisher ran)\n");
    return 0;
}
