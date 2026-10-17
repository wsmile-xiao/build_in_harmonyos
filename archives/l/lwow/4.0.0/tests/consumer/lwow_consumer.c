/*
 * lwow_consumer.c — 消费者用例（模拟业务上层温度监测组件）
 *
 * 仅通过 lwow 已安装/导出的公开头文件与公开 API 使用库：
 *   - <lwow/lwow.h> 公开 API：lwow_init / lwow_search_devices / lwow_ds18x20_start / lwow_ds18x20_read
 *   - <lwow/devices/lwow_device_ds18x20.h> 公开设备 API
 * 模拟一次温度巡检业务：初始化总线 -> 枚举设备 -> 逐台读取温度 -> 汇总输出。
 * 总线驱动为确定性模拟（单台 DS18B20），遵循 1-Wire 搜索/读 scratchpad 位级协议。
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
    PHASE_IDLE = 0,
    PHASE_SEARCH,
    PHASE_SCRATCH,
} sim_phase_t;

typedef struct {
    sim_phase_t phase;
    int bit_pos;
    int slot;
    int scratch_idx;
} sim_bus_t;

static uint8_t bus_init(void *arg) {
    (void)arg;
    return 1;
}

static uint8_t bus_deinit(void *arg) {
    (void)arg;
    return 1;
}

static uint8_t bus_set_baud(uint32_t baud, void *arg) {
    (void)baud;
    (void)arg;
    return 1;
}

static uint8_t bus_txrx(const uint8_t *tx, uint8_t *rx, size_t len, void *arg) {
    sim_bus_t *bus = (sim_bus_t *)arg;
    if (tx == NULL || rx == NULL) {
        return 0;
    }
    if (len == 1U) {
        if (tx[0] == 0xF0U) {
            bus->phase = PHASE_IDLE;
            rx[0] = 0x55U;
            return 1;
        }
        if (bus->phase == PHASE_SEARCH) {
            uint8_t rom_bit = (sim_rom[bus->bit_pos / 8] >> (bus->bit_pos % 8)) & 0x01U;
            if (bus->slot == 0) {
                rx[0] = rom_bit ? 0xFFU : 0x00U;
                bus->slot = 1;
            } else if (bus->slot == 1) {
                rx[0] = rom_bit ? 0x00U : 0xFFU;
                bus->slot = 2;
            } else {
                rx[0] = 0xFFU;
                bus->slot = 0;
                ++bus->bit_pos;
                if (bus->bit_pos >= 64) {
                    bus->phase = PHASE_IDLE;
                }
            }
            return 1;
        }
        rx[0] = 0xFFU;
        return 1;
    }
    if (len == 8U) {
        if (bus->phase == PHASE_SCRATCH) {
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
    lwow_rom_t roms[4];
    size_t found = 0;
    size_t i;
    float total = 0.0f;
    lwowr_t res;

    memset(&drv, 0, sizeof(drv));
    memset(&bus, 0, sizeof(bus));
    bus.phase = PHASE_IDLE;
    sim_rom[7] = lwow_crc(sim_rom, 7U);
    sim_scratch[8] = lwow_crc(sim_scratch, 8U);
    drv.init = bus_init;
    drv.deinit = bus_deinit;
    drv.set_baudrate = bus_set_baud;
    drv.tx_rx = bus_txrx;

    res = lwow_init(&ow, &drv, &bus);
    if (res != lwowOK) {
        fprintf(stderr, "consumer: lwow_init failed (%d)\n", res);
        return 1;
    }

    res = lwow_search_devices(&ow, roms, 4U, &found);
    if (res != lwowOK) {
        fprintf(stderr, "consumer: search failed (%d)\n", res);
        lwow_deinit(&ow);
        return 2;
    }

    for (i = 0; i < found; ++i) {
        float t = 0.0f;
        if (lwow_ds18x20_start(&ow, &roms[i]) == 1U &&
            lwow_ds18x20_read(&ow, &roms[i], &t) == 1U) {
            total += t;
            printf("consumer: device[%zu] temp=%.2f C\n", i, t);
        }
    }
    printf("consumer: 巡检完成，%zu 台设备，平均温度 %.2f C\n", found, found ? total / found : 0.0f);

    lwow_deinit(&ow);
    if (found == 0U) {
        fprintf(stderr, "consumer: 未枚举到设备\n");
        return 3;
    }
    printf("consumer PASSED\n");
    return 0;
}