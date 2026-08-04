#include <linux/types.h>
#include <linux/version.h>

int main(void)
{
    if (LINUX_VERSION_CODE <= 0) {
        return 1;
    }
    if (KERNEL_VERSION(5, 15, 0) <= 0) {
        return 2;
    }
    if (sizeof(__u32) != 4U) {
        return 3;
    }
    return 0;
}
