#include <linux/version.h>
#include <linux/types.h>
#include <linux/input.h>
#include <linux/ioctl.h>
#include <linux/if_ether.h>
#include <linux/input-event-codes.h>
#include <asm/byteorder.h>
#include <asm/posix_types.h>
#include <asm/unistd.h>

int main(void)
{
    /* 版本一致性断言（编译期）：包版本 6.12.77 必须与头文件声明一致 */
#if LINUX_VERSION_CODE != KERNEL_VERSION(6, 12, 77)
#error "kernel-headers version mismatch: expected 6.12.77"
#endif
#if !defined(LINUX_VERSION_MAJOR) || !defined(LINUX_VERSION_PATCHLEVEL) || !defined(LINUX_VERSION_SUBLEVEL)
#error "kernel-headers: LINUX_VERSION_MAJOR/PATCHLEVEL/SUBLEVEL missing"
#endif

    /* 运行期断言：宏与结构体在交叉编译下真实可用 */
    struct input_id id = { .bustype = BUS_USB, .vendor = 0x1234, .product = 0x5678, .version = 0x0001 };
    __u16 code = KEY_A;
    __u32 eth = ETH_P_IP;
    int ioctl_req_ok = _IOC(_IOC_READ, 'E', 0x01, sizeof(struct input_id)) != 0 ? 1 : 0;
    /* arm64 syscall 表：__NR_io_setup=0（首项），__NR_openat=56 */
    int nr_ok = (__NR_io_setup == 0 && __NR_openat == 56) ? 1 : 0;

    int ok = (LINUX_VERSION_MAJOR == 6)
          && (LINUX_VERSION_PATCHLEVEL == 12)
          && (LINUX_VERSION_SUBLEVEL == 77)
          && (id.bustype == BUS_USB)
          && (code == KEY_A)
          && (eth == ETH_P_IP)
          && ioctl_req_ok
          && nr_ok;
    return ok ? 0 : 1;
}
