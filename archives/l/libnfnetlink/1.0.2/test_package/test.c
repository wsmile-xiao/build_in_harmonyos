#include <stdio.h>
#include <string.h>

/* HarmonyOS fix: avoid sockaddr_storage redefinition in linux/socket.h */
#ifndef __kernel_sa_family_t
typedef unsigned short __kernel_sa_family_t;
#endif
#ifndef _K_SS_MAXSIZE
#define _K_SS_MAXSIZE 128
#endif
#ifndef _UAPI_LINUX_SOCKET_H
#define _UAPI_LINUX_SOCKET_H
#endif

#include <libnfnetlink/libnfnetlink.h>

int main(void) {
    char buf[256];
    struct nlmsghdr *nlh = (struct nlmsghdr *)buf;

    memset(buf, 0, sizeof(buf));
    nlh->nlmsg_len = NLMSG_ALIGN(sizeof(struct nlmsghdr));

    int ret = nfnl_addattr32(nlh, sizeof(buf), 1, 0x12345678);

    if (ret < 0) {
        printf("test libnfnetlink: nfnl_addattr32 failed\n");
        return 1;
    }

    printf("test libnfnetlink 1.0.2: nfnl_addattr32 OK\n");
    return 0;
}
