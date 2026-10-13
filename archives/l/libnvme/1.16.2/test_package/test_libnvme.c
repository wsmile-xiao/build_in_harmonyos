/* Consumer smoke test for the libnvme Conan package.
 *
 * Exercises the public API surface of both shipped libraries
 * (libnvme + libnvme-mi) without requiring NVMe hardware:
 *   - version string export
 *   - root object lifecycle
 *   - unconnected controller allocation + attribute access
 *   - config tree JSON (de)serialization round-trip (json-c path)
 *   - UUID string conversion helpers
 *   - TLS key export/import round-trip (OpenSSL path)
 */
#include <errno.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libnvme.h>
#include <libnvme-mi.h>

static int failures;

#define CHECK(cond, name)                                        \
    do {                                                         \
        if (cond) {                                              \
            printf("PASS: %s\n", name);                          \
        } else {                                                 \
            printf("FAIL: %s (errno=%d)\n", name, errno);        \
            failures++;                                          \
        }                                                        \
    } while (0)

int main(void)
{
    /* 1. version string */
    const char *ver = nvme_get_version(NVME_VERSION_PROJECT);
    CHECK(ver && strcmp(ver, "1.16.2") == 0, "nvme_get_version == 1.16.2");

    /* 2. root lifecycle */
    nvme_root_t r = nvme_create_root(stderr, LOG_ERR);
    CHECK(r != NULL, "nvme_create_root");

    /* 3. unconnected controller */
    nvme_ctrl_t c = nvme_create_ctrl(r, "nqn.2014-08.org.nvmexpress:uuid:"
                                     "ce4fee3e-c02c-11ee-8442-830d068a36c6",
                                     "tcp", "127.0.0.1", NULL, NULL, NULL);
    CHECK(c != NULL, "nvme_create_ctrl");
    if (c)
        nvme_free_ctrl(c);

    /* 4. config JSON round trip through a temp file in $TMPDIR */
    {
        const char *tmpdir = getenv("TMPDIR");
        char path[512];
        FILE *f;
        nvme_root_t r2 = nvme_create_root(stderr, LOG_ERR);
        int rc;

        snprintf(path, sizeof(path), "%s/libnvme-smoke-%d.json",
                 (tmpdir && *tmpdir) ? tmpdir : ".", (int)getpid());

        f = fopen(path, "w");
        CHECK(f != NULL, "fopen tmp config");
        if (f) {
            /* nvme_read_config() deserializes an array of host objects */
            fprintf(f, "[{\"hostnqn\":\"nqn.2014-08.org.nvmexpress:uuid:"
                       "ce4fee3e-c02c-11ee-8442-830d068a36c6\","
                       "\"hostid\":\"ce4fee3e-c02c-11ee-8442-830d068a36c6\"}]\n");
            fclose(f);
        }
        rc = nvme_read_config(r2, path);
        CHECK(rc == 0, "nvme_read_config(empty json)");
        nvme_free_tree(r2);
        remove(path);
    }

    /* 5. UUID helpers */
    {
        unsigned char uuid[NVME_UUID_LEN] = {0};
        char str[64] = {0};
        int rc = nvme_uuid_to_string(uuid, str);
        CHECK(rc == 0 && strcmp(str, "00000000-0000-0000-0000-000000000000") == 0,
              "nvme_uuid_to_string zero uuid");
    }

    /* 6. TLS key export/import round trip (OpenSSL DH-HMAC path) */
    {
        const char *encoded = NULL;
        const char *identity = NULL;
        unsigned char key[32];
        memset(key, 0x5a, sizeof(key));
        encoded = nvme_export_tls_key(key, sizeof(key));
        CHECK(encoded != NULL, "nvme_export_tls_key");
        if (encoded) {
            int key_len = 0;
            unsigned int hmac = 0;
            /* hmac is an out-param written unconditionally: pass a real
             * pointer (NULL would crash inside libnvme) */
            unsigned char *decoded = nvme_import_tls_key(encoded, &key_len, &hmac);
            CHECK(decoded != NULL && key_len == (int)sizeof(key) &&
                      hmac == NVME_HMAC_ALG_SHA2_256 &&
                      memcmp(decoded, key, sizeof(key)) == 0,
                  "nvme_import_tls_key round trip");
            free(decoded);
            free((void *)encoded);
        }
        identity = nvme_generate_tls_key_identity(
            "nqn.2014-08.org.nvmexpress:uuid:"
            "ce4fee3e-c02c-11ee-8442-830d068a36c6",
            "nqn.2014-08.org.nvmexpress:uuid:"
            "ce4fee3e-c02c-11ee-8442-830d068a36c6",
            1, NVME_HMAC_ALG_SHA2_256, key, sizeof(key));
        CHECK(identity != NULL, "nvme_generate_tls_key_identity");
        free(identity);
    }

    nvme_free_tree(r);

    /* 7. libnvme-mi root lifecycle */
    {
        nvme_root_t mr = nvme_mi_create_root(stderr, LOG_ERR);
        CHECK(mr != NULL, "nvme_mi_create_root");
        if (mr)
            nvme_mi_free_root(mr);
    }

    if (failures) {
        printf("test_libnvme: %d check(s) FAILED\n", failures);
        return 1;
    }
    printf("test_libnvme: all checks passed\n");
    return 0;
}
