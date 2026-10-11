#include <luksmeta.h>

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define IMAGE_SIZE (4u * 1024u * 1024u)

static int checks;
static int failures;

static void check(int condition, const char *message)
{
    checks++;
    if (condition) {
        printf("ok: %s\n", message);
    } else {
        failures++;
        printf("FAIL: %s\n", message);
    }
}

int main(void)
{
    static const luksmeta_uuid_t expected_uuid = {
        0x23, 0x14, 0x93, 0x59, 0x1b, 0x61, 0x48, 0x03,
        0xb8, 0x18, 0x77, 0x4a, 0xb7, 0x30, 0xfb, 0xec
    };
    static const char payload[] = "HarmonyOS luksmeta consumer test";
    const char *tmpdir = getenv("TMPDIR");
    char filename[512];
    char loaded[sizeof(payload)] = {0};
    luksmeta_uuid_t loaded_uuid = {0};
    struct crypt_device *device = NULL;
    int fd;
    int result;
    int slot;

    if (!tmpdir || tmpdir[0] == '\0')
        tmpdir = ".";
    snprintf(filename, sizeof(filename), "%s/luksmeta-api-XXXXXX", tmpdir);
    fd = mkstemp(filename);
    check(fd >= 0, "create sparse image");
    if (fd < 0)
        return 1;
    check(ftruncate(fd, IMAGE_SIZE) == 0, "size image to 4 MiB");
    close(fd);

    result = crypt_init(&device, filename);
    check(result == 0 && device != NULL, "crypt_init image");
    result = crypt_format(device, CRYPT_LUKS1, "aes", "xts-plain64",
                          NULL, NULL, 32, NULL);
    check(result == 0, "format LUKS1 header");
    check(luksmeta_test(device) == -ENOENT, "metadata initially absent");
    check(luksmeta_init(device) == 0, "initialize metadata area");
    check(luksmeta_test(device) == 0, "metadata header validates");

    slot = luksmeta_save(device, CRYPT_ANY_SLOT, expected_uuid,
                         payload, sizeof(payload));
    check(slot >= 0, "save payload to an available slot");
    result = luksmeta_load(device, slot, loaded_uuid, NULL, 0);
    check(result == (int) sizeof(payload), "query payload size");
    result = luksmeta_load(device, slot, loaded_uuid, loaded, sizeof(loaded));
    check(result == (int) sizeof(payload), "load payload bytes");
    check(memcmp(expected_uuid, loaded_uuid, sizeof(expected_uuid)) == 0,
          "loaded UUID matches");
    check(memcmp(payload, loaded, sizeof(payload)) == 0,
          "loaded payload matches");
    check(luksmeta_wipe(device, slot, expected_uuid) == 0, "wipe slot");
    check(luksmeta_load(device, slot, loaded_uuid, loaded, sizeof(loaded)) == -ENODATA,
          "wiped slot reports no data");
    check(luksmeta_nuke(device) == 0, "nuke metadata area");
    check(luksmeta_test(device) == -ENOENT, "metadata absent after nuke");

    crypt_free(device);
    unlink(filename);
    printf("luksmeta API: %d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
