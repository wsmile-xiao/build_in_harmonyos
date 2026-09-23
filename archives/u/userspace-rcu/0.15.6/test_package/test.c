#include <stdio.h>
#include <urcu.h>

int main(void) {
    /* Test that we can call the RCU API (memb flavor, library call mode) */
    rcu_register_thread();
    urcu_memb_read_lock();
    urcu_memb_read_unlock();
    rcu_unregister_thread();
    printf("userspace-rcu API test: OK\n");
    return 0;
}
