/* test_package/test.c — libntfs-3g 2026.7.7 consumer test
 *
 * L1 test:
 * 1. 编译并链接 libntfs-3g（含头文件与库）；
 * 2. 调用 ntfs_malloc/ntfs_free/ntfs_calloc 分配/清零/释放验证库
 *    核心内存管理路径可用（misc.h 公开 API）。
 *
 * 注：上游 ntfs-3g 头文件依赖标准 C 类型（size_t/va_list/off_t/
 *     NULL 分别来自 stddef/stdarg/sys/types），types.h 仅在
 *     HAVE_SYS_TYPES_H 时包含 <sys/types.h>，消费者必须先行包含
 *     标准头（上游自身源文件同样如此）。
 */
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/types.h>
#include <time.h>
#include <ntfs-3g/misc.h>
#include <ntfs-3g/volume.h>

int main(void) {
    /* 断言 1: ntfs_malloc 分配成功（1024 字节） */
    void *p = ntfs_malloc(1024);
    if (!p) {
        fprintf(stderr, "ntfs_malloc(1024) failed\n");
        return 1;
    }
    /* 断言 2: 写入并读回内容一致（库内存可正常访问） */
    memset(p, 0x5a, 1024);
    if (((unsigned char *)p)[0] != 0x5a || ((unsigned char *)p)[1023] != 0x5a) {
        fprintf(stderr, "memset/memcmp over ntfs_malloc buffer failed\n");
        return 1;
    }
    /* 断言 3: ntfs_free 正常释放（不崩溃） */
    ntfs_free(p);
    /* 断言 4: ntfs_calloc 分配成功且清零（库 calloc 路径可用） */
    void *z = ntfs_calloc(64);
    if (!z) {
        fprintf(stderr, "ntfs_calloc(64) failed\n");
        return 1;
    }
    {
        unsigned int i;
        for (i = 0; i < 64; i++) {
            if (((unsigned char *)z)[i] != 0) {
                fprintf(stderr, "ntfs_calloc buffer not zeroed at %u\n", i);
                ntfs_free(z);
                return 1;
            }
        }
    }
    ntfs_free(z);
    printf("libntfs-3g 2026.7.7 consumer test OK (4 assertions passed)\n");
    return 0;
}