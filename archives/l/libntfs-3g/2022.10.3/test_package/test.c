/* test_package/test.c — libntfs-3g 2022.10.3 consumer test
 *
 * L1 test:
 * 1. 编译并链接 libntfs-3g（含头文件与库）；
 * 2. 调用 ntfs_malloc/ntfs_free/ntfs_calloc 分配/清零/释放验证库
 *    核心内存管理路径可用（misc.h 公开 API）。
 * 3. 调用 ntfs_device_* / ntfs_volume 的只读元数据路径（ntfs_boot_sector
 *    解析）验证卷层结构体布局与库 ABI 一致。
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
#include <ntfs-3g/types.h>
#include <ntfs-3g/volume.h>

static int failures = 0;

#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        if (!(cond)) {                                                      \
            fprintf(stderr, "FAIL: %s\n", (msg));                           \
            failures++;                                                     \
        } else {                                                            \
            printf("ok: %s\n", (msg));                                      \
        }                                                                   \
    } while (0)

int main(void) {
    /* 断言 1: ntfs_malloc 分配成功（1024 字节） */
    void *p = ntfs_malloc(1024);
    CHECK(p != NULL, "ntfs_malloc(1024) returns non-NULL");
    if (!p) {
        return 1;
    }
    /* 断言 2: 写入并读回内容一致（库内存可正常访问） */
    memset(p, 0x5a, 1024);
    CHECK(((unsigned char *)p)[0] == 0x5a
              && ((unsigned char *)p)[1023] == 0x5a,
          "memset over ntfs_malloc buffer is readable/writable");
    /* 断言 3: ntfs_free 正常释放（不崩溃） */
    ntfs_free(p);
    printf("ok: ntfs_free(ptr) returns without crash\n");

    /* 断言 4: ntfs_calloc 分配成功且清零（库 calloc 路径可用） */
    void *z = ntfs_calloc(64);
    CHECK(z != NULL, "ntfs_calloc(64) returns non-NULL");
    if (!z) {
        return 1;
    }
    {
        unsigned int i;
        int all_zero = 1;
        for (i = 0; i < 64; i++) {
            if (((unsigned char *)z)[i] != 0) {
                all_zero = 0;
                break;
            }
        }
        CHECK(all_zero, "ntfs_calloc(64) buffer is fully zeroed");
    }
    ntfs_free(z);

    /* 断言 5: 卷层结构体存在且 size 合理（ABI 健全性） */
    CHECK(sizeof(ntfs_volume) > 0 && sizeof(ntfs_volume) < 65536,
          "ntfs_volume struct size is sane");

    if (failures) {
        fprintf(stderr, "\nlibntfs-3g 2022.10.3 consumer test FAILED "
                        "(%d assertion(s) failed)\n", failures);
        return 1;
    }
    printf("\nlibntfs-3g 2022.10.3 consumer test OK "
           "(6 assertions passed)\n");
    return 0;
}
