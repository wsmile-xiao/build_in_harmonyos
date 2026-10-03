/*
 * libgoa 3.58.1 消费者契约测试。
 *
 * 所有断言都作用在 libgoa-1.0.so.0 的导出符号上，因此包缺失、符号缺失或
 * ABI 不匹配时会在链接期或运行期直接失败（对应 L1e 反向验证）。
 */
#include <stdio.h>
#include <string.h>

#define GOA_API_IS_SUBJECT_TO_CHANGE
#include <goa/goa.h>

static int failures;

#define CHECK(cond, what)                                                    \
    do {                                                                     \
        if (cond) {                                                          \
            printf("ok   - %s\n", what);                                     \
        } else {                                                             \
            fprintf(stderr, "FAIL - %s\n", what);                            \
            failures++;                                                      \
        }                                                                    \
    } while (0)

int main(void)
{
    GError *error = NULL;
    GoaClient *client;

    /* 1. goaconfig.h 的编译期版本宏（安装到 lib/goa-1.0/include） */
    CHECK(GOA_MAJOR_VERSION == 3 && GOA_MINOR_VERSION == 58 && GOA_MICRO_VERSION == 1,
          "goaconfig.h: GOA_MAJOR/MINOR/MICRO_VERSION == 3.58.1");
    CHECK(GOA_CHECK_VERSION(3, 58, 1), "goaversion.h: GOA_CHECK_VERSION(3,58,1)");

    /* 2. goaversion.c 导出的版本全局量与版本检查函数 */
    CHECK(goa_major_version == 3 && goa_minor_version == 58 && goa_micro_version == 1,
          "libgoa-1.0: goa_major/minor/micro_version == 3.58.1");
    CHECK(goa_check_version(3, 58, 1) == NULL,
          "libgoa-1.0: goa_check_version(3,58,1) == NULL");
    CHECK(goa_check_version(3, 99, 0) != NULL,
          "libgoa-1.0: goa_check_version(3,99,0) 返回错误说明");

    /* 3. goaerror.c 的错误域 */
    CHECK(goa_error_quark() != 0, "libgoa-1.0: goa_error_quark() != 0");

    /* 4. GObject 类型系统：本库类型 + gdbus-codegen 生成的 D-Bus 代理类型 */
    CHECK(g_type_name(GOA_TYPE_CLIENT) != NULL
          && strcmp(g_type_name(GOA_TYPE_CLIENT), "GoaClient") == 0,
          "GOA_TYPE_CLIENT -> \"GoaClient\"");
    CHECK(g_type_is_a(GOA_TYPE_CLIENT, G_TYPE_OBJECT), "GoaClient 继承自 GObject");
    CHECK(GOA_TYPE_OBJECT != 0 && GOA_TYPE_ACCOUNT != 0 && GOA_TYPE_MANAGER != 0,
          "goa-generated.h: GoaObject/GoaAccount/GoaManager 类型已注册");

    /* 5. 主入口真实调用：OHOS 上没有会话总线 / goa-daemon，
          结果必须是"拿到 client"或"拿到 GError"，不能两者皆空。 */
    client = goa_client_new_sync(NULL, &error);
    CHECK(client != NULL || error != NULL,
          "goa_client_new_sync() 返回 GoaClient 或 GError");
    if (client != NULL) {
        CHECK(GOA_IS_CLIENT(client), "goa_client_new_sync() 返回的对象是 GoaClient");
        CHECK(goa_client_get_object_manager(client) != NULL
              || goa_client_get_manager(client) != NULL,
              "GoaClient 暴露了 D-Bus object manager / manager");
        g_object_unref(client);
    } else {
        printf("info - goa_client_new_sync() 未连接上会话总线（OHOS 无 goa-daemon）：%s\n",
               error->message);
        g_clear_error(&error);
    }

    if (failures == 0) {
        printf("libgoa 3.58.1 consumer contract: all checks passed\n");
    }
    return failures == 0 ? 0 : 1;
}
