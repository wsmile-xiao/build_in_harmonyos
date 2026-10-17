/* liblksctp 消费者冒烟断言
 *
 * 断言 libsctp 的**真实功能行为**（非“文件存在”）：直接链接 libsctp 并调用
 * 公开 API `sctp_getaddrlen()`（netinet/sctp.h:865）。该函数是库内纯用户态
 * 逻辑（addrs.c:135，按地址族返回 sizeof），不需要内核 SCTP、不需要 socket，
 * 因此可在任何 worker 上确定性通过；它同时验证了三件事：
 *   1. 公开头 <netinet/sctp.h> 可被消费者包含；
 *   2. 消费者能 -lsctp 链接成功（Versions.map 把符号导出到 VERS_1）；
 *   3. 运行期 .so 能被加载器加载（即 .codesign 签名有效，E077）。
 * 若库未签名，进程在 main() 之前就被内核拒绝，本断言直接非零退出。
 */
#include <netinet/sctp.h>

#include <netinet/in.h>
#include <stdio.h>
#include <sys/socket.h>

int main(void) {
    int len_v4 = sctp_getaddrlen(AF_INET);
    int len_v6 = sctp_getaddrlen(AF_INET6);
    int len_unknown = sctp_getaddrlen(AF_UNSPEC);

    if (len_v4 != (int)sizeof(struct sockaddr_in)) {
        fprintf(stderr, "sctp_getaddrlen(AF_INET)=%d, expected %d\n",
                len_v4, (int)sizeof(struct sockaddr_in));
        return 1;
    }
    if (len_v6 != (int)sizeof(struct sockaddr_in6)) {
        fprintf(stderr, "sctp_getaddrlen(AF_INET6)=%d, expected %d\n",
                len_v6, (int)sizeof(struct sockaddr_in6));
        return 1;
    }
    if (len_unknown != 0) {
        fprintf(stderr, "sctp_getaddrlen(AF_UNSPEC)=%d, expected 0\n", len_unknown);
        return 1;
    }

    printf("liblksctp: sctp_getaddrlen ok (AF_INET=%d, AF_INET6=%d, default=%d)\n",
           len_v4, len_v6, len_unknown);
    return 0;
}
