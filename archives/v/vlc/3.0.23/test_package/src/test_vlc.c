/*
 * test_vlc.c — vlc 3.0.23 真实调用测试
 *
 * 调用 libvlc 公共 API：
 *   - libvlc_get_version()：版本字符串非空且以 "3.0" 开头
 *   - libvlc_new(0, NULL) + libvlc_release()：实例创建/销毁
 *     （内部初始化线程系统/插件缓存，验证 libc 适配的完整性）
 *   - libvlc_get_compiler()：编译器串非空
 *
 * 退出码 0 = 全部断言通过；非 0 = 失败。
 */
#include <stdio.h>
#include <string.h>
#include <vlc/vlc.h>

static int failures = 0;

#define CHECK(cond, msg)                                   \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL: %s\n", (msg));                   \
            failures++;                                    \
        } else {                                           \
            printf("PASS: %s\n", (msg));                   \
        }                                                  \
    } while (0)

int main(void)
{
    /* 1. 版本字符串 */
    const char *ver = libvlc_get_version();
    CHECK(ver != NULL && ver[0] != '\0', "libvlc_get_version() returns non-empty string");
    CHECK(ver != NULL && strncmp(ver, "3.0", 3) == 0, "libvlc_get_version() starts with 3.0");

    /* 2. 编译器串 */
    const char *cc = libvlc_get_compiler();
    CHECK(cc != NULL && cc[0] != '\0', "libvlc_get_compiler() returns non-empty string");

    /* 3. 实例创建/销毁（初始化线程系统 + 插件缓存） */
    libvlc_instance_t *vlc = libvlc_new(0, NULL);
    CHECK(vlc != NULL, "libvlc_new(0, NULL) returns non-NULL instance");
    if (vlc != NULL) {
        libvlc_release(vlc);
        printf("PASS: libvlc_release() completed\n");
    }

    if (failures == 0) {
        printf("ALL TESTS PASSED\n");
    }
    return failures;
}
