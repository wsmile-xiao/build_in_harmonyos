/*
 * pump.c — pipemeter 1.1.5 test_package 测试源码
 *
 * 向 stdout 输出精确 N 字节的可校验数据流，充当 pipemeter 的上游生产者。
 * 它存在的意义是让 L1 测试真正经过“编译 → 执行 → 管道 → 被测二进制”的完整
 * 链路（R34：测试必须实质依赖被测包），而不是只在 shell 里 echo 字符串。
 *
 * 用法: pump [字节数]     默认 524288 (= 512 KiB)
 * 退出码: 0 成功；2 参数非法；3 短写；4 flush 失败
 */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define PUMP_BLOCK 8192
#define PUMP_DEFAULT_BYTES "524288"

int main(int argc, char **argv)
{
    unsigned long long total;
    unsigned long long written = 0;
    char block[PUMP_BLOCK];
    char *endp = NULL;
    size_t i;

    if (argc > 2) {
        fprintf(stderr, "usage: pump [bytes]\n");
        return 2;
    }

    errno = 0;
    endp = NULL;
    total = strtoull(argc > 1 ? argv[1] : PUMP_DEFAULT_BYTES, &endp, 10);
    if (errno != 0 || endp == NULL || *endp != '\0' || total == 0) {
        fprintf(stderr, "pump: invalid byte count\n");
        return 2;
    }

    /* 已知模式，便于消费端校验数据面未被篡改 */
    for (i = 0; i < sizeof(block); i++) {
        block[i] = (char)('A' + (int)(i % 26));
    }

    while (written < total) {
        size_t chunk = (size_t)((total - written) > (unsigned long long)sizeof(block)
                                    ? sizeof(block)
                                    : (size_t)(total - written));
        if (fwrite(block, 1, chunk, stdout) != chunk) {
            fprintf(stderr, "pump: short write after %llu bytes\n", written);
            return 3;
        }
        written += (unsigned long long)chunk;
    }

    if (fflush(stdout) != 0) {
        fprintf(stderr, "pump: fflush failed\n");
        return 4;
    }
    fprintf(stderr, "pump: wrote %llu bytes\n", written);
    return 0;
}
