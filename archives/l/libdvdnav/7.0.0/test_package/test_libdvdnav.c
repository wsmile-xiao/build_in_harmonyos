/*
 * test_libdvdnav.c — libdvdnav 7.0.0 真实调用测试
 *
 * 调用 libdvdnav 公共 API：
 *   - dvdnav_version()：版本字符串非空且以 "7.0" 开头
 *   - dvdnav_open(NULL, ...)：NULL 路径应返回 ERR（验证符号链接与错误路径）
 *   - dvdnav_err_to_string(NULL)：NULL 句柄错误串（不崩溃即可）
 *
 * 退出码 0 = 全部断言通过；非 0 = 失败。
 */
#include <stdio.h>
#include <string.h>
#include <dvdnav/dvdnav.h>

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
    const char *ver = dvdnav_version();
    CHECK(ver != NULL && ver[0] != '\0', "dvdnav_version() returns non-empty string");
    CHECK(ver != NULL && strncmp(ver, "7.0", 3) == 0, "dvdnav_version() starts with 7.0");

    /* 2. dvdnav_open(NULL) 应失败（NULL 路径，验证符号链接与错误处理） */
    dvdnav_t *nav = NULL;
    dvdnav_status_t st = dvdnav_open(&nav, NULL);
    CHECK(st == DVDNAV_STATUS_ERR, "dvdnav_open(NULL) returns DVDNAV_STATUS_ERR");
    CHECK(nav == NULL, "dvdnav_open(NULL) leaves handle NULL");

    /* 3. dvdnav_err_to_string(NULL) 不崩溃，返回值可为 NULL 或串 */
    const char *err = dvdnav_err_to_string(NULL);
    (void)err;  /* 仅验证不段错 */

    /* 4. DVDNAV_STATUS_OK / ERR 常量可见（编译期即验证，运行期再确认语义） */
    CHECK(DVDNAV_STATUS_ERR == 0, "DVDNAV_STATUS_ERR == 0");
    CHECK(DVDNAV_STATUS_OK == 1, "DVDNAV_STATUS_OK == 1");

    if (failures == 0) {
        printf("ALL TESTS PASSED\n");
        return 0;
    }
    printf("%d TEST(S) FAILED\n", failures);
    return 1;
}
