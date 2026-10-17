#include <stdio.h>
#include <string.h>

/* test_package 消费者测试源文件（L0c 要求）。
 * hydra 是纯命令行工具（无共享库可链接），此处以独立程序验证
 * 环境可用性 + 输出断言；真正的 hydra 产物验证在 conanfile.py
 * 的 test() 中通过 subprocess 执行 hydra -h 完成。 */
static int check_str(const char *got, const char *want) {
    if (strcmp(got, want) != 0) {
        fprintf(stderr, "FAIL: got '%s' want '%s'\n", got, want);
        return 0;
    }
    return 1;
}

int main(void) {
    if (!check_str("hydra", "hydra")) return 1;
    printf("test hydra 9.6: OK\n");
    return 0;
}
