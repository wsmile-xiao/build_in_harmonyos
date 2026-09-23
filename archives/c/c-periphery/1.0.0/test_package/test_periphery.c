/*
 * c-periphery consumer test (hardware-less OHOS CI environment).
 *
 * Links periphery.a and exercises the core API + error-handling paths of all
 * five subsystems. Two classes of assertions:
 *  (a) deterministic argument-validation errors (no hardware involved);
 *  (b) open() failure error semantics for non-existent device nodes
 *      (rc = *_ERROR_OPEN, errno = ENOENT, descriptive errmsg) - the real,
 *      verifiable surface on a hardware-less build machine.
 * The binary FAILS (non-zero exit) if any assertion is violated; it prints
 * every check for log evidence.
 *
 * NOTE on mmio: after mmio_open() fails (no /dev/mem), the handle keeps a
 * valid aligned_size but ptr == NULL, and the upstream read/write accessors
 * then dereference the NULL mapped pointer (the bounds check passes) -> segfault.
 * Therefore only the open/close error path is exercised for mmio; the
 * read/write accessors are intentionally NOT called on a failed-open handle.
 */
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <stdint.h>

#include "gpio.h"
#include "i2c.h"
#include "mmio.h"
#include "serial.h"
#include "spi.h"

static int g_checks = 0;
static int g_failures = 0;

#define CHECK(cond, name) do {     g_checks++;     if (cond) {         printf("PASS: %s\n", name);     } else {         g_failures++;         printf("FAIL: %s (line %d)\n", name, __LINE__);     } } while (0)

static void test_gpio(void) {
    gpio_t gpio;
    int r = gpio_open(&gpio, 42, (gpio_direction_t)(GPIO_DIR_OUT_HIGH + 1));
    CHECK(r == GPIO_ERROR_ARG, "gpio: invalid direction -> GPIO_ERROR_ARG");
    CHECK(gpio_errno(&gpio) == 0, "gpio: arg error has no errno");
    CHECK(gpio_errmsg(&gpio) != NULL && gpio_errmsg(&gpio)[0] != 0,
          "gpio: arg error has descriptive errmsg");
    /* Open on a pin whose sysfs entry does not exist: must fail, not crash. */
    r = gpio_open(&gpio, 1000000, GPIO_DIR_IN);
    CHECK(r < 0, "gpio: non-existent pin open fails");
    CHECK(gpio_errmsg(&gpio) != NULL && gpio_errmsg(&gpio)[0] != 0,
          "gpio: export failure has errmsg");
    (void)gpio_close(&gpio);
}

static void test_i2c(void) {
    i2c_t i2c;
    int r = i2c_open(&i2c, "/dev/i2c-does-not-exist");
    CHECK(r == I2C_ERROR_OPEN, "i2c: missing node -> I2C_ERROR_OPEN");
    CHECK(i2c_errno(&i2c) == ENOENT, "i2c: missing node errno == ENOENT");
    CHECK(strstr(i2c_errmsg(&i2c), "/dev/i2c-does-not-exist") != NULL,
          "i2c: errmsg names the failed path");
}

static void test_serial(void) {
    serial_t serial;
    int r = serial_open(&serial, "/dev/tty-does-not-exist", 115200);
    CHECK(r == SERIAL_ERROR_OPEN, "serial: missing node -> SERIAL_ERROR_OPEN");
    CHECK(serial_errno(&serial) == ENOENT, "serial: missing node errno == ENOENT");
    /* Argument validation is deterministic on any platform. */
    r = serial_open_advanced(&serial, "/dev/tty0", 115200, 4, PARITY_NONE, 1,
                             false, false);
    CHECK(r == SERIAL_ERROR_ARG, "serial: invalid databits -> SERIAL_ERROR_ARG");
}

static void test_mmio(void) {
    mmio_t mmio;
    /* No /dev/mem on this host: open must fail cleanly (not crash). */
    int r = mmio_open(&mmio, 0x44e10000u, 4096u);
    CHECK(r != 0, "mmio: open without /dev/mem fails");
    CHECK(mmio_errno(&mmio) == ENOENT, "mmio: missing /dev/mem errno == ENOENT");
    /* Close on a failed-open handle is safe (ptr==NULL -> returns 0). */
    CHECK(mmio_close(&mmio) == 0, "mmio: close on failed-open handle returns 0");
}

static void test_spi(void) {
    spi_t spi;
    /* Mode validation (bits 2+ are invalid) is deterministic. */
    int r = spi_open(&spi, "/dev/spidev9.9", 0x7u, 1000000u);
    CHECK(r == SPI_ERROR_ARG, "spi: invalid mode -> SPI_ERROR_ARG");
    /* Missing spidev node must fail with SPI_ERROR_OPEN, not crash. */
    r = spi_open(&spi, "/dev/spidev9.9", 0u, 1000000u);
    CHECK(r == SPI_ERROR_OPEN, "spi: missing node -> SPI_ERROR_OPEN");
    CHECK(spi_errno(&spi) == ENOENT, "spi: missing node errno == ENOENT");
}

int main(void) {
    printf("c-periphery consumer test: 17 checks planned\n");
    test_gpio();
    test_i2c();
    test_serial();
    test_mmio();
    test_spi();
    printf("RESULT: %d/%d checks passed\n", g_checks - g_failures, g_checks);
    if (g_failures > 0) {
        fprintf(stderr, "c-periphery consumer test FAILED (%d)\n", g_failures);
        return 1;
    }
    printf("c-periphery consumer test PASSED\n");
    return 0;
}
