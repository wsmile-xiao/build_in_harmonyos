/*
 * test_package.c — validates the packaged lwow library public API.
 *
 * Uses only the public header <lwow/lwow.h> from the installed package:
 *  - lwow_init / lwow_reset / lwow_write_byte_ex / lwow_read_byte_ex lifecycle
 *  - lwow_crc for a pure, observable CRC computation result
 */
#include <stdio.h>
#include <string.h>
#include "lwow/lwow.h"

/* Simulated 1-Wire bus: single device present, echoes back written bytes */
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
    (void)arg;
    if (tx != NULL && rx != NULL && len == 1U) {
        /* Reset pulse 0xF0: a connected device pulls the line for presence,
         * so the sampled byte differs from both 0x00 and 0xF0. */
        rx[0] = (tx[0] == 0xF0U) ? 0x55U : tx[0];
    }
    return 1;
}

int main(void) {
    lwow_ll_drv_t drv;
    lwow_t ow;
    uint8_t byt = 0;
    lwowr_t res;

    memset(&drv, 0, sizeof(drv));
    drv.init = test_init;
    drv.deinit = test_deinit;
    drv.set_baudrate = test_set_baudrate;
    drv.tx_rx = test_tx_rx;

    res = lwow_init(&ow, &drv, NULL);
    if (res != lwowOK) {
        printf("FAIL: lwow_init returned %d\n", res);
        return 1;
    }
    printf("OK: lwow_init succeeded\n");

    res = lwow_reset(&ow);
    if (res != lwowOK) {
        printf("FAIL: lwow_reset returned %d\n", res);
        lwow_deinit(&ow);
        return 1;
    }
    printf("OK: lwow_reset (presence) succeeded\n");

    res = lwow_write_byte_ex(&ow, 0x33U, &byt); /* READ ROM command */
    if (res != lwowOK || byt != 0x33U) {
        printf("FAIL: lwow_write_byte_ex res=%d byt=%u\n", res, byt);
        lwow_deinit(&ow);
        return 1;
    }
    printf("OK: lwow_write_byte_ex echo succeeded\n");

    res = lwow_read_byte_ex(&ow, &byt);
    if (res != lwowOK || byt != 0xFFU) {
        printf("FAIL: lwow_read_byte_ex res=%d byt=%u\n", res, byt);
        lwow_deinit(&ow);
        return 1;
    }
    printf("OK: lwow_read_byte_ex succeeded\n");

    /* CRC over a known ROM pattern must equal 0xA3 (observable pure result) */
    {
        static const uint8_t rom[8] = {0x28, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x00};
        uint8_t crc = lwow_crc(rom, sizeof(rom));
        printf("INFO: lwow_crc(rom) = 0x%02X\n", crc);
        if (crc != 0xA3U) {
            printf("FAIL: unexpected CRC 0x%02X\n", crc);
            lwow_deinit(&ow);
            return 1;
        }
    }
    printf("OK: lwow_crc matched expected value\n");

    lwow_deinit(&ow);
    printf("test_package PASSED\n");
    return 0;
}
