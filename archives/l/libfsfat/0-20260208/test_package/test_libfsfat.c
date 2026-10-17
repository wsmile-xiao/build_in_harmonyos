/* libfsfat 0-20260208 消费者测试（通用面，任何平台都编译运行）。
 *
 * 只经已安装包的公开头 <libfsfat.h> 与共享库 libfsfat.so 调用 API：
 * 版本、访问标志、codepage 正常/错误路径、volume 生命周期与错误路径。
 * 真实文件系统读取路径（合成 FAT-16 镜像的挂载、标签、目录与文件读取）
 * 在 OHOS 专项测试 test_ohos.c 中覆盖。
 */
#include <libfsfat.h>

#include <stdio.h>
#include <string.h>

static int check(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 0;
    }
    return 1;
}

int main(void)
{
    const char *version;
    const char *missing_path = "libfsfat-consumer-missing.img";
    int codepage = 0;
    int result;
    int assertions = 0;
    libfsfat_error_t *error = NULL;
    libfsfat_volume_t *volume = NULL;

    version = libfsfat_get_version();
    if (!check(version != NULL, "libfsfat_get_version returned NULL")) {
        return 1;
    }
    assertions++;

    /* 库自报版本是上游 libyal 版本串 20260208；本包的 Conan 版本号是
     * 0-20260208（发行版 0~20260208 命名口径，见 conandata.yml）。 */
    if (!check(strcmp(version, "20260208") == 0, "version mismatch")) {
        return 1;
    }
    assertions++;

    if (!check(
            libfsfat_get_access_flags_read() == LIBFSFAT_ACCESS_FLAG_READ,
            "read access flag mismatch")) {
        return 1;
    }
    assertions++;

    result = libfsfat_get_codepage(&codepage, &error);
    if (!check(result == 1 && error == NULL, "get_codepage failed")) {
        libfsfat_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfsfat_get_codepage(NULL, &error);
    if (!check(
            result == -1 && error != NULL,
            "get_codepage error path failed")) {
        libfsfat_error_free(&error);
        return 1;
    }
    assertions++;
    libfsfat_error_free(&error);

    result = libfsfat_set_codepage(0, &error);
    if (!check(result == 1 && error == NULL, "set_codepage failed")) {
        libfsfat_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfsfat_check_volume_signature(NULL, &error);
    if (!check(
            result == -1 && error != NULL,
            "check_volume_signature error path failed")) {
        libfsfat_error_free(&error);
        return 1;
    }
    assertions++;
    libfsfat_error_free(&error);

    result = libfsfat_check_volume_signature(missing_path, &error);
    if (!check(
            result == -1 && error != NULL,
            "check_volume_signature missing file error path failed")) {
        libfsfat_error_free(&error);
        return 1;
    }
    assertions++;
    libfsfat_error_free(&error);

    result = libfsfat_volume_initialize(&volume, &error);
    if (!check(
            result == 1 && volume != NULL && error == NULL,
            "volume_initialize failed")) {
        libfsfat_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfsfat_volume_open(
        volume, missing_path, LIBFSFAT_OPEN_READ, &error);
    if (!check(
            result == -1 && error != NULL,
            "volume_open missing file error path failed")) {
        libfsfat_error_free(&error);
        return 1;
    }
    assertions++;
    libfsfat_error_free(&error);

    result = libfsfat_volume_free(&volume, &error);
    if (!check(
            result == 1 && volume == NULL && error == NULL,
            "volume_free failed")) {
        libfsfat_error_free(&error);
        return 1;
    }
    assertions++;

    printf(
        "libfsfat 0-20260208 consumer test: %d assertions passed\n",
        assertions);
    return 0;
}
