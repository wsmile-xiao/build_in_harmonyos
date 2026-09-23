/**
 * consumer_app_test.c — ee 库消费者验证用例
 *
 * 模拟鸿蒙 PC 上层业务组件（设备参数持久化服务）：仅通过 ee 库安装后
 * 导出的公开头文件 ee.h 与公开 API（EE_Init/EE_Capacity/EE_Read/
 * EE_Write/EE_Format）使用该库，验证第三方使用者能否编译、链接、调用
 * 并正常运行。
 *
 * 业务场景：把一组设备参数（灯光亮度、传感器阈值、工作模式）持久化到
 * EEPROM 模拟区，重启（模拟）后回读校验一致；再验证格式化清空语义。
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "ee.h"

typedef struct
{
    uint8_t  light_level;     /* 灯光亮度 0-255 */
    uint16_t sensor_threshold; /* 传感器阈值 */
    uint8_t  work_mode;       /* 工作模式 */
    uint16_t crc16;           /* 参数校验和 */
} DeviceParams_t;

int main(void)
{
    DeviceParams_t params;
    uint32_t capacity;
    int pass = 0;

    memset(&params, 0, sizeof(params));
    capacity = 0;

    /* 业务初始化：绑定持久化缓冲区并读取上次保存的参数 */
    if (EE_Init(&params, sizeof(DeviceParams_t)) != true)
    {
        printf("CONSUMER_FAIL EE_Init\n");
        return 1;
    }
    capacity = EE_Capacity();
    printf("ee capacity: %u bytes\n", (unsigned)capacity);
    if (capacity < sizeof(DeviceParams_t))
    {
        printf("CONSUMER_FAIL capacity too small\n");
        return 1;
    }

    EE_Read();

    /* 首次运行场景：模拟区为空（0xFF），写入默认参数并持久化 */
    if (params.crc16 == 0xFFFFU)
    {
        printf("first-run: initializing defaults\n");
        params.light_level = 128;
        params.sensor_threshold = 1024;
        params.work_mode = 3;
        params.crc16 = 0x5A5A;
        if (EE_Write() != true)
        {
            printf("CONSUMER_FAIL EE_Write defaults\n");
            return 1;
        }
        printf("defaults persisted: light=%u threshold=%u mode=%u\n",
               params.light_level, params.sensor_threshold, params.work_mode);
    }

    /* 业务运行中修改参数并持久化 */
    params.light_level = 200;
    params.sensor_threshold = 2048;
    params.work_mode = 7;
    params.crc16 = 0xA55A;
    if (EE_Write() != true)
    {
        printf("CONSUMER_FAIL EE_Write updated\n");
        return 1;
    }
    printf("updated params persisted\n");

    /* 模拟设备重启：清零 RAM 缓冲后从持久化区回读 */
    memset(&params, 0, sizeof(params));
    EE_Read();
    if (params.light_level == 200 && params.sensor_threshold == 2048 &&
        params.work_mode == 7 && params.crc16 == 0xA55A)
    {
        printf("restart-restore OK: light=%u threshold=%u mode=%u crc=%04X\n",
               params.light_level, params.sensor_threshold, params.work_mode, params.crc16);
        pass++;
    }
    else
    {
        printf("CONSUMER_FAIL restart-restore: %u/%u/%u/%04X\n",
               params.light_level, params.sensor_threshold, params.work_mode, params.crc16);
        return 1;
    }

    /* 格式化后回读应回到空态（全 0xFF） */
    if (EE_Format() != true)
    {
        printf("CONSUMER_FAIL EE_Format\n");
        return 1;
    }
    EE_Read();
    if (params.crc16 == 0xFFFFU)
    {
        printf("format-wipe OK: device reset to empty\n");
        pass++;
    }
    else
    {
        printf("CONSUMER_FAIL format-wipe\n");
        return 1;
    }

    printf("CONSUMER_TEST_PASS checks=%d\n", pass);
    return 0;
}