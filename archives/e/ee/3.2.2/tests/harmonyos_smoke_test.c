/* smoke_test.c — ee 3.2.2 模拟 Flash 功能自测 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "ee.h"
#include "main.h"
#include "NimaLTD.I-CUBE-EE_conf.h"

typedef struct
{
    uint32_t val1;
    uint32_t val2;
    uint32_t val3;
} Storage_t;

int main(void)
{
    Storage_t data;
    int rc = 0;
    uint32_t capacity;

    memset(&data, 0, sizeof(data));

    /* flash init handled by constructor */

    if (EE_Init(&data, sizeof(Storage_t)) != true)
    {
        printf("FAIL EE_Init\n");
        return 1;
    }
    capacity = EE_Capacity();
    printf("capacity=%u (expect %u)\n", (unsigned)capacity, (unsigned)EE_PAGE_SECTOR_SIZE_1K);
    if (capacity != EE_PAGE_SECTOR_SIZE_1K)
    {
        printf("FAIL capacity\n");
        return 1;
    }

    /* 初始读应为全 0xFF */
    EE_Read();
    if (data.val1 != 0xFFFFFFFFU)
    {
        printf("FAIL initial read\n");
        return 1;
    }

    /* 写入数据并回读校验 */
    data.val1 = 0xDEADBEEFU;
    data.val2 = 0xCAFEBABEU;
    data.val3 = 0x12345678U;
    if (EE_Write() != true)
    {
        printf("FAIL EE_Write\n");
        return 1;
    }

    memset(&data, 0, sizeof(data));
    EE_Read();
    if (data.val1 != 0xDEADBEEFU || data.val2 != 0xCAFEBABEU || data.val3 != 0x12345678U)
    {
        printf("FAIL readback: %08X %08X %08X\n", (unsigned)data.val1, (unsigned)data.val2, (unsigned)data.val3);
        return 1;
    }
    printf("readback OK val1=%08X val2=%08X val3=%08X\n",
           (unsigned)data.val1, (unsigned)data.val2, (unsigned)data.val3);

    /* 格式化后再读应为全 0xFF */
    if (EE_Format() != true)
    {
        printf("FAIL EE_Format\n");
        return 1;
    }
    EE_Read();
    if (data.val1 != 0xFFFFFFFFU)
    {
        printf("FAIL post-format read\n");
        return 1;
    }
    printf("post-format read OK (all 0xFF)\n");

    /* 非法参数：NULL 指针 */
    if (EE_Init(NULL, sizeof(Storage_t)) != false)
    {
        printf("FAIL NULL init\n");
        return 1;
    }
    printf("NULL init rejected OK\n");

    printf("SMOKE_TEST_PASS rc=%d\n", rc);
    return 0;
}