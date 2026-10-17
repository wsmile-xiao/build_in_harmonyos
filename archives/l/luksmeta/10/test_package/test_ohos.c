#include <luksmeta.h>

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifndef __OHOS__
#error "This test verifies the HarmonyOS build specifically"
#endif

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
    const char *tmpdir = getenv("TMPDIR");
    char filename[512];
    struct crypt_device *device = NULL;
    int fd;
    int result;

    check(tmpdir != NULL && tmpdir[0] != '\0', "HarmonyOS TMPDIR is provided");
    if (!tmpdir || tmpdir[0] == '\0')
        return 1;

    snprintf(filename, sizeof(filename), "%s/luksmeta-ohos-XXXXXX", tmpdir);
    fd = mkstemp(filename);
    check(fd >= 0, "create image in HarmonyOS writable storage");
    if (fd < 0)
        return 1;
    check(ftruncate(fd, IMAGE_SIZE) == 0, "sparse-file growth succeeds");
    check(fsync(fd) == 0, "filesystem sync succeeds");
    close(fd);

    result = crypt_init(&device, filename);
    check(result == 0 && device != NULL, "libcryptsetup opens HarmonyOS path");
    result = crypt_format(device, CRYPT_LUKS1, "aes", "xts-plain64",
                          NULL, NULL, 32, NULL);
    check(result == 0, "LUKS1 formatting succeeds on HarmonyOS storage");
    check(luksmeta_init(device) == 0, "luksmeta initializes on HarmonyOS storage");
    check(luksmeta_test(device) == 0, "luksmeta header validates on HarmonyOS");
    check(luksmeta_nuke(device) == 0, "luksmeta cleanup succeeds on HarmonyOS");

    crypt_free(device);
    unlink(filename);
    printf("luksmeta HarmonyOS: %d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
