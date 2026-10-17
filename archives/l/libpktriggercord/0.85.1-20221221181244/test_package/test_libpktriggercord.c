/*
 * test_libpktriggercord.c — 消费者视角功能测试（conan test_package / L1）
 *
 * 覆盖 libpktriggercord 真实导出 API，全部为不依赖相机硬件的纯逻辑路径：
 *   1) 日志级别状态机  pslr_set_verbosity / pslr_get_verbosity / pslr_verbosity_enabled
 *   2) 枚举→字符串表    pslr_get_color_space_str
 *   3) 字符串→枚举表    pslr_get_drive_mode
 *   4) AF 点位图展开     pslr_get_af11_point_str
 *   5) 镜头库表          pslr_get_lens_name（内嵌 exiftool 数据）
 *   6) 文件格式表        pslr_get_user_file_format_t
 *   7) 版本/版权串       pslr_copyright
 *   8) 日志写出          pslr_write_log
 * 用法：./test_libpktriggercord [result-file]
 *   除 stdout 外，另把逐项与汇总写入 result-file，供 conan test() 解析真实计数
 *   （避免测试统计与代码常量手工同步）。
 * 注意：上游 pslr_scsi.h 已定义 CHECK(x)，本文件断言宏因此命名为 EXPECT。
 */
#include <pslr.h>
#include <pslr_enum.h>
#include <pslr_lens.h>
#include <pslr_log.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int discovered = 0;
static int passed = 0;
static FILE *resfp = NULL;

#define EXPECT(label, cond)                                                     \
    do {                                                                        \
        int _ok;                                                                \
        discovered++;                                                           \
        _ok = (cond) ? 1 : 0;                                                   \
        passed += _ok;                                                          \
        printf("%s %s\n", _ok ? "PASS" : "FAIL", (label));                      \
        if (resfp)                                                              \
            fprintf(resfp, "case %s %s\n", (label), _ok ? "pass" : "fail");     \
    } while (0)

int main(int argc, char **argv)
{
    if (argc > 1) {
        resfp = fopen(argv[1], "w");
        if (!resfp) {
            fprintf(stderr, "cannot write result file: %s\n", argv[1]);
            return 2;
        }
    }

    /* 1) verbosity 状态机 */
    pslr_set_verbosity(PSLR_WARNING);
    EXPECT("verbosity_set_get_roundtrip", pslr_get_verbosity() == PSLR_WARNING);
    EXPECT("verbosity_debug_disabled_at_warning",
           pslr_verbosity_enabled(PSLR_DEBUG) == false);
    pslr_set_verbosity(PSLR_DEBUG);
    EXPECT("verbosity_debug_enabled_at_debug",
           pslr_verbosity_enabled(PSLR_DEBUG) == true);

    /* 2) 枚举 -> 字符串（上游 pslr_enum.c 表） */
    const char *cs = pslr_get_color_space_str(PSLR_COLOR_SPACE_ADOBERGB);
    EXPECT("color_space_str_adobergb", cs != NULL && strcmp(cs, "AdobeRGB") == 0);

    /* 3) 字符串 -> 枚举 */
    EXPECT("drive_mode_from_str_continuous_hi",
           pslr_get_drive_mode((char *)"Continuous-HI") == PSLR_DRIVE_MODE_CONTINUOUS_HI);

    /* 4) AF 点位图展开（0 -> "none"；两个置位 -> 逗号分隔） */
    const char *af0 = pslr_get_af11_point_str(0);
    EXPECT("af11_point_zero_is_none", af0 != NULL && strcmp(af0, "none") == 0);
    char *af3 = pslr_get_af11_point_str(0x3);
    EXPECT("af11_point_bits_comma", af3 != NULL && strchr(af3, ',') != NULL);
    free(af3);

    /* 5) 内嵌 exiftool 镜头表：已知 id 有名，未知 id 返回空串 */
    const char *lens00 = pslr_get_lens_name(0, 0);
    EXPECT("lens_name_known", lens00 != NULL && strlen(lens00) > 0);
    const char *lens_bad = pslr_get_lens_name(0xffff, 0xffff);
    EXPECT("lens_name_unknown_is_empty", lens_bad != NULL && lens_bad[0] == '\0');

    /* 6) 用户文件格式表 pslr_user_file_formats[3] */
    user_file_format_t *dng = pslr_get_user_file_format_t(USER_FILE_FORMAT_DNG);
    EXPECT("user_file_format_dng",
           dng != NULL && dng->file_format_name != NULL &&
           strcmp(dng->file_format_name, "DNG") == 0 &&
           strcmp(dng->extension, "dng") == 0);
    EXPECT("user_file_format_out_of_range_null",
           pslr_get_user_file_format_t(USER_FILE_FORMAT_MAX) == NULL);

    /* 7) 版权串（上游硬编码，确认库数据/文本段被正确链接） */
    char *cr = pslr_copyright();
    EXPECT("copyright_contains_author",
           cr != NULL && strstr(cr, "Andras Salamon") != NULL);
    free(cr);

    /* 8) 日志路径可执行且不崩溃 */
    pslr_write_log(PSLR_WARNING, "libpktriggercord test_package log line\n");
    EXPECT("write_log_does_not_crash", 1);

    printf("RESULT discovered=%d passed=%d failed=%d\n",
           discovered, passed, discovered - passed);
    fflush(stdout);
    if (resfp) {
        fprintf(resfp, "RESULT discovered=%d passed=%d failed=%d\n",
                discovered, passed, discovered - passed);
        fclose(resfp);
    }
    return (passed == discovered && discovered > 0) ? 0 : 1;
}
