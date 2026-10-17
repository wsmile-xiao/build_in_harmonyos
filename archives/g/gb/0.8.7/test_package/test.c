// test_package 消费者测试（R34/R51）：
// 仅通过 gb 已安装/导出的公开头文件 gb.h 使用公开 API，
// 验证第三方消费者可以编译、链接、调用并正常运行。
// gb 为 stb 风格 single-file 库：消费者在单个编译单元定义
// GB_IMPLEMENTATION 以实例化实现（gb.h 声明与实现的官方用法）。
#define GB_IMPLEMENTATION
#include <stdio.h>
#include <string.h>

#include "gb.h"

int main(void) {
    // gb_strlen / gb_strlcpy 等公开 API 来自 gb.h（类型为 isize）
    const char *src = "hello gb 0.8.7";
    isize n = gb_strlen(src);
    if (n != (isize)strlen(src)) {
        fprintf(stderr, "FAIL: gb_strlen mismatch (%ld != %zu)\n",
                (long)n, strlen(src));
        return 1;
    }

    char buf[64];
    isize copied = gb_strlcpy(buf, src, sizeof(buf));
    if (copied != n || strcmp(buf, src) != 0) {
        fprintf(stderr, "FAIL: gb_strlcpy mismatch (%ld != %ld, '%s')\n",
                (long)copied, (long)n, buf);
        return 1;
    }

    // gb_abs 公开 API
    if (gb_abs(-42) != 42) {
        fprintf(stderr, "FAIL: gb_abs(-42)\n");
        return 1;
    }

    // gb_clamp 公开 API
    if (gb_clamp(100, 0, 50) != 50 || gb_clamp(-5, 0, 50) != 0) {
        fprintf(stderr, "FAIL: gb_clamp\n");
        return 1;
    }

    printf("consumer test gb 0.8.7: OK (strlen=%lld copy='%s' abs=42 clamp=50)\n",
           (long long)n, buf);
    return 0;
}