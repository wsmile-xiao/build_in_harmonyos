#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <spctag.h>

static int total;
static int failed;

static int check(int condition, const char *name)
{
    total++;
    if (condition) {
        printf("ok %d - %s\n", total, name);
    } else {
        failed++;
        printf("not ok %d - %s\n", total, name);
    }
    return condition;
}

static int write_fixture(const char *path, int text_tag)
{
    unsigned char data[256] = {0};
    FILE *file;

    memcpy(data, "SNES-SPC700 Sound File Data", 27);
    data[35] = 26;
    if (text_tag) {
        memcpy(data + 46, "Original text", 13);
        memcpy(data + 158, "12/31/1999", 11);
        memcpy(data + 169, "180", 3);
        memcpy(data + 172, "0500", 4);
    } else {
        memcpy(data + 46, "Original bin", 12);
        data[158] = 31;
        data[159] = 12;
        data[160] = 0xcf;
        data[161] = 0x07;
    }

    file = fopen(path, "wb");
    if (file == NULL)
        return 0;
    if (fwrite(data, sizeof(data), 1, file) != 1) {
        fclose(file);
        return 0;
    }
    return fclose(file) == 0;
}

static void test_text_tag(const char *path)
{
    FILE *file;

    check(write_fixture(path, 1), "create text fixture");
    file = fopen(path, "r+b");
    check(file != NULL, "open text fixture");
    if (file == NULL)
        return;

    check(spctag_init(file) == SPCTAG_SUCCESS, "initialize text tag");
    check(spctag_txt_tag == 1, "detect text tag");
    check(strcmp(spctag_get_songtitle(), "Original text") == 0,
          "read original text title");
    check(strcmp(spctag_get_dumpdate(), "12/31/1999") == 0,
          "read original text date");
    check(spctag_set_songtitle("Harmony song") == SPCTAG_SUCCESS,
          "set text song title");
    check(spctag_set_gametitle("Harmony game") == SPCTAG_SUCCESS,
          "set text game title");
    check(spctag_set_dumpername("OHOS") == SPCTAG_SUCCESS,
          "set text dumper");
    check(spctag_set_comments("ID666 round trip") == SPCTAG_SUCCESS,
          "set text comments");
    check(spctag_set_dumpdate("09/18/2026") == SPCTAG_SUCCESS,
          "set text date");
    check(spctag_set_length("240") == SPCTAG_SUCCESS, "set text length");
    check(spctag_set_fadelength("1500") == SPCTAG_SUCCESS,
          "set text fade length");
    check(spctag_set_artist("OpenHarmony") == SPCTAG_SUCCESS,
          "set text artist");
    check(spctag_set_defaultchannels("01010101") == SPCTAG_SUCCESS,
          "set text channels");
    check(spctag_set_emulator("Snes9x") == SPCTAG_SUCCESS,
          "set text emulator");
    check(spctag_save(file) == SPCTAG_SUCCESS, "save text tag");
    check(strcmp(spctag_get_songtitle(), "Harmony song") == 0,
          "read updated text title in memory");
    check(strcmp(spctag_get_defaultchannels(), "01010101") == 0,
          "read updated text channels in memory");
    check(strcmp(spctag_get_emulator(), "Snes9x") == 0,
          "read updated text emulator in memory");
    spctag_free();
    check(spctag_is_init == 0, "free text tag state");
    fclose(file);

    file = fopen(path, "r+b");
    check(file != NULL, "reopen text fixture");
    if (file == NULL)
        return;
    check(spctag_init(file) == SPCTAG_SUCCESS, "reinitialize text tag");
    check(strcmp(spctag_get_songtitle(), "Harmony song") == 0,
          "persist text song title");
    check(strcmp(spctag_get_gametitle(), "Harmony game") == 0,
          "persist text game title");
    check(strcmp(spctag_get_dumpdate(), "09/18/2026") == 0,
          "persist text date");
    check(strcmp(spctag_get_length(), "240") == 0, "persist text length");
    check(strcmp(spctag_get_fadelength(), "1500") == 0,
          "persist text fade length");
    check(strcmp(spctag_get_artist(), "OpenHarmony") == 0,
          "persist text artist");
    spctag_free();
    check(spctag_is_init == 0, "free reopened text tag state");
    fclose(file);
}

static void test_binary_tag(const char *path)
{
    FILE *file;

    check(write_fixture(path, 0), "create binary fixture");
    file = fopen(path, "r+b");
    check(file != NULL, "open binary fixture");
    if (file == NULL)
        return;
    check(spctag_init(file) == SPCTAG_SUCCESS, "initialize binary tag");
    check(spctag_txt_tag == 0, "detect binary tag");
    check(strcmp(spctag_get_dumpdate(), "12/31/1999") == 0,
          "read portable binary date");
    check(spctag_set_dumpdate("01/02/2025") == SPCTAG_SUCCESS,
          "set binary date");
    check(spctag_set_songtitle("Binary song") == SPCTAG_SUCCESS,
          "set binary title");
    check(spctag_set_defaultchannels("10101010") == SPCTAG_SUCCESS,
          "set binary channels");
    check(spctag_set_emulator("ZSNES") == SPCTAG_SUCCESS,
          "set binary emulator");
    check(spctag_save(file) == SPCTAG_SUCCESS, "save binary tag");
    spctag_free();
    check(spctag_is_init == 0, "free binary tag state");
    fclose(file);

    file = fopen(path, "r+b");
    check(file != NULL, "reopen binary fixture");
    if (file == NULL)
        return;
    check(spctag_init(file) == SPCTAG_SUCCESS, "reinitialize binary tag");
    check(strcmp(spctag_get_songtitle(), "Binary song") == 0,
          "persist binary title");
    check(strcmp(spctag_get_dumpdate(), "01/02/2025") == 0,
          "persist binary date");
    check(strcmp(spctag_get_defaultchannels(), "10101010") == 0,
          "persist binary channels");
    check(strcmp(spctag_get_emulator(), "ZSNES") == 0,
          "persist binary emulator");
    check(strcmp(LIBSPCTAG_VERSION_STR, "0.2") == 0, "public version macro");
    spctag_free();
    fclose(file);
}

int main(void)
{
    const char *text_path = "libspctag-text-test.spc";
    const char *binary_path = "libspctag-binary-test.spc";

    test_text_tag(text_path);
    test_binary_tag(binary_path);
    remove(text_path);
    remove(binary_path);

    printf("libspctag consumer assertions: %d/%d passed\n", total - failed, total);
    return failed == 0 && total == 48 ? 0 : 1;
}
