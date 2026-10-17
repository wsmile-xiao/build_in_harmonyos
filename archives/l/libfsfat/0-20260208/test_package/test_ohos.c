/* libfsfat 0-20260208 鸿蒙专项消费者测试（仅在 settings.os=OHOS 时编译运行）。
 *
 * 覆盖两件事：
 * 1. 平台面：编译目标必须是 HarmonyOS（__OHOS__）、运行期 TMPDIR 必须是可写的
 *    非 /tmp 目录（HMDFS 上 /tmp 只读，见设备事实 §一.1/§一.10）；
 * 2. 功能面（运行/加载验证）：在 TMPDIR 下用公开 API 之外的纯 POSIX 写盘生成一个
 *    合法 FAT-16 镜像（1 个卷标项 + 1 个文件项），再用 libfsfat 公开 API 读取：
 *    卷签名 → 打开 → 文件系统类型 → 卷标 → 根目录项数 → 按路径取文件项 →
 *    文件大小 → 读回内容 → 关闭释放。这条链路同时验证共享库在 OHOS 上的
 *    真实加载与 FAT 解析路径，而不是只断言版本字符串。
 */
#ifndef __OHOS__
#error "test_ohos.c must be compiled for HarmonyOS"
#endif

#include <libfsfat.h>

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define FAT16_SECTOR_SIZE 512
#define FAT16_TOTAL_SECTORS 8192 /* 4 MiB: 数据簇 8095 >= 4085 → FAT-16 */
#define FAT16_RESERVED_SECTORS 1
#define FAT16_NUMBER_OF_FATS 2
#define FAT16_SECTORS_PER_FAT 32
#define FAT16_ROOT_ENTRIES 512
#define FAT16_ROOT_SECTORS \
    ((FAT16_ROOT_ENTRIES * 32 + FAT16_SECTOR_SIZE - 1) / FAT16_SECTOR_SIZE)
#define FAT16_DATA_START_SECTOR \
    (FAT16_RESERVED_SECTORS + FAT16_NUMBER_OF_FATS * FAT16_SECTORS_PER_FAT + \
     FAT16_ROOT_SECTORS)

static const char fat16_label[] = "OHOSTEST   ";
static const char file_content[] = "hello ohos\n";

static int check(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 0;
    }
    return 1;
}

static void put16(uint8_t *buffer, size_t offset, uint16_t value)
{
    buffer[offset] = (uint8_t)(value & 0xff);
    buffer[offset + 1] = (uint8_t)((value >> 8) & 0xff);
}

static void put32(uint8_t *buffer, size_t offset, uint32_t value)
{
    buffer[offset] = (uint8_t)(value & 0xff);
    buffer[offset + 1] = (uint8_t)((value >> 8) & 0xff);
    buffer[offset + 2] = (uint8_t)((value >> 16) & 0xff);
    buffer[offset + 3] = (uint8_t)((value >> 24) & 0xff);
}

/* 生成合法 FAT-16 镜像：卷标项 + 1 个 11 字节文件，簇 2 存内容。 */
static int create_fat16_image(const char *path)
{
    const size_t image_size = (size_t)FAT16_TOTAL_SECTORS * FAT16_SECTOR_SIZE;
    const size_t root_offset = (size_t)FAT16_RESERVED_SECTORS *
                               FAT16_SECTOR_SIZE +
                               (size_t)FAT16_NUMBER_OF_FATS *
                               FAT16_SECTORS_PER_FAT * FAT16_SECTOR_SIZE;
    uint8_t *image = (uint8_t *)calloc(1, image_size);
    size_t fat_offset;
    size_t index;
    int file_descriptor;
    ssize_t written;

    if (image == NULL) {
        return -1;
    }
    /* 引导扇区 BPB */
    image[0] = 0xeb;
    image[1] = 0x3c;
    image[2] = 0x90;
    memcpy(image + 3, "MSDOS5.0", 8);
    put16(image, 0x0b, FAT16_SECTOR_SIZE);
    image[0x0d] = 1; /* sectors per cluster */
    put16(image, 0x0e, FAT16_RESERVED_SECTORS);
    image[0x10] = FAT16_NUMBER_OF_FATS;
    put16(image, 0x11, FAT16_ROOT_ENTRIES);
    put16(image, 0x13, FAT16_TOTAL_SECTORS);
    image[0x15] = 0xf8; /* media descriptor: fixed disk */
    put16(image, 0x16, FAT16_SECTORS_PER_FAT);
    put16(image, 0x18, 32); /* sectors per track */
    put16(image, 0x1a, 2);  /* number of heads */
    image[0x24] = 0x80;     /* drive number */
    image[0x26] = 0x29;     /* extended boot signature */
    put32(image, 0x27, 0x12345678); /* volume serial number */
    memcpy(image + 0x2b, fat16_label, 11);
    memcpy(image + 0x36, "FAT16   ", 8);
    image[0x1fe] = 0x55;
    image[0x1ff] = 0xaa;

    /* 两份 FAT：0/1 保留项，簇 2（文件）结束标记 */
    for (index = 0; index < FAT16_NUMBER_OF_FATS; index++) {
        fat_offset = ((size_t)FAT16_RESERVED_SECTORS +
                      index * FAT16_SECTORS_PER_FAT) *
                     FAT16_SECTOR_SIZE;
        put16(image, fat_offset, 0xfff8);
        put16(image, fat_offset + 2, 0xffff);
        put16(image, fat_offset + 4, 0xffff);
    }
    /* 根目录：卷标项（属性 0x08）+ 文件项 HELLO.TXT（属性 0x20，簇 2） */
    memcpy(image + root_offset, fat16_label, 11);
    image[root_offset + 11] = 0x08;
    memcpy(image + root_offset + 32, "HELLO   TXT", 11);
    image[root_offset + 32 + 11] = 0x20;
    put16(image, root_offset + 32 + 26, 2);
    put32(image, root_offset + 32 + 28, (uint32_t)(sizeof(file_content) - 1));
    /* 簇 2 = 数据区首个扇区 */
    memcpy(
        image + (size_t)FAT16_DATA_START_SECTOR * FAT16_SECTOR_SIZE,
        file_content,
        sizeof(file_content) - 1);

    file_descriptor = open(path, O_CREAT | O_TRUNC | O_WRONLY, 0600);
    if (file_descriptor < 0) {
        free(image);
        return -1;
    }
    written = write(file_descriptor, image, image_size);
    if (written != (ssize_t)image_size) {
        close(file_descriptor);
        free(image);
        return -1;
    }
    if (close(file_descriptor) != 0) {
        free(image);
        return -1;
    }
    free(image);
    return 0;
}

int main(void)
{
    const char *tmpdir;
    char path[4096];
    char buffer[64];
    uint8_t file_system_format = 0;
    uint8_t label[64];
    int number_of_sub_entries = 0;
    int path_length;
    int result;
    int assertions = 0;
    size64_t file_size = 0;
    libfsfat_error_t *error = NULL;
    libfsfat_file_entry_t *file_entry = NULL;
    libfsfat_file_entry_t *root_directory = NULL;
    libfsfat_volume_t *volume = NULL;

    assertions++; /* 编译期 __OHOS__ 守卫（#error 已在编译阶段拦下非 OHOS 目标） */

    if (!check(
            strcmp(libfsfat_get_version(), "20260208") == 0,
            "libfsfat is not the expected OHOS package")) {
        return 1;
    }
    assertions++;

    tmpdir = getenv("TMPDIR");
    if (!check(
            tmpdir != NULL && tmpdir[0] != '\0' && strcmp(tmpdir, "/tmp") != 0,
            "OHOS test must use a writable TMPDIR instead of /tmp")) {
        return 1;
    }
    assertions++;

    path_length = snprintf(
        path, sizeof(path), "%s/libfsfat-ohos-fat16.img", tmpdir);
    if (!check(
            path_length > 0 && (size_t)path_length < sizeof(path),
            "could not construct the OHOS FAT-16 image path")) {
        return 1;
    }
    assertions++;

    if (!check(
            create_fat16_image(path) == 0,
            "could not create the FAT-16 image under TMPDIR")) {
        return 1;
    }
    assertions++;

    result = libfsfat_check_volume_signature(path, &error);
    if (!check(result == 1 && error == NULL, "FAT-16 image signature rejected")) {
        libfsfat_error_free(&error);
        unlink(path);
        return 1;
    }
    assertions++;

    result = libfsfat_volume_initialize(&volume, &error);
    if (!check(result == 1 && volume != NULL, "volume_initialize failed")) {
        libfsfat_error_free(&error);
        unlink(path);
        return 1;
    }
    assertions++;

    result = libfsfat_volume_open(
        volume, path, LIBFSFAT_OPEN_READ, &error);
    if (!check(result == 1 && error == NULL, "volume_open failed")) {
        libfsfat_error_free(&error);
        unlink(path);
        return 1;
    }
    assertions++;

    /* 该 API 写回的是单个字节的 LIBFSFAT_FILE_SYSTEM_FORMAT 枚举值（不是字符串） */
    result = libfsfat_volume_get_file_system_format(
        volume, &file_system_format, &error);
    if (!check(
            result == 1 &&
                file_system_format == LIBFSFAT_FILE_SYSTEM_FORMAT_FAT16,
            "file system format is not FAT-16")) {
        libfsfat_error_free(&error);
        unlink(path);
        return 1;
    }
    assertions++;

    memset(label, 0, sizeof(label));
    result = libfsfat_volume_get_utf8_label(volume, label, sizeof(label), &error);
    if (!check(
            result == 1 && strcmp((const char *)label, "OHOSTEST") == 0,
            "volume label mismatch")) {
        libfsfat_error_free(&error);
        unlink(path);
        return 1;
    }
    assertions++;

    result = libfsfat_volume_get_root_directory(volume, &root_directory, &error);
    if (!check(
            result == 1 && root_directory != NULL,
            "volume_get_root_directory failed")) {
        libfsfat_error_free(&error);
        unlink(path);
        return 1;
    }
    assertions++;

    result = libfsfat_file_entry_get_number_of_sub_file_entries(
        root_directory, &number_of_sub_entries, &error);
    if (!check(
            result == 1 && number_of_sub_entries == 1,
            "root directory sub file entry count mismatch")) {
        libfsfat_error_free(&error);
        unlink(path);
        return 1;
    }
    assertions++;

    result = libfsfat_volume_get_file_entry_by_utf8_path(
        volume,
        (const uint8_t *)"\\HELLO.TXT",
        strlen("\\HELLO.TXT"),
        &file_entry,
        &error);
    if (!check(
            result == 1 && file_entry != NULL,
            "volume_get_file_entry_by_utf8_path failed")) {
        libfsfat_error_free(&error);
        unlink(path);
        return 1;
    }
    assertions++;

    result = libfsfat_file_entry_get_size(file_entry, &file_size, &error);
    if (!check(
            result == 1 && file_size == (size64_t)(sizeof(file_content) - 1),
            "file entry size mismatch")) {
        libfsfat_error_free(&error);
        unlink(path);
        return 1;
    }
    assertions++;

    memset(buffer, 0, sizeof(buffer));
    result = libfsfat_file_entry_read_buffer(
        file_entry, buffer, sizeof(file_content) - 1, &error);
    if (!check(
            result == (int)(sizeof(file_content) - 1) &&
                memcmp(buffer, file_content, sizeof(file_content) - 1) == 0,
            "file entry content mismatch")) {
        libfsfat_error_free(&error);
        unlink(path);
        return 1;
    }
    assertions++;

    result = libfsfat_file_entry_free(&file_entry, &error);
    if (!check(
            result == 1 && file_entry == NULL,
            "file_entry_free failed")) {
        libfsfat_error_free(&error);
        unlink(path);
        return 1;
    }
    assertions++;

    result = libfsfat_file_entry_free(&root_directory, &error);
    if (!check(
            result == 1 && root_directory == NULL,
            "root directory free failed")) {
        libfsfat_error_free(&error);
        unlink(path);
        return 1;
    }
    assertions++;

    /* 该 API 的约定是「成功返回 0、失败返回 -1」 */
    result = libfsfat_volume_close(volume, &error);
    if (!check(result == 0 && error == NULL, "volume_close failed")) {
        libfsfat_error_free(&error);
        unlink(path);
        return 1;
    }
    assertions++;

    result = libfsfat_volume_free(&volume, &error);
    if (!check(
            result == 1 && volume == NULL, "volume_free failed")) {
        libfsfat_error_free(&error);
        unlink(path);
        return 1;
    }
    assertions++;

    errno = 0;
    if (!check(
            unlink(path) == 0 && access(path, F_OK) != 0 && errno == ENOENT,
            "OHOS temporary FAT-16 image cleanup failed")) {
        return 1;
    }
    assertions++;

    printf(
        "libfsfat OHOS-specific test: %d assertions passed "
        "(FAT-16 image round trip under TMPDIR)\n",
        assertions);
    return 0;
}
