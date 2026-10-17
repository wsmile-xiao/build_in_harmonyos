// consumer.c — clutter 1.26.4 消费测试程序（R34：实质调用被测库 API）
//
// OHOS 无显示服务（无 X11/Wayland/DRM），clutter_init() 无法建立任何
// 后端，故不能调用它。本程序改为实质调用 Clutter 中**不依赖显示上下文**
// 的真实 API 子集，以证明库被真正链接、加载并执行了库内代码：
//   1. 版本宏与 CLUTTER_CHECK_VERSION           —— 版本契约（编译期）
//   2. clutter_color_from_string/to_hls()        —— 颜色解析与色彩空间换算
//   3. clutter_units_from_pixels/to_pixels()     —— 单位换算（经 GObject
//      单例 ClutterSettings 取 GSettings，真实走库内对象系统）
//   4. clutter_actor_new() + set/get_size/名称读写 + unref —— Actor 对象
//      生命周期与属性系统（不要求 stage/backend，可在无显示下创建析构）
// 任一断言失败即返回非 0。
#include <clutter/clutter.h>
#include <math.h>
#include <stdio.h>

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(cond, msg)                                                \
    do {                                                                \
        g_checks++;                                                     \
        if (!(cond)) {                                                  \
            printf("FAIL: %s\n", (msg));                                \
            g_failed++;                                                 \
        } else {                                                        \
            printf("ok: %s\n", (msg));                                  \
        }                                                               \
    } while (0)

int main(void)
{
    /* 1. 版本 —— 编译期宏（库头文件提供的版本契约） */
    printf("clutter version: %d.%d.%d (hex %08x)\n", CLUTTER_MAJOR_VERSION,
           CLUTTER_MINOR_VERSION, CLUTTER_MICRO_VERSION, CLUTTER_VERSION_HEX);
    CHECK(CLUTTER_MAJOR_VERSION == 1 && CLUTTER_MINOR_VERSION == 26,
          "编译期版本宏为 1.26");
    CHECK(CLUTTER_CHECK_VERSION(1, 26, 0), "CLUTTER_CHECK_VERSION(1,26,0)");
    CHECK(!CLUTTER_CHECK_VERSION(1, 27, 0),
          "CLUTTER_CHECK_VERSION(1,27,0) 为假（版本上界正确）");

    /* 2. 颜色解析 + RGB<->HLS 换算 */
    {
        ClutterColor color;
        gfloat hue = -1.0f, lum = -1.0f, sat = -1.0f;

        CHECK(clutter_color_from_string(&color, "#7f7f7f"),
              "clutter_color_from_string(#7f7f7f)");
        CHECK(color.red == 0x7f && color.green == 0x7f && color.blue == 0x7f,
              "颜色分量解析正确 (0x7f,0x7f,0x7f)");
        clutter_color_to_hls(&color, &hue, &lum, &sat);
        CHECK(fabsf(hue) < 0.0001f, "灰度色 hue == 0");
        CHECK(lum >= 0.0f && lum <= 1.0f, "灰度色 luminance 在 [0,1]");
        CHECK(fabsf(sat) < 0.0001f, "灰度色 saturation == 0");
    }

    /* 3. 单位换算（走 ClutterSettings 单例，真实对象系统路径） */
    {
        ClutterUnits units;
        gfloat px;

        clutter_units_from_pixels(&units, 42.0f);
        px = clutter_units_to_pixels(&units);
        CHECK(fabsf(px - 42.0f) < 0.001f, "pixels 单位往返换算 == 42");
    }

    /* 4. Actor 对象生命周期（无 stage/backend 也可创建析构） */
    {
        ClutterActor *actor = clutter_actor_new();
        gfloat w = -1.0f, h = -1.0f;
        gchar *name = NULL;

        CHECK(actor != NULL, "clutter_actor_new() 返回非空");
        if (actor != NULL) {
            clutter_actor_set_size(actor, 320.0f, 240.0f);
            clutter_actor_get_size(actor, &w, &h);
            CHECK(fabsf(w - 320.0f) < 0.001f && fabsf(h - 240.0f) < 0.001f,
                  "actor set/get_size 往返一致 (320x240)");

            /* 属性系统（GObject 属性 + 库内属性定义）。
             * reactive 的上游默认值为 FALSE（clutter-actor.c 的
             * g_param_spec_boolean("reactive", ..., FALSE, ...)），
             * 此处断言读取值与上游默认契约一致。 */
            clutter_actor_set_name(actor, "ohos-clutter-consumer");
            name = clutter_actor_get_name(actor);
            CHECK(name != NULL && strcmp(name, "ohos-clutter-consumer") == 0,
                  "actor 名称属性往返一致");

            CHECK(clutter_actor_get_reactive(actor) == FALSE,
                  "actor 默认 reactive 为假（与上游属性默认值契约一致）");

            /* 可写性：设置后读取应反映新值 */
            clutter_actor_set_reactive(actor, TRUE);
            CHECK(clutter_actor_get_reactive(actor) == TRUE,
                  "actor set_reactive(TRUE) 后读取为真");

            g_object_unref(actor);
            printf("ok: actor unref 无崩溃\n");
        }
    }

    printf("SUMMARY: %d/%d checks passed\n", g_checks - g_failed, g_checks);
    return (g_failed == 0) ? 0 : 1;
}
