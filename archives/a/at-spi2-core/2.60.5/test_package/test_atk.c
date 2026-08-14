#include <atk/atk.h>
#include <atspi/atspi.h>
#include <stdio.h>

/*
 * Real ATK/atspi smoke test (R34: 必须实质调用被测 API/二进制，禁止空壳)。
 *
 *  1) atk:  创建 AtkObject、设置/查询角色、atk_role_get_name() 返回角色名
 *  2) atspi: 取 atspi_init()/atspi_get_desktop() 的函数地址做链接级验证
 *             （运行时需要 D-Bus accessibility bus，OHOS 无 dbus-daemon，
 *               因此不做总线连接，只验证库可链接）
 *
 * 返回非 0 即失败。
 */
int main(void) {
    int failures = 0;

    /* atk: GObject 类型系统 + 角色 API */
    AtkObject *obj = ATK_OBJECT(g_object_new(ATK_TYPE_OBJECT, NULL));
    if (obj == NULL) {
        fprintf(stderr, "FAIL: ATK_TYPE_OBJECT / g_object_new\n");
        return 1;
    }
    atk_object_set_role(obj, ATK_ROLE_PUSH_BUTTON);
    AtkRole role = atk_object_get_role(obj);
    if (role != ATK_ROLE_PUSH_BUTTON) {
        fprintf(stderr, "FAIL: atk_object_get_role returned %d\n", (int)role);
        failures++;
    }
    const char *name = atk_role_get_name(role);
    if (name == NULL || name[0] == '\0') {
        fprintf(stderr, "FAIL: atk_role_get_name returned empty\n");
        failures++;
    }
    g_object_unref(obj);

    /* atspi: 链接级验证（函数地址引用强制符号解析，不实际调用） */
    gint (*init_fn)(void) = atspi_init;
    AtspiAccessible *(*desktop_fn)(gint) = atspi_get_desktop;
    if (init_fn == NULL || desktop_fn == NULL) {
        fprintf(stderr, "FAIL: atspi symbols not linkable\n");
        failures++;
    }

    if (failures == 0) {
        printf("at-spi2-core 2.60.5 OK: atk role API + atspi linkage verified (role=%s)\n",
               name ? name : "(null)");
    }
    return failures;
}
