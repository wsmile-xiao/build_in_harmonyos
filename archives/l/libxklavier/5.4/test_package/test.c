/* test_package — libxklavier 5.4 消费者测试
 *
 * 真实调用库 API（R34）：xkl_engine_get_type / xkl_engine_get_instance /
 * xkl_config_item_new(+set/get_name) / xkl_config_rec_new /
 * xkl_set_debug_level / xkl_get_last_error。
 *
 * OHOS 无 X server：xkl_engine_get_instance(NULL) 是库内已处理的
 * 安全路径（返回 NULL，不崩溃），既验证了库加载/链接，也验证了
 * NULL 防护；无法在此环境跑完整的 XKB 后端（需 XOpenDisplay）。
 */
#include <stdio.h>
#include <string.h>

#include <glib-object.h>
#include <libxklavier/xklavier.h>

static int g_failures = 0;

#define CHECK(cond, msg) \
    do { \
        if (cond) { \
            printf("PASS: %s\n", msg); \
        } else { \
            fprintf(stderr, "FAIL: %s\n", msg); \
            g_failures++; \
        } \
    } while (0)

int main(void) {
    GType engine_type;

    /* 1. GObject 类型注册（xkl_engine_get_type 是公开导出符号） */
    engine_type = xkl_engine_get_type();
    CHECK(engine_type != 0, "xkl_engine_get_type() registers XklEngine GType");

    /* 2. 引擎实例：OHOS 无 X display，NULL 输入必须安全返回 NULL */
    CHECK(xkl_engine_get_instance(NULL) == NULL,
          "xkl_engine_get_instance(NULL) returns NULL safely");

    /* 3. 配置项对象 + 名称读写往返 */
    {
        XklConfigItem *item = xkl_config_item_new();
        CHECK(item != NULL, "xkl_config_item_new()");
        if (item != NULL) {
            xkl_config_item_set_name(item, "us");
            const gchar *name = xkl_config_item_get_name(item);
            CHECK(name != NULL && strcmp(name, "us") == 0,
                  "xkl_config_item name roundtrip");
            g_object_unref(G_OBJECT(item));
        }
    }

    /* 4. 配置记录对象 */
    {
        XklConfigRec *rec = xkl_config_rec_new();
        CHECK(rec != NULL, "xkl_config_rec_new()");
        if (rec != NULL) {
            g_object_unref(G_OBJECT(rec));
        }
    }

    /* 5. 调试/错误 API（不崩溃即可；返回可为 NULL） */
    xkl_set_debug_level(0);
    (void)xkl_get_last_error();
    CHECK(1, "xkl_set_debug_level()/xkl_get_last_error() callable");

    printf("libxklavier 5.4 API test finished: %d failure(s)\n", g_failures);
    return g_failures == 0 ? 0 : 1;
}
