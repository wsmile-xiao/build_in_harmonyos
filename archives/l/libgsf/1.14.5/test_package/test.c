/* test_package/test.c — libgsf 1.14.5 consumer test
 *
 * L1 test:
 * 1. 编译并链接 libgsf-1（含头文件与库）；
 * 2. 运行时用 gsf_input_memory_new + gsf_input_read 从内存输入读回
 *    数据，断言内容一致——直接验证库核心读取路径可用。
 * 注：不显式 g_object_unref（glib 释放路径在鸿蒙运行时受限，单次测试
 * 进程退出自动回收）。
 */
#include <gsf/gsf.h>
#include <gsf/gsf-input-memory.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    static const unsigned char payload[] = "libgsf 1.14.5 payload";
    /* needs_free=FALSE：payload 为 static const 缓冲，绝不能被 g_free
     * （TRUE 会在 g_object_unref 时对静态内存 free 导致崩溃） */
    GsfInput *in = gsf_input_memory_new(payload, sizeof(payload) - 1, FALSE);
    if (!in) {
        fprintf(stderr, "gsf_input_memory_new failed\n");
        return 1;
    }
    unsigned char buf[64] = {0};
    const guint8 *ret = gsf_input_read(in, sizeof(payload) - 1, buf);
    if (ret == NULL) {
        fprintf(stderr, "gsf_input_read failed\n");
        return 1;
    }
    if (memcmp(buf, payload, sizeof(payload) - 1) != 0) {
        fprintf(stderr, "gsf_input_read content mismatch\n");
        return 1;
    }
    printf("libgsf 1.14.5 consumer test OK\n");
    return 0;
}
