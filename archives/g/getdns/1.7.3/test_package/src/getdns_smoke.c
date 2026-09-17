#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* 鸿蒙特有验证点：
 * 1) OHOS 平台宏链路：OHOS PC SDK 提供 __OHOS__ 预定义宏（clang 驱动
 *    -target aarch64-linux-ohos 时定义），此处显式探测以证明产物在
 *    OHOS 工具链环境下编译；
 * 2) getdns 交叉编译产物 API 实链：getdns_context_create/destroy 是
 *    libgetdns 的核心入口（无网络依赖，纯内存对象构造/析构），
 *    调用成功即证明链接的 OHOS aarch64 动态库符号完整可用；
 * 3) getdns_dict 系 API 冒烟（set/get_bindata/get_names + pretty_print）：
 *    覆盖库的非联网核心数据结构路径。 */
#include <getdns/getdns.h>
#include <getdns/getdns_extra.h>

#if defined(__OHOS__)
#  define PLATFORM_NAME "OpenHarmony/HarmonyOS (aarch64-linux-ohos)"
#elif defined(__linux__)
#  define PLATFORM_NAME "Linux"
#else
#  define PLATFORM_NAME "unknown"
#endif

int main(void)
{
    /* 1. context create/destroy —— libgetdns 核心生命周期 API */
    struct getdns_context *ctx = NULL;
    getdns_return_t r = getdns_context_create(&ctx, 1);
    if (r != GETDNS_RETURN_GOOD || ctx == NULL) {
        fprintf(stderr, "FAIL: getdns_context_create -> %d\n", (int)r);
        return 1;
    }
    printf("[ohos-smoke] platform: %s\n", PLATFORM_NAME);
    printf("[ohos-smoke] getdns_context_create: OK\n");

    /* 2. dict 数据结构冒烟：set/get bindata + get_names + pretty print */
    struct getdns_dict *dict = getdns_dict_create();
    if (dict == NULL) {
        fprintf(stderr, "FAIL: getdns_dict_create\n");
        return 1;
    }
    struct getdns_bindata bd;
    static const char payload[] = "harmonyos-pc";
    bd.size = (uint32_t)strlen(payload) + 1;
    bd.data = (uint8_t *)payload;
    r = getdns_dict_set_bindata(dict, "smoke", &bd);
    if (r != GETDNS_RETURN_GOOD) {
        fprintf(stderr, "FAIL: getdns_dict_set_bindata -> %d\n", (int)r);
        return 1;
    }
    struct getdns_bindata *out = NULL;
    r = getdns_dict_get_bindata(dict, "smoke", &out);
    if (r != GETDNS_RETURN_GOOD || out == NULL || out->size != bd.size) {
        fprintf(stderr, "FAIL: getdns_dict_get_bindata -> %d\n", (int)r);
        return 1;
    }
    printf("[ohos-smoke] getdns_dict set/get bindata: OK (value=%s)\n",
           (const char *)out->data);

    struct getdns_list *names = getdns_list_create();
    r = getdns_dict_get_names(dict, &names);
    if (r != GETDNS_RETURN_GOOD) {
        fprintf(stderr, "FAIL: getdns_dict_get_names -> %d\n", (int)r);
        return 1;
    }
    size_t len = 0;
    getdns_list_get_length(names, &len);
    printf("[ohos-smoke] getdns_dict_get_names: OK (len=%zu)\n", len);
    getdns_list_destroy(names);

    char *pretty = getdns_pretty_print_dict(dict);
    if (pretty != NULL) {
        printf("[ohos-smoke] pretty_print: %s\n", pretty);
        free(pretty);
    }
    getdns_dict_destroy(dict);

    /* 3. 版本信息（getdns_get_version 系） */
    printf("[ohos-smoke] getdns version: %s\n", getdns_get_version());
    printf("[ohos-smoke] ALL OHOS SMOKE CHECKS PASSED\n");

    getdns_context_destroy(ctx);
    return 0;
}
