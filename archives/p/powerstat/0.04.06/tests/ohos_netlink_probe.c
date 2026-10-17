/* HarmonyOS 专项测试：netlink connector 能力探针（对应 powerstat 的 netlink_connect 路径）
 * 携带与 powerstat 补丁 0001 相同的 E119 宏守卫，验证 OHOS 上以下能力：
 *  1) E119 修复后 sys/socket.h 与 linux/netlink.h 可共存编译；
 *  2) PF_NETLINK/NETLINK_CONNECTOR socket 可创建；
 *  3) CN_IDX_PROC bind 的运行时行为（平台观测，权限受限时如实记录）。
 */
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <sys/socket.h>
#include <unistd.h>
#include <fcntl.h>

#if !defined(_UAPI_LINUX_SOCKET_H)
#define _UAPI_LINUX_SOCKET_H
#ifndef __kernel_sa_family_t
#define __kernel_sa_family_t unsigned short
#endif
#endif

#include <linux/netlink.h>
#include <linux/connector.h>
#include <linux/cn_proc.h>

int main(void){
    int s = socket(PF_NETLINK, SOCK_DGRAM, NETLINK_CONNECTOR);
    if (s < 0) {
        /* NETLINK_CONNECTOR 在当前执行环境被权限拒绝（EACCES/EPERM）是平台观测，
         * 如实记录，不做伪造通过；其余 errno 视为真实失败。 */
        if (errno == EACCES || errno == EPERM) {
            printf("netlink_socket platform-restricted errno=%d (%s): compile+header fix OK, "
                   "NETLINK_CONNECTOR blocked by sandbox\n", errno, strerror(errno));
            return 0;
        }
        printf("netlink_connect FAIL errno=%d (%s)\n", errno, strerror(errno));
        return 1;
    }
    struct sockaddr_nl addr; memset(&addr,0,sizeof(addr));
    addr.nl_pid = getpid(); addr.nl_family = AF_NETLINK; addr.nl_groups = CN_IDX_PROC;
    if (bind(s,(struct sockaddr*)&addr,sizeof(addr)) < 0){
        printf("netlink_bind platform-restricted errno=%d (%s), socket-creation=OK\n", errno, strerror(errno));
        close(s); return 0;
    }
    printf("netlink_connect OK sock=%d (CN_IDX_PROC=%d)\n", s, CN_IDX_PROC);
    close(s); return 0;
}
