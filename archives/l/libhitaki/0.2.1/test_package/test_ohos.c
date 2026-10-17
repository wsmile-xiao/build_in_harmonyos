#include <stdio.h>
#include <stdlib.h>
#include <glib.h>
#include <glib-object.h>

#include <hitaki.h>

/* HarmonyOS 专项测试：验证 introspection 关闭后的 OHOS 构建仍然交付完整、
 * 可运行的公开 API 面（与消费者用例 test.c 不同维度——本用例直接回归
 * 无 GIR typelib 环境下的 GObject 类型系统注册与 glib-mkenums 生成的枚举
 * 符号，即本库 OHOS 适配（关闭 GIR）的核心行为）。
 * 静态链接包（shared=False）不做 dlopen，符号存在性由链接与版本脚本审计
 * 在配方/审计阶段另行核对。 */

static int check_type_registry(void)
{
    HitakiSndUnit *unit = hitaki_snd_unit_new();
    GType t;

    if (unit == NULL)
        return 1;
    if (!HITAKI_IS_SND_UNIT(unit))
        return 1;

    /* 无 GIR typelib 环境下类型仍注册（introspection 关闭只影响 typelib
     * 生成，不影响 C API 类型注册）。 */
    t = g_type_from_name("HitakiSndUnit");
    if (t == 0)
        return 1;

    /* 各设备类型 get_type 均应返回合法 GType（公开注册函数）。 */
    if (hitaki_snd_unit_get_type() == 0 ||
        hitaki_snd_dice_get_type() == 0 ||
        hitaki_snd_motu_get_type() == 0 ||
        hitaki_alsa_firewire_get_type() == 0)
        return 1;

    printf("OHOS-TEST OK: type registry intact without GIR typelib "
           "(HitakiSndUnit=%lu)\n", (unsigned long)g_type_from_name("HitakiSndUnit"));
    g_object_unref(unit);
    return 0;
}

static int check_enum_symbols(void)
{
    /* glib-mkenums 生成 hitaki_enums.h 后枚举符号仍与上游声明一致。
     * 上游枚举从 1 开始编号：DICE=1, FIREWORKS=2, ..., FIREFACE=8。 */
    if (HITAKI_ALSA_FIREWIRE_TYPE_DICE != 1 ||
        HITAKI_ALSA_FIREWIRE_TYPE_FIREWORKS != 2 ||
        HITAKI_ALSA_FIREWIRE_TYPE_FIREFACE != 8) {
        g_printerr("OHOS-TEST FAIL: enum value mismatch\n");
        return 1;
    }
    printf("OHOS-TEST OK: enum values match upstream declaration\n");
    return 0;
}

int main(void)
{
    if (check_type_registry() != 0) {
        g_printerr("OHOS-TEST FAIL: GObject type registry regression\n");
        return 1;
    }
    if (check_enum_symbols() != 0)
        return 1;
    return 0;
}