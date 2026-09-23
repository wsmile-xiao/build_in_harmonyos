#include <libdbustest/dbus-test.h>
#include <stdio.h>

int main(void)
{
    DbusTestService *service = NULL;
    DbusTestTask *task = NULL;
    DbusTestProcess *process = NULL;

    /* OHOS 无运行中的 D-Bus 会话（dbus-daemon），仅做构造/销毁的实质调用，
     * 验证 libdbustest 可链接、公开 API 可调用（R34）。 */
    task = dbus_test_task_new();
    if (task == NULL) {
        fprintf(stderr, "FAIL: dbus_test_task_new returned NULL\n");
        return 1;
    }
    dbus_test_task_set_name(task, "consumer-check");

    service = dbus_test_service_new(NULL);
    if (service == NULL) {
        fprintf(stderr, "FAIL: dbus_test_service_new returned NULL\n");
        g_object_unref(task);
        return 1;
    }
    dbus_test_service_add_task(service, task);

    process = dbus_test_process_new("/bin/true");
    if (process == NULL) {
        fprintf(stderr, "FAIL: dbus_test_process_new returned NULL\n");
        g_object_unref(service);
        return 1;
    }
    dbus_test_service_add_task(service, DBUS_TEST_TASK(process));

    /* 不调用 dbus_test_service_run（需运行 dbus-daemon）；仅析构验证 */
    g_object_unref(service);

    printf("OK: dbustest libdbustest link + construct/destruct API callable\n");
    return 0;
}
