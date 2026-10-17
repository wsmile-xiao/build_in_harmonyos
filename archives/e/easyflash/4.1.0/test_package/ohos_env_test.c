/*
 * ohos_env_test.c — HarmonyOS-specific test for easyflash 4.1.0.
 *
 * Exercises API surface beyond the basic consumer CRUD test:
 *   - binary blob round-trip through ef_set_env_blob / ef_get_env_blob
 *     (payload contains 0x00 bytes, proving the RAM/NOR flash port
 *      masking semantics do not corrupt binary data)
 *   - save + re-initialisation NV persistence of binary blobs
 *   - default-env restore (ef_env_set_default + ef_load_env)
 *
 * Runs on OHOS (aarch64) against the installed libeasyflash + RAM port.
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

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { fprintf(stderr, "OHOS-TEST FAIL: %s\n", msg); failures++; } \
    else { printf("OHOS-TEST PASS: %s\n", msg); } \
} while (0)

int main(void) {
    /* Blob with embedded NUL bytes and high-bit values. */
    const unsigned char payload[33] = {
        0x00, 0x01, 0x7f, 0x80, 0xfe, 0xff, 0x00, 'E',
        'F', 0x00, 0x41, 0x42, 0x43, 0x00, 0xde, 0xad,
        0xbe, 0xef, 0x00, 0x11, 0x22, 0x33, 0x44, 0x55,
        0x66, 0x77, 0x88, 0x99, 0xaa, 0xbb, 0xcc, 0xdd,
        0x00
    };
    unsigned char out[64] = {0};
    size_t saved_len = 0;

    CHECK(easyflash_init() == EF_NO_ERR, "easyflash_init()");
    CHECK(ef_load_env() == EF_NO_ERR, "ef_load_env()");

    /* Binary blob round-trip (must preserve embedded NUL bytes). */
    CHECK(ef_set_env_blob("blob_cfg", payload, sizeof(payload)) == EF_NO_ERR,
          "ef_set_env_blob(binary payload)");
    CHECK(ef_get_env_blob("blob_cfg", out, sizeof(out), &saved_len) == (int)sizeof(payload),
          "ef_get_env_blob returns exact blob length");
    CHECK(saved_len == sizeof(payload), "saved_len == payload size");
    CHECK(memcmp(out, payload, sizeof(payload)) == 0,
          "blob bytes preserved (incl. embedded NUL)");

    /* Re-init and reload — blob must survive (NV persistence). */
    CHECK(easyflash_init() == EF_NO_ERR, "re-init easyflash_init()");
    CHECK(ef_load_env() == EF_NO_ERR, "re-init ef_load_env()");
    memset(out, 0, sizeof(out));
    CHECK(ef_get_env_blob("blob_cfg", out, sizeof(out), &saved_len) == (int)sizeof(payload),
          "blob survives re-init");
    CHECK(memcmp(out, payload, sizeof(payload)) == 0, "blob content matches after re-init");

    /* Default-env restore. */
    CHECK(ef_env_set_default() == EF_NO_ERR, "ef_env_set_default()");
    CHECK(ef_load_env() == EF_NO_ERR, "reload after set_default");
    {
        char defval[64] = {0};
        size_t dl = 0;
        size_t n = ef_get_env_blob("boot_times", defval, sizeof(defval), &dl);
        CHECK(n > 0 && dl == 1 && defval[0] == '0', "default env boot_times=0 restored");
    }

    if (failures == 0) {
        printf("ohos_env_test: ALL PASS\n");
        return 0;
    }
    fprintf(stderr, "ohos_env_test: %d FAILURES\n", failures);
    return 1;
}