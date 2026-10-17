#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <spctag.h>

#ifndef __OHOS__
#error "test_ohos.c must be compiled by the HarmonyOS toolchain"
#endif

#ifndef __aarch64__
#error "HarmonyOS PC libspctag test requires an aarch64 target"
#endif

static int total;
static int failed;

static void check(int condition, const char *name)
{
    total++;
    if (condition) {
        printf("ok %d - %s\n", total, name);
    } else {
        failed++;
        printf("not ok %d - %s\n", total, name);
    }
}

static int create_binary_fixture(const char *path)
{
    unsigned char data[256] = {0};
    FILE *file;

    memcpy(data, "SNES-SPC700 Sound File Data", 27);
    data[35] = 26;
    data[158] = 18;
    data[159] = 9;
    data[160] = 0xea;
    data[161] = 0x07;

    file = fopen(path, "wb");
    if (file == NULL)
        return 0;
    if (fwrite(data, sizeof(data), 1, file) != 1) {
        fclose(file);
        return 0;
    }
    return fclose(file) == 0;
}

int main(void)
{
    const char *tmpdir = getenv("TMPDIR");
    char path[1024];
    FILE *file;

    check(1, "compiled with __OHOS__");
    check(sizeof(void *) == 8, "OHOS PC process is 64-bit");
    check(tmpdir != NULL && tmpdir[0] != '\0', "TMPDIR is configured");
    if (tmpdir == NULL || tmpdir[0] == '\0')
        return 1;

    snprintf(path, sizeof(path), "%s/libspctag-ohos-%ld.spc",
             tmpdir, (long)getpid());
    check(create_binary_fixture(path), "OHOS TMPDIR accepts an SPC fixture");
    file = fopen(path, "r+b");
    check(file != NULL, "reopen fixture from OHOS TMPDIR");
    if (file == NULL)
        return 1;
    check(spctag_init(file) == SPCTAG_SUCCESS && spctag_txt_tag == 0,
          "initialize binary ID666 on OHOS");
    check(spctag_set_songtitle("OHOS PC") == SPCTAG_SUCCESS &&
          spctag_save(file) == SPCTAG_SUCCESS,
          "write ID666 through the OHOS filesystem");
    spctag_free();
    fclose(file);

    file = fopen(path, "r+b");
    if (file != NULL && spctag_init(file) == SPCTAG_SUCCESS) {
        check(strcmp(spctag_get_songtitle(), "OHOS PC") == 0,
              "read persisted ID666 through the OHOS filesystem");
        spctag_free();
        fclose(file);
    } else {
        check(0, "read persisted ID666 through the OHOS filesystem");
        if (file != NULL)
            fclose(file);
    }
    remove(path);

    printf("libspctag OHOS assertions: %d/%d passed\n", total - failed, total);
    return failed == 0 && total == 8 ? 0 : 1;
}
