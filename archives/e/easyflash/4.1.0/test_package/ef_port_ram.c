/*
 * ef_port_ram.c — RAM-backing flash emulation port for easyflash tests.
 *
 * EasyFlash requires the platform port (ef_port.c) to implement
 * read/erase/write/log primitives. On OHOS PC there is no MCU flash,
 * so this port emulates flash semantics over a static RAM region:
 *   - erase sets bytes to 0xFF
 *   - write only flips 1 -> 0 (NOR flash semantics)
 *   - read returns the RAM contents
 * It is used by both test_package and the OHOS-specific test executable.
 */
#include <easyflash.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#define RAM_FLASH_SIZE (ENV_AREA_SIZE * 2 + 4096)

static unsigned char s_flash[RAM_FLASH_SIZE];
static int s_flash_inited = 0;

static const ef_env default_env_set[] = {
    {"boot_times", "0", 1},
};

EfErrCode ef_port_init(ef_env const **default_env, size_t *default_env_size) {
    /* Real flash retains content across power cycles / re-initialisation:
     * only erase the emulated region on the very first init. */
    if (!s_flash_inited) {
        memset(s_flash, 0xFF, sizeof(s_flash));
        s_flash_inited = 1;
    }
    *default_env = default_env_set;
    *default_env_size = sizeof(default_env_set) / sizeof(default_env_set[0]);
    return EF_NO_ERR;
}

/* Read data from flash. Unit of addr/size is bytes; buffer elements are 32-bit. */
EfErrCode ef_port_read(uint32_t addr, uint32_t *buf, size_t size) {
    if (addr + size > sizeof(s_flash)) {
        return EF_READ_ERR;
    }
    memcpy(buf, s_flash + addr, size);
    return EF_NO_ERR;
}

EfErrCode ef_port_erase(uint32_t addr, size_t size) {
    if (addr % EF_ERASE_MIN_SIZE != 0) {
        return EF_ERASE_ERR;
    }
    if (addr + size > sizeof(s_flash)) {
        return EF_ERASE_ERR;
    }
    memset(s_flash + addr, 0xFF, size);
    return EF_NO_ERR;
}

/* Write data to flash with NOR semantics: bits only go 1 -> 0. */
EfErrCode ef_port_write(uint32_t addr, const uint32_t *buf, size_t size) {
    size_t i;
    const unsigned char *src = (const unsigned char *)buf;
    if (addr + size > sizeof(s_flash)) {
        return EF_WRITE_ERR;
    }
    for (i = 0; i < size; i++) {
        unsigned char v = s_flash[addr + i] & src[i];
        if (v != s_flash[addr + i]) {
            s_flash[addr + i] = v;
        }
    }
    return EF_NO_ERR;
}

void ef_port_env_lock(void) {
}

void ef_port_env_unlock(void) {
}

void ef_log_debug(const char *file, const long line, const char *format, ...) {
#ifdef PRINT_DEBUG
    va_list args;
    va_start(args, format);
    vfprintf(stdout, format, args);
    va_end(args);
#endif
}

void ef_log_info(const char *format, ...) {
    va_list args;
    va_start(args, format);
    vfprintf(stdout, format, args);
    va_end(args);
}

void ef_print(const char *format, ...) {
    va_list args;
    va_start(args, format);
    vfprintf(stdout, format, args);
    va_end(args);
}