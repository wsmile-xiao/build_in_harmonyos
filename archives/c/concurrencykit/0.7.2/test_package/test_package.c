#include <ck_pr.h>
#include <ck_spinlock.h>

int main(void) {
    ck_spinlock_t lock = CK_SPINLOCK_INITIALIZER;
    unsigned int value = 0;
    ck_spinlock_lock(&lock);
    ck_pr_inc_uint(&value);
    ck_spinlock_unlock(&lock);
    return ck_pr_load_uint(&value) == 1 ? 0 : 1;
}
