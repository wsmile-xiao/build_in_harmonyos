/*
 * Consumer test — periphery 2.5.0
 *
 * Simulates a downstream application: uses only the packaged public headers
 * (include/periphery per-module headers) and the packaged libperiphery. Verifies that the
 * library compiles, links, and its public API is callable on HarmonyOS PC.
 *
 * The probe covers all 7 modules (gpio/i2c/led/mmio/pwm/serial/spi) plus
 * version: new/close/free round-trips and error-code behavior for absent
 * devices. No real peripheral hardware is required — on a PC, open() on a
 * non-existent device must return the documented error code, which is
 * exactly the contract a library user relies on.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#include "periphery/gpio.h"
#include "periphery/i2c.h"
#include "periphery/led.h"
#include "periphery/mmio.h"
#include "periphery/pwm.h"
#include "periphery/serial.h"
#include "periphery/spi.h"
#include "periphery/version.h"

static int checks = 0;
static int failures = 0;

#define CHECK(cond)                                                  \
    do {                                                             \
        checks++;                                                    \
        if (cond) {                                                  \
            printf(" [ OK ] %s\n", #cond);                           \
        } else {                                                     \
            failures++;                                              \
            printf(" [FAIL] %s (%s:%d)\n", #cond, __FILE__, __LINE__); \
        }                                                            \
    } while (0)

int main(void) {
    /* Version API */
    const periphery_version_t *ver = periphery_version_info();
    printf("periphery version: %s (major=%u minor=%u patch=%u commit=%s)\n",
           periphery_version(), ver->major, ver->minor, ver->patch, ver->commit_id);
    CHECK(ver != NULL);
    CHECK(ver->major == 2);
    CHECK(ver->minor == 5);
    CHECK(ver->patch == 0);
    CHECK(periphery_version()[0] != '\0');

    /* GPIO */
    {
        gpio_t *gpio = gpio_new();
        CHECK(gpio != NULL);
        if (gpio) {
            /* Invalid direction argument */
            CHECK(gpio_open(gpio, "/dev/gpiochip0", 55, 5) == GPIO_ERROR_ARG);
            /* Absent/forbidden device -> documented open error (errno set) */
            int rc = gpio_open(gpio, "/dev/gpiochip-nonexistent", 55, GPIO_DIR_IN);
            CHECK(rc == GPIO_ERROR_OPEN);
            CHECK(gpio_errno(gpio) > 0);
            gpio_free(gpio);
        }
    }

    /* I2C */
    {
        i2c_t *i2c = i2c_new();
        CHECK(i2c != NULL);
        if (i2c) {
            CHECK(i2c_open(i2c, "/dev/i2c-nonexistent") == I2C_ERROR_OPEN);
            CHECK(i2c_errno(i2c) > 0);
            CHECK(i2c_close(i2c) == 0);
            i2c_free(i2c);
        }
    }

    /* LED */
    {
        led_t *led = led_new();
        CHECK(led != NULL);
        if (led) {
            CHECK(led_open(led, "no-such-led") == LED_ERROR_OPEN);
            CHECK(led_errno(led) > 0);
            led_free(led);
        }
    }

    /* MMIO */
    {
        mmio_t *mmio = mmio_new();
        CHECK(mmio != NULL);
        if (mmio) {
            /* /dev/mem absent on PC -> documented open error */
            int rc = mmio_open(mmio, 0x10000000, 4096);
            CHECK(rc == MMIO_ERROR_OPEN);
            CHECK(mmio_errno(mmio) > 0);
            mmio_free(mmio);
        }
    }

    /* PWM */
    {
        pwm_t *pwm = pwm_new();
        CHECK(pwm != NULL);
        if (pwm) {
            int rc = pwm_open(pwm, 9999, 0);
            CHECK(rc == PWM_ERROR_OPEN);
            CHECK(pwm_errno(pwm) > 0);
            pwm_free(pwm);
        }
    }

    /* Serial */
    {
        serial_t *serial = serial_new();
        CHECK(serial != NULL);
        if (serial) {
            /* Invalid stopbits (same invalid-argument check as upstream
             * tests/test_serial.c test_arguments) */
            CHECK(serial_open_advanced(serial, "/dev/ttyS-nonexistent", 115200, 8,
                                       PARITY_NONE, 3, false, false) == SERIAL_ERROR_ARG);
            /* Absent device */
            int rc = serial_open(serial, "/dev/ttyS-nonexistent", 115200);
            CHECK(rc == SERIAL_ERROR_OPEN);
            CHECK(serial_errno(serial) > 0);
            serial_free(serial);
        }
    }

    /* SPI */
    {
        spi_t *spi = spi_new();
        CHECK(spi != NULL);
        if (spi) {
            int rc = spi_open(spi, "/dev/spidev-nonexistent", 0, 1000000);
            CHECK(rc == SPI_ERROR_OPEN);
            CHECK(spi_errno(spi) > 0);
            spi_free(spi);
        }
    }

    printf("\n=== periphery consumer test: %d checks, %d failures ===\n", checks, failures);
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
