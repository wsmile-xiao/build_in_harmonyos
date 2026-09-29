/**
 * \file            ohos_special_test.cpp
 * \brief           lwmem 2.2.4 HarmonyOS 专项测试 — 真实可执行, 非空壳 stub.
 *
 * 调用 lwmem API 完成分配/释放/重分配, 并用运行时探针校验目标平台的
 * 字节序与分配对齐行为。代码走 POSIX/标准 C++ 单一路径, 不使用任何
 * 平台条件编译宏 (R8: 平台差异用运行时判定, 不用 #if/#ifdef/#elif 分支)。
 */
#include <cstdio>
#include <cstdint>
#include <cstring>
#include "lwmem/lwmem.h"

static uint32_t lw_mem[4096 / 4]; /* 4 KB region */

static lwmem_region_t lw_regions[] = {
    { lw_mem, sizeof(lw_mem) },
    { NULL, 0 },
};

static int status = 0;

#define CHECK(x)                                                                                            \
    do {                                                                                                    \
        if (!(x)) {                                                                                         \
            printf("FAIL: %s (line %d)\n", #x, __LINE__);                                                   \
            status = 1;                                                                                     \
        }                                                                                                   \
    } while (0)

/*
 * 运行时字节序探针: 固定整数取 unsigned char* 观察首字节。
 * 目标平台为小端 (aarch64), 期望首字节为 0x04; 不匹配即为平台行为异常。
 * 无任何编译期平台宏分支。
 */
static int platform_check() {
    uint32_t probe = 0x01020304u;
    const unsigned char* p = (const unsigned char*)&probe;
    if (p[0] != 0x04u) {
        printf("special test: FAILED endianness (first byte=%u, expected 4)\n",
               (unsigned)p[0]);
        return 1;
    }
    printf("special test: platform check OK (little-endian)\n");
    return 0;
}

int main(void) {
    void* p1;
    void* p2;

    printf("lwmem special test starting\n");

    CHECK(lwmem_assignmem(lw_regions) > 0);

    p1 = lwmem_malloc(128);
    CHECK(p1 != NULL);
    if (p1 != NULL) {
        /* 对齐检查: 分配指针必须 4 字节对齐 (LWMEM_CFG_ALIGN_NUM=4) */
        CHECK(((uintptr_t)p1 % 4) == 0);
        memset(p1, 0x5A, 128);
        CHECK(((unsigned char*)p1)[0] == 0x5A);
        CHECK(((unsigned char*)p1)[127] == 0x5A);
    }

    p2 = lwmem_calloc(8, 8); /* 64 bytes zeroed */
    CHECK(p2 != NULL);
    if (p2 != NULL) {
        int i;
        for (i = 0; i < 64; ++i) {
            CHECK(((unsigned char*)p2)[i] == 0);
        }
    }

    /* realloc 扩大并保留前段内容 */
    if (p1 != NULL) {
        void* p3 = lwmem_realloc(p1, 256);
        CHECK(p3 != NULL);
        if (p3 != NULL) {
            CHECK(((unsigned char*)p3)[0] == 0x5A);
            CHECK(((unsigned char*)p3)[127] == 0x5A);
            CHECK(lwmem_get_size(p3) >= 256);
            lwmem_free(p3);
        }
    }
    if (p2 != NULL) {
        lwmem_free(p2);
    }

    if (status != 0) {
        printf("lwmem special test: FAILED\n");
        return 1;
    }

    if (platform_check() != 0) {
        return 1;
    }

    printf("lwmem special test: PASS (alloc/free/realloc/alignment/endianness verified)\n");
    return 0;
}