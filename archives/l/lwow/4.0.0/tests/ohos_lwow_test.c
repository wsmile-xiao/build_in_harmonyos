/*
 * ohos_lwow_test.c — HarmonyOS 专项测试（鸿蒙 PC aarch64 平台）
 *
 * 真实调用 lwow 公开 API 完成 1-Wire 设备枚举与 DS18B20 温度读取路径验证：
 *   - 确定性总线模拟驱动：按 1-Wire 搜索协议逐位响应单台 DS18B20（ROM 0x28…）
 *   - lwow_init / lwow_search_devices 枚举 ROM
 *   - lwow_ds18x20_start + lwow_ds18x20_read 温度读取（scratchpad + CRC 校验）
 *   - lwow_crc 纯函数校验
 * 运行于 OHOS 设备（aarch64-linux-ohos clang），退出码 0 = 全部断言通过。
 */
#include <stdio.h>
#include <string.h>
#include "lwow/lwow.h"
#include "lwow/devices/lwow_device_ds18x20.h"

/* 模拟单台 DS18B20（family 0x28，最后 1 字节 CRC 由 lwow_crc 补齐） */
static uint8_t sim_rom[8] = {0x28, 0xAA, 0x11, 0x22, 0x33, 0x44, 0x55, 0x00};

/* 模拟 scratchpad：25.0625°C（temp raw = 0x0191 = 401，12-bit 分辨率） */
static uint8_t sim_scratch[9] = {0x91, 0x01, 0x4B, 0x46, 0x7F, 0xFF, 0x0C, 0x10, 0x00};

typedef enum {
    PHASE_IDLE = 0, /* 等待命令（或转换完成检查位） */
    PHASE_SEARCH,   /* 正在执行 ROM 搜索位级交换 */
    PHASE_SCRATCH,  /* 正在读取 scratchpad 字节 */
} sim_phase_t;

typedef struct {
    sim_phase_t phase;
    int bit_pos;  /* 搜索位位置 0..63 */
    int slot;     /* 每位 3 槽：0=读1, 1=读2, 2=写回 */
    int scratch_idx;
} sim_bus_t;

static uint8_t test_init(void *arg) {
    (void)arg;
    return 1;
}

static uint8_t test_deinit(void *arg) {
    (void)arg;
    return 1;
}

static uint8_t test_set_baudrate(uint32_t baud, void *arg) {
    (void)baud;
    (void)arg;
    return 1;
}

static uint8_t test_tx_rx(const uint8_t *tx, uint8_t *rx, size_t len, void *arg) {
    sim_bus_t *bus = (sim_bus_t *)arg;
    if (tx == NULL || rx == NULL) {
        return 0;
    }

    if (len == 1U) {
        /* 复位脉冲 0xF0：设备拉低应答 presence（非 0、非 0xF0） */
        if (tx[0] == 0xF0U) {
            bus->phase = PHASE_IDLE;
            rx[0] = 0x55U;
            return 1;
        }
        if (bus->phase == PHASE_SEARCH) {
            uint8_t rom_bit;
            /* 1-Wire 搜索：ROM 位从 LSB 开始，每字节 8 位 */
            rom_bit = (sim_rom[bus->bit_pos / 8] >> (bus->bit_pos % 8)) & 0x01U;
            if (bus->slot == 0) {
                rx[0] = rom_bit ? 0xFFU : 0x00U; /* 第一读槽：ROM 位本身 */
                bus->slot = 1;
            } else if (bus->slot == 1) {
                rx[0] = rom_bit ? 0x00U : 0xFFU; /* 第二读槽：补位 */
                bus->slot = 2;
            } else {
                rx[0] = 0xFFU; /* 写回槽：设备静默 */
                bus->slot = 0;
                ++bus->bit_pos;
                if (bus->bit_pos >= 64) {
                    bus->phase = PHASE_IDLE; /* 搜索完成 */
                }
            }
            return 1;
        }
        /* 转换完成检查位：读槽全 1 = 完成 */
        rx[0] = 0xFFU;
        return 1;
    }

    if (len == 8U) {
        if (bus->phase == PHASE_SCRATCH) {
            /* 读 scratchpad：按位输出（1 → 0xFF，0 → 0x00） */
            uint8_t b = sim_scratch[bus->scratch_idx];
            for (size_t i = 0; i < 8U; ++i) {
                rx[i] = (b & (1U << i)) ? 0xFFU : 0x00U;
            }
            ++bus->scratch_idx;
            if (bus->scratch_idx >= 9) {
                bus->phase = PHASE_IDLE;
            }
            return 1;
        }
        /* 命令字节：解码（bit7..bit0 → 字节值） */
        {
            uint8_t cmd = 0;
            for (size_t i = 0; i < 8U; ++i) {
                if (tx[i] == 0xFFU) {
                    cmd |= (uint8_t)(1U << i);
                }
            }
            if (cmd == LWOW_CMD_SEARCHROM) {
                bus->phase = PHASE_SEARCH;
                bus->bit_pos = 0;
                bus->slot = 0;
            } else if (cmd == LWOW_CMD_RSCRATCHPAD) {
                bus->phase = PHASE_SCRATCH;
                bus->scratch_idx = 0;
            }
            memcpy(rx, tx, 8U);
            return 1;
        }
    }
    return 0;
}

int main(void) {
    lwow_ll_drv_t drv;
    lwow_t ow;
    sim_bus_t bus;
    lwow_rom_t roms[8];
    size_t found = 0;
    float temp = 0.0f;
    lwowr_t res;

    memset(&drv, 0, sizeof(drv));
    memset(&bus, 0, sizeof(bus));
    bus.phase = PHASE_IDLE;
    sim_rom[7] = lwow_crc(sim_rom, 7U);        /* ROM CRC 字节 */
    sim_scratch[8] = lwow_crc(sim_scratch, 8U); /* scratchpad CRC 字节 */
    drv.init = test_init;
    drv.deinit = test_deinit;
    drv.set_baudrate = test_set_baudrate;
    drv.tx_rx = test_tx_rx;

    res = lwow_init(&ow, &drv, &bus);
    if (res != lwowOK) {
        printf("FAIL: lwow_init (%d)\n", res);
        return 1;
    }
    printf("OK: lwow_init\n");

    /* 设备搜索：单台 DS18B20 */
    res = lwow_search_devices(&ow, roms, 8U, &found);
    if (res != lwowOK) {
        printf("FAIL: lwow_search_devices (%d)\n", res);
        lwow_deinit(&ow);
        return 2;
    }
    if (found != 1U) {
        printf("FAIL: 期望 1 台设备，实际 %zu\n", found);
        lwow_deinit(&ow);
        return 3;
    }
    if (memcmp(roms[0].rom, sim_rom, 8U) != 0) {
        printf("FAIL: 搜索 ROM 与模拟设备不一致\n");
        lwow_deinit(&ow);
        return 4;
    }
    printf("OK: lwow_search_devices found=%zu, ROM 一致\n", found);

    /* 温度转换 + 读取：期望 25.0625°C */
    res = lwow_ds18x20_start(&ow, NULL);
    if (res != 1U) {
        printf("FAIL: lwow_ds18x20_start (%u)\n", res);
        lwow_deinit(&ow);
        return 5;
    }
    res = lwow_ds18x20_read(&ow, NULL, &temp);
    if (res != 1U) {
        printf("FAIL: lwow_ds18x20_read (%u)\n", res);
        lwow_deinit(&ow);
        return 6;
    }
    if (temp < 25.05f || temp > 25.08f) {
        printf("FAIL: temp 期望 25.0625，实际 %.4f\n", temp);
        lwow_deinit(&ow);
        return 7;
    }
    printf("OK: lwow_ds18x20 read temp=%.4f C\n", temp);

    lwow_deinit(&ow);
    printf("ohos_lwow_test PASSED\n");
    return 0;
}