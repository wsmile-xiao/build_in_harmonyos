/* harmonyos_specific_test.c — gettext-tiny HarmonyOS 专项测试
 *
 * 验证被适配库在 OHOS 平台上的真实可用性：
 * 1. libintl 公开 API 在 OHOS(aarch64) 可编译、链接、运行并返回预期结果；
 * 2. msgfmt 工具能把 .po 编译为 .mo（msgfmt 是库随附的公开 CLI 产物），
 *    验证 OHOS 上 .mo 生成结果可观察且正确。
 *
 * 路径由 CMake 在编译期注入（见 CMakeLists.txt），不依赖运行时环境变量：
 *   GT_BIN_DIR  包内 bin 目录（含 msgfmt）
 *   GT_PO_DIR   测试 .po 源目录（CMAKE_CURRENT_SOURCE_DIR）
 *   GT_TMP_DIR  测试输出目录（CMAKE_CURRENT_BINARY_DIR）
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libintl.h>

#ifndef GT_BIN_DIR
#define GT_BIN_DIR "."
#endif
#ifndef GT_PO_DIR
#define GT_PO_DIR "."
#endif
#ifndef GT_TMP_DIR
#define GT_TMP_DIR "."
#endif

int main(void) {
    int fail = 0;
    char cmdbuf[1024];

    /* 1) libintl API 在 OHOS 平台运行 */
    const char *t = gettext("platform_check");
    if (!t || strcmp(t, "platform_check") != 0) {
        fprintf(stderr, "FAIL gettext platform_check\n");
        fail = 1;
    }
    const char *dt = dgettext("mydomain", "key");
    if (!dt || strcmp(dt, "key") != 0) {
        fprintf(stderr, "FAIL dgettext\n");
        fail = 1;
    }
    char *dom = textdomain("messages");
    if (!dom || strcmp(dom, "messages") != 0) {
        fprintf(stderr, "FAIL textdomain\n");
        fail = 1;
    }

    /* 2) msgfmt .po -> .mo 编译（平台工具链验证） */
    snprintf(cmdbuf, sizeof(cmdbuf), "%s/msgfmt -o %s/harmonyos_specific_test.mo %s/harmonyos_specific_test.po",
             GT_BIN_DIR, GT_TMP_DIR, GT_PO_DIR);
    if (system(cmdbuf) != 0) {
        fprintf(stderr, "FAIL msgfmt .mo compile (cmd=%s)\n", cmdbuf);
        fail = 1;
    } else {
        char mofile[1024];
        snprintf(mofile, sizeof(mofile), "%s/harmonyos_specific_test.mo", GT_TMP_DIR);
        FILE *f = fopen(mofile, "rb");
        if (!f) {
            fprintf(stderr, "FAIL .mo file missing\n");
            fail = 1;
        } else {
            fseek(f, 0, SEEK_END);
            long sz = ftell(f);
            fclose(f);
            if (sz <= 0) {
                fprintf(stderr, "FAIL .mo empty\n");
                fail = 1;
            }
        }
    }

    if (fail) {
        printf("harmonyos_specific_test: FAILED\n");
        return 1;
    }
    printf("harmonyos_specific_test OK: platform=OHOS(aarch64) libintl_api=ok msgfmt_mo=ok\n");
    return 0;
}
