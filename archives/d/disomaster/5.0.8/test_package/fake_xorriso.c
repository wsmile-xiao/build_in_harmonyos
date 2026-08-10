/*
 * fake_xorriso - 模拟 xorriso 命令行行为的 C 程序
 *
 * 用于 disomaster test_package 的非破坏性测试。
 * 验证 DISOMaster 通过 QProcess 传递的参数列表格式是否正确，
 * 并输出模拟的 xorriso 响应供 DISOMaster 解析。
 * 不执行任何真实硬件操作。
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* 检查参数列表中是否包含指定字符串参数 */
static int has_arg(int argc, char **argv, const char *arg)
{
    int i;
    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], arg) == 0)
            return 1;
    }
    return 0;
}

/* 获取 -key 格式参数后面的值 */
static const char *get_arg_value(int argc, char **argv, const char *arg)
{
    int i;
    for (i = 1; i < argc - 1; i++) {
        if (strcmp(argv[i], arg) == 0)
            return argv[i + 1];
    }
    return NULL;
}

/* 获取 key=value 格式参数的值部分 */
static const char *get_kv_value(int argc, char **argv, const char *key)
{
    size_t keylen = strlen(key);
    int i;
    for (i = 1; i < argc; i++) {
        if (strncmp(argv[i], key, keylen) == 0 && argv[i][keylen] == '=')
            return argv[i] + keylen + 1;
    }
    return NULL;
}

int main(int argc, char **argv)
{
    int i;

    if (argc < 2) {
        fprintf(stderr, "fake_xorriso: no arguments provided\n");
        return 1;
    }

    /*
     * 模式 1: -as cdrecord（writeISO）
     * 参数: -as cdrecord -v dev=<device> blank=as_needed speed=<speed>k <isopath>
     */
    if (has_arg(argc, argv, "-as") && argc > 2 && strcmp(argv[2], "cdrecord") == 0) {
        if (!get_kv_value(argc, argv, "dev")) {
            fprintf(stderr, "fake_xorriso: missing dev= for cdrecord mode\n");
            return 2;
        }
        if (!has_arg(argc, argv, "blank=as_needed")) {
            fprintf(stderr, "fake_xorriso: missing blank=as_needed\n");
            return 3;
        }
        /* 输出进度和速度 */
        printf("Track 01: 10 of 20 MB written.\n");
        printf("5x.\n");
        printf("Track 01: 20 of 20 MB written.\n");
        printf("10x.\n");
        return 0;
    }

    /*
     * 模式 2: -dev <device> -end（acquireDevice）
     * 仅获取设备，不需要输出
     */
    if (has_arg(argc, argv, "-dev") && !has_arg(argc, argv, "-toc") &&
        !has_arg(argc, argv, "-check_media") && !has_arg(argc, argv, "-commit") &&
        !has_arg(argc, argv, "-blank") && has_arg(argc, argv, "-end")) {
        const char *dev = get_arg_value(argc, argv, "-dev");
        if (!dev) {
            fprintf(stderr, "fake_xorriso: missing device for -dev\n");
            return 4;
        }
        return 0;
    }

    /*
     * 模式 3: -dev <device> -toc -list_speeds -end（getDeviceProperty）
     * 输出模拟的设备属性信息
     */
    if (has_arg(argc, argv, "-dev") && has_arg(argc, argv, "-toc") &&
        has_arg(argc, argv, "-list_speeds") && has_arg(argc, argv, "-end")) {
        const char *dev = get_arg_value(argc, argv, "-dev");
        if (!dev) {
            fprintf(stderr, "fake_xorriso: missing device for -toc\n");
            return 5;
        }
        /* 输出模拟的介质属性 */
        printf("Media current: CD-RW\n");
        printf("Media status : is blank\n");
        printf("Media summary: 0 sessions, 0 data blocks, 0k data, 653m free\n");
        printf("Volume id : 'ISOIMAGE'\n");
        printf("Write speed : 1411k 70x\n");
        printf("Write speed : 705k 35x\n");
        return 0;
    }

    /*
     * 模式 4: -dev <device> ... -commit -end（commit）
     * 输出刻录进度和速度
     */
    if (has_arg(argc, argv, "-dev") && has_arg(argc, argv, "-commit") &&
        has_arg(argc, argv, "-end")) {
        const char *dev = get_arg_value(argc, argv, "-dev");
        if (!dev) {
            fprintf(stderr, "fake_xorriso: missing device for -commit\n");
            return 6;
        }
        if (!has_arg(argc, argv, "-volid")) {
            fprintf(stderr, "fake_xorriso: missing -volid for commit\n");
            return 7;
        }
        /* 输出刻录进度 */
        printf("50%% fifo\n");
        printf("100%% fifo\n");
        printf("50%% done\n");
        printf("100%% done\n");
        printf("10x.\n");
        return 0;
    }

    /*
     * 模式 5: -outdev <device> -blank as_needed -end（erase）
     * 输出擦除进度
     */
    if (has_arg(argc, argv, "-outdev") && has_arg(argc, argv, "-blank") &&
        has_arg(argc, argv, "as_needed") && has_arg(argc, argv, "-end") &&
        !has_arg(argc, argv, "-check_media")) {
        const char *dev = get_arg_value(argc, argv, "-outdev");
        if (!dev) {
            fprintf(stderr, "fake_xorriso: missing device for -blank\n");
            return 8;
        }
        printf("Blanking media...\n");
        printf("Blanking done.\n");
        return 0;
    }

    /*
     * 模式 6: -dev <device> -check_media -end（checkmedia）
     * 输出介质区域质量信息（全部良好）
     */
    if (has_arg(argc, argv, "-dev") && has_arg(argc, argv, "-check_media") &&
        has_arg(argc, argv, "-end") && !has_arg(argc, argv, "use=outdev")) {
        const char *dev = get_arg_value(argc, argv, "-dev");
        if (!dev) {
            fprintf(stderr, "fake_xorriso: missing device for -check_media\n");
            return 9;
        }
        /* 输出介质区域质量（0-100 全部良好） */
        printf("Media region : 0 100 <-\n");
        return 0;
    }

    /*
     * 模式 7: -outdev <device> -check_media use=outdev data_to=<path> -end（dumpISO）
     * 输出转储进度
     */
    if (has_arg(argc, argv, "-outdev") && has_arg(argc, argv, "-check_media") &&
        has_arg(argc, argv, "use=outdev") && has_arg(argc, argv, "-end")) {
        const char *dev = get_arg_value(argc, argv, "-outdev");
        if (!dev) {
            fprintf(stderr, "fake_xorriso: missing device for dumpISO\n");
            return 10;
        }
        printf("Dumping media to ISO image...\n");
        printf("50%% done\n");
        printf("100%% done\n");
        return 0;
    }

    /* 未识别的参数模式 */
    fprintf(stderr, "fake_xorriso: unrecognized argument pattern\n");
    for (i = 0; i < argc; i++) {
        fprintf(stderr, "  argv[%d] = %s\n", i, argv[i]);
    }
    return 99;
}
