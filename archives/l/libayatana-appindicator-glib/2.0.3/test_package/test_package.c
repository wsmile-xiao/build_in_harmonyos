/* test_package — 鸿蒙特有端到端消费者用例 for libayatana-appindicator-glib.
 *
 * 完整消费者流程（rule12：非纯断言，真实跑通功能/流程）：
 *   构造 AppIndicator → 设置 icon/attention_icon/title/label/status → 挂载
 *   GMenu 菜单与 GSimpleActionGroup 动作 → 经事件循环驱动"idle 延迟派发"的
 *   new-label 信号 → 校验信号回调真实触发（端到端链路）→ 校验 getter 回读
 *   一致 → 释放。信号延迟派发语义与上游 labelSignals 用例一致。
 *
 * 同目录 test-libappindicator.c 为上游单元测试（6 个 g_test 用例，未修改，
 * 逐字复制自 2.0.3 tag），一并真实编译执行（rule4）。
 */
#include <libayatana-appindicator-glib/ayatana-appindicator.h>
#include <gio/gio.h>
#include <stdio.h>

static gint g_label_signals = 0;

static void on_label_changed(AppIndicator *indicator, gchar *label, gchar *guide, gpointer data) {
    (void)indicator;
    (void)label;
    (void)guide;
    (void)data;
    g_label_signals++;
}

static gint g_failures = 0;

#define CHECK(cond, msg) \
    do { \
        if (!(cond)) { \
            fprintf(stderr, "FAIL: %s\n", msg); \
            g_failures++; \
        } \
    } while (0)

/* 迭代主循环，把 idle 中挂起的 new-label 信号派发到回调（与上游
 * labelSignalsCheck 同法），最多转 20 圈防死循环。 */
static void pump_main_context(void) {
    gint spins = 0;
    while (g_main_context_pending(NULL) && spins < 20) {
        g_main_context_iteration(NULL, TRUE);
        spins++;
    }
}

int main(void) {
    GMenu *menu = g_menu_new();
    GMenuItem *item = g_menu_item_new("退出", "app.quit");
    g_menu_append_item(menu, item);
    g_object_unref(item);

    GSimpleActionGroup *actions = g_simple_action_group_new();
    GSimpleAction *action = g_simple_action_new("quit", NULL);
    g_action_map_add_action(G_ACTION_MAP(actions), G_ACTION(action));
    g_object_unref(action);

    AppIndicator *indicator =
        app_indicator_new("test-package", "test-package-icon", APP_INDICATOR_CATEGORY_APPLICATION_STATUS);
    CHECK(indicator != NULL, "app_indicator_new()");

    app_indicator_set_status(indicator, APP_INDICATOR_STATUS_ACTIVE);
    app_indicator_set_icon(indicator, "test-package-icon", NULL);
    app_indicator_set_attention_icon(indicator, "test-package-attention", NULL);
    app_indicator_set_title(indicator, "Test Package");
    app_indicator_set_menu(indicator, menu);
    app_indicator_set_actions(indicator, actions);

    /* 端到端信号链路：new-label 经 idle 延迟派发 → 事件循环驱动回调 */
    g_signal_connect(G_OBJECT(indicator), "new-label", G_CALLBACK(on_label_changed), NULL);
    app_indicator_set_label(indicator, "hello", "guide");
    pump_main_context();
    CHECK(g_label_signals == 1, "new-label 信号经事件循环触发");

    /* 无变化不重复触发（上游 labelSignals 同语义） */
    g_label_signals = 0;
    app_indicator_set_label(indicator, "hello", "guide");
    pump_main_context();
    CHECK(g_label_signals == 0, "相同 label 不重复触发信号");

    /* getter 回读与 setter 一致 */
    CHECK(g_strcmp0(app_indicator_get_id(indicator), "test-package") == 0, "get_id()");
    CHECK(g_strcmp0(app_indicator_get_icon(indicator), "test-package-icon") == 0, "get_icon()");
    CHECK(g_strcmp0(app_indicator_get_attention_icon(indicator), "test-package-attention") == 0,
          "get_attention_icon()");
    CHECK(g_strcmp0(app_indicator_get_title(indicator), "Test Package") == 0, "get_title()");
    CHECK(g_strcmp0(app_indicator_get_label(indicator), "hello") == 0, "get_label()");
    CHECK(g_strcmp0(app_indicator_get_label_guide(indicator), "guide") == 0, "get_label_guide()");
    CHECK(app_indicator_get_status(indicator) == APP_INDICATOR_STATUS_ACTIVE, "get_status()");
    CHECK(app_indicator_get_category(indicator) == APP_INDICATOR_CATEGORY_APPLICATION_STATUS,
          "get_category()");

    g_object_unref(menu);
    g_object_unref(actions);
    g_object_unref(G_OBJECT(indicator));

    if (g_failures) {
        fprintf(stderr, "test_package FAILED: %d check(s)\n", g_failures);
        return 1;
    }
    puts("libayatana-appindicator-glib test_package OK (端到端消费者用例通过)");
    return 0;
}
