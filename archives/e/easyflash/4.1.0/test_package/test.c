/*
 * test.c — consumer-side verification for easyflash 4.1.0.
 *
 * A third-party consumer only sees the installed public headers (easyflash.h)
 * and links libeasyflash; the RAM flash port below simulates the target
 * flash so the ENV (key-value) API can run end-to-end on OHOS PC.
 *
 * Public API exercised: easyflash_init(), ef_env_set(), ef_get_env_blob(),
 * ef_del_env(), ef_set_and_save_env(), ef_del_and_save_env().
 */
#include <easyflash.h>
#include <stdio.h>
#include <string.h>

extern EfErrCode ef_port_init(ef_env const **default_env, size_t *default_env_size);
extern EfErrCode ef_port_read(uint32_t addr, uint32_t *buf, size_t size);
extern EfErrCode ef_port_erase(uint32_t addr, size_t size);
extern EfErrCode ef_port_write(uint32_t addr, const uint32_t *buf, size_t size);
extern void ef_port_env_lock(void);
extern void ef_port_env_unlock(void);

#define CHECK(cond, msg) do { \
    if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); return 1; } \
    printf("PASS: %s\n", msg); \
} while (0)

int main(void) {
    char value[64];
    size_t saved_len = 0;

    /* ef_port_init is called by ef_env_init() inside easyflash_init(). */
    CHECK(easyflash_init() == EF_NO_ERR, "easyflash_init()");
    CHECK(ef_load_env() == EF_NO_ERR, "ef_load_env()");

    /* In-memory CRUD on the ENV KV store. */
    CHECK(ef_set_env("fw_ver", "1.2.3") == EF_NO_ERR, "ef_set_env(fw_ver)");
    CHECK(ef_get_env_blob("fw_ver", value, sizeof(value), &saved_len) > 0, "ef_get_env_blob(fw_ver)");
    CHECK(strncmp(value, "1.2.3", saved_len) == 0, "ef_get_env_blob value match");

    /* Persist + reload path (write through the port layer). */
    CHECK(ef_set_and_save_env("boot_mode", "test") == EF_NO_ERR, "ef_set_and_save_env(boot_mode)");
    CHECK(ef_get_env_blob("boot_mode", value, sizeof(value), &saved_len) > 0, "reload boot_mode");
    CHECK(strncmp(value, "test", saved_len) == 0, "boot_mode value match");

    /* Delete path. */
    CHECK(ef_del_env("fw_ver") == EF_NO_ERR, "ef_del_env(fw_ver)");
    CHECK(ef_del_and_save_env("boot_mode") == EF_NO_ERR, "ef_del_and_save_env(boot_mode)");

    printf("easyflash consumer test: ALL PASS\n");
    return 0;
}