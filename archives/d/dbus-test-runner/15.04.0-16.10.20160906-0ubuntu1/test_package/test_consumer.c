#include <libdbustest/dbus-test.h>
#include <stdio.h>

int main(void)
{
    DbusTestTask *task = dbus_test_task_new();
    if (task == NULL) {
        fputs("dbus_test_task_new returned NULL\n", stderr);
        return 1;
    }
    dbus_test_task_set_name(task, "consumer-check");
    g_object_unref(task);
    puts("dbus_test_task_new/set_name/unref passed");
    return 0;
}
