#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include <urcu.h>
#include <urcu/pointer.h>

/* 消费者测试：实质调用 liburcu 公开 API（R34）
 * 使用读锁/读解锁 + synchronize_rcu 验证库可链接可运行 */
int main(void) {
    int value = 42;
    int *ptr = &value;
    int *read;

    rcu_read_lock();
    read = rcu_dereference(ptr);
    if (read == NULL || *read != 42) {
        fprintf(stderr, "liburcu rcu_dereference failed\n");
        return 1;
    }
    rcu_read_unlock();

    synchronize_rcu();

    printf("liburcu 0.15.6 consumer test: OK (read=%d)\n", *read);
    return 0;
}
