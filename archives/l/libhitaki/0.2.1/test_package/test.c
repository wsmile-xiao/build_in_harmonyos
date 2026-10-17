#include <stdio.h>
#include <stdlib.h>
#include <glib.h>
#include <glib-object.h>

#include <hitaki.h>

/* 消费者冒烟测试：仅用本库安装/导出的公开头文件与公开 API，
 * 验证第三方使用者能编译、链接并调用 libhitaki。
 * libhitaki 面向 IEEE1394 ALSA HwDep 设备：无真实设备时 hitaki_snd_unit_new
 * 仍返回合法 GObject 实例（设备操作在 open() 后才需要硬件），这里验证
 * 对象实例化 + 属性访问 + 类型系统注册 + GIR 枚举值可观察结果。 */

static void test_snd_unit_object(void)
{
    HitakiSndUnit *unit = hitaki_snd_unit_new();
    gchar *name = NULL;
    GValue value = G_VALUE_INIT;

    if (unit == NULL) {
        g_printerr("FAIL: hitaki_snd_unit_new() returned NULL\n");
        exit(1);
    }
    if (!HITAKI_IS_SND_UNIT(unit)) {
        g_printerr("FAIL: object not HitakiSndUnit\n");
        exit(1);
    }

    name = g_strdup_printf("%s", G_OBJECT_TYPE_NAME(unit));
    if (name == NULL || !g_str_equal(name, "HitakiSndUnit")) {
        g_printerr("FAIL: unexpected type name '%s'\n", name ? name : "(null)");
        exit(1);
    }

    /* 可观察属性: unit-type 枚举应为 ALSA firewire 设备类型之一 */
    g_object_get_property(G_OBJECT(unit), "unit-type", &value);
    if (!G_VALUE_HOLDS_ENUM(&value)) {
        g_printerr("FAIL: unit-type property not an enum GValue\n");
        exit(1);
    }
    g_value_unset(&value);

    g_clear_object(&unit);
    g_free(name);
    printf("test_libhitaki consumer: OK (HitakiSndUnit instantiated, type=%s, "
           "unit-type enum readable)\n", "HitakiSndUnit");
}

int main(void)
{
    test_snd_unit_object();
    return 0;
}