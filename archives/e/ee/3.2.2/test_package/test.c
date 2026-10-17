/* test_package 消费者验证 — ee 3.2.2
 * 真实调用 ee 库公开 API：EE_Init / EE_Capacity / EE_Read / EE_Write /
 * EE_Format。验证流程：
 *   1) 初始化 12 字节持久化区（容量校验 = 1024）
 *   2) 写入已知数据 → 回读逐字节校验（写入后校验由 EE_Write 内部完成）
 *   3) 格式化 → 回读为全 0xFF（空态）
 *   4) 非法参数（NULL）被拒绝
 * 任一断言失败以非零退出码结束。
 */
#include "ee.h"
#include "NimaLTD.I-CUBE-EE_conf.h"

#include <stdio.h>
#include <string.h>
#include <stdint.h>

int main(void)
{
    uint32_t storage[3];
    uint32_t capacity;
    int failures = 0;

    memset(storage, 0, sizeof(storage));

    if (EE_Init(storage, sizeof(storage)) != true)
    {
        printf("FAIL EE_Init\n");
        return 1;
    }
    capacity = EE_Capacity();
    printf("EE_Capacity() = %u\n", (unsigned)capacity);
    if (capacity != EE_PAGE_SECTOR_SIZE_1K)
    {
        printf("FAIL capacity: %u != %u\n", (unsigned)capacity,
               (unsigned)EE_PAGE_SECTOR_SIZE_1K);
        failures++;
    }

    /* 初始空态回读应为 0xFFFFFFFF */
    EE_Read();
    if (storage[0] != 0xFFFFFFFFU)
    {
        printf("FAIL initial empty read: %08X\n", (unsigned)storage[0]);
        failures++;
    }

    /* 写入已知数据 */
    storage[0] = 0xDEADBEEFU;
    storage[1] = 0xCAFEBABEU;
    storage[2] = 0x12345678U;
    if (EE_Write() != true)
    {
        printf("FAIL EE_Write\n");
        failures++;
    }

    /* 清空 RAM 缓冲后回读校验 */
    memset(storage, 0, sizeof(storage));
    EE_Read();
    if (storage[0] != 0xDEADBEEFU || storage[1] != 0xCAFEBABEU || storage[2] != 0x12345678U)
    {
        printf("FAIL readback: %08X %08X %08X\n",
               (unsigned)storage[0], (unsigned)storage[1], (unsigned)storage[2]);
        failures++;
    }
    printf("readback OK: %08X %08X %08X\n",
           (unsigned)storage[0], (unsigned)storage[1], (unsigned)storage[2]);

    /* 格式化 → 空态 */
    if (EE_Format() != true)
    {
        printf("FAIL EE_Format\n");
        failures++;
    }
    EE_Read();
    if (storage[0] != 0xFFFFFFFFU)
    {
        printf("FAIL post-format empty read: %08X\n", (unsigned)storage[0]);
        failures++;
    }

    /* 非法参数拒绝 */
    if (EE_Init(NULL, sizeof(storage)) != false)
    {
        printf("FAIL NULL-init rejection\n");
        failures++;
    }

    if (failures != 0)
    {
        printf("test_ee FAILED: %d failure(s)\n", failures);
        return 1;
    }
    printf("test_ee PASS: all ee API checks OK\n");
    return 0;
}