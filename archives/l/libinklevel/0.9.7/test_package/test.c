/*
 * libinklevel 0.9.7 消费者测试（HarmonyOS PC / aarch64）
 *
 * 上游 0.9.7 没有测试套件（Makefile.am 无 TESTS / check_PROGRAMS），本测试是适配
 * 阶段补齐的消费者侧测试，全部通过公共头文件 inklevel.h 调用真实 API，不使用桩函数。
 *
 * 用例：
 *   TC1 公共 API 可用性   get_version_string() 返回非空且版本号正确
 *   TC2 参数校验错误路径   未知端口类型返回 UNKNOWN_PORT_SPECIFIED(-6)
 *   TC3 设备名解析错误路径 非法 BJNP URI 返回 BJNP_URI_INVALID(-17)
 *   TC4 无设备环境探测     USB 端口在无打印机环境下返回负值且不崩溃
 */

#include <stdio.h>
#include <string.h>

#include "inklevel.h"

static int failures = 0;

static void check(const char *name, int cond)
{
    printf("[%s] %s\n", cond ? "PASS" : "FAIL", name);
    if (!cond) {
        failures++;
    }
}

int main(void)
{
    struct ink_level level;
    char *version;
    int rc;

    /* TC1: 版本接口 —— 验证库可加载、公共符号可解析、版本号正确 */
    version = get_version_string();
    printf("       version = %s\n", version ? version : "(null)");
    check("TC1 get_version_string() 非空", version != NULL);
    check("TC1 版本号包含 0.9.7",
          version != NULL && strstr(version, "0.9.7") != NULL);

    /* TC2: 未知端口类型 —— 错误路径必须返回明确错误码，而不是崩溃 */
    memset(&level, 0, sizeof(level));
    rc = get_ink_level(99, NULL, 0, &level);
    printf("       get_ink_level(port=99) = %d (UNKNOWN_PORT_SPECIFIED=%d)\n",
           rc, UNKNOWN_PORT_SPECIFIED);
    check("TC2 未知端口返回 UNKNOWN_PORT_SPECIFIED",
          rc == UNKNOWN_PORT_SPECIFIED);

    /* TC3: 非法 BJNP URI —— 设备名解析失败路径 */
    memset(&level, 0, sizeof(level));
    rc = get_ink_level(CUSTOM_BJNP, "http://not-a-bjnp-uri", 0, &level);
    printf("       get_ink_level(CUSTOM_BJNP, \"http://not-a-bjnp-uri\") = %d "
           "(BJNP_URI_INVALID=%d)\n", rc, BJNP_URI_INVALID);
    check("TC3 非法 BJNP URI 返回 BJNP_URI_INVALID",
          rc == BJNP_URI_INVALID);

    /* TC4: 无打印机环境下的 USB 探测 —— 必须优雅返回负值 */
    memset(&level, 0, sizeof(level));
    rc = get_ink_level(USB, NULL, 0, &level);
    printf("       get_ink_level(USB) = %d\n", rc);
    check("TC4 无设备时 USB 探测返回负值", rc < 0);

    if (failures == 0) {
        printf("ALL CHECKS PASSED\n");
        return 0;
    }
    printf("%d CHECK(S) FAILED\n", failures);
    return 1;
}
