#include <stdio.h>
#include <glib.h>
#include <zeitgeist-datamodel.h>

int main(void) {
    /* 真实调用 zeitgeist API（R34：非空壳）：创建 ZeitgeistEvent 实例、
     * 设置属性并校验——确保库符号真实链接、头文件与库版本匹配。
     * 注意：不调用 zeitgeist_log_new()——它初始化 D-Bus 连接，无
     * machine-id 的设备（OHOS）会挂起。event API 纯内存无此依赖。 */
    ZeitgeistEvent *event = zeitgeist_event_new();
    if (event == NULL) {
        fprintf(stderr, "FAIL: zeitgeist_event_new() returned NULL\n");
        return 1;
    }

    /* 校验 datamodel 类型系统已注册 */
    if (zeitgeist_event_get_type() == G_TYPE_INVALID) {
        fprintf(stderr, "FAIL: ZeitgeistEvent GType not registered\n");
        g_object_unref(event);
        return 1;
    }

    /* 调用 setter/getter 验证符号完整 */
    zeitgeist_event_set_interpretation(event, "test:interpretation");
    if (g_strcmp0(zeitgeist_event_get_interpretation(event),
                  "test:interpretation") != 0) {
        fprintf(stderr, "FAIL: interpretation set/get mismatch\n");
        g_object_unref(event);
        return 1;
    }

    g_object_unref(event);
    printf("zeitgeist test: OK (event instantiated, GType registered, "
           "set/get roundtrip)\n");
    return 0;
}
