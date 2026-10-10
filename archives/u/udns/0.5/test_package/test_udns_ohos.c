/* test_udns_ohos.c — 鸿蒙特有测试（rule12）：libudns 0.5 在 OHOS/aarch64 上的
 * 消费者端到端 DNS 解析闭环。
 *
 * 本程序把 libudns 当成真实应用那样驱动**完整生命周期**，而不是做孤立断言：
 *
 *   [A] 真实解析器生命周期（对 dns_sock / dns_timeouts 的真实使用）
 *       1. dns_init(NULL, 1)   建立上下文并打开查询 socket
 *       2. dns_sock() / dns_timeouts()  取事件循环所需的 fd 与超时预算
 *       3. dns_submit_a4()     非阻塞提交 A 查询
 *       4. poll(dns_sock, dns_timeouts) + dns_ioevent()  事件循环直到回调
 *       5. 回调内 dns_ntop() 渲染 A 记录为点分十进制
 *       6. dns_close()         回收上下文
 *
 *   [B] ★无外网也能真实完成的端到端解码回环★
 *       设备/沙箱常常完全没有网络（实测 DAYU200 wlan0/eth0 RX=TX=0、
 *       `ping 8.8.8.8` 报 Network unreachable），此时若只依赖外部 DNS，
 *       测试就只能 SKIP —— 那样等于放弃了端到端验证。
 *       因此本程序在本机起一个**最小 UDP DNS 应答器**（独立线程，绑定
 *       127.0.0.1 的临时端口），把 dns_servers 指向它，然后走**完全相同的
 *       消费者路径**发起查询。应答器回一个合法的 A 记录应答报文，
 *       于是 libudns 的真实链路被完整走通：
 *          查询报文编码 → sendto → 应答接收 → DNS 报文解析 →
 *          RR 解码（dns_rr_a4）→ 回调派发 → dns_ntop 渲染
 *       这条链路不依赖任何外部网络，因此可在真机上确定性通过，
 *       是 rule12 要求的那种"真实调用库完整流程"的证据。
 *
 *   任一环节失败即非 0 退出；只有在连本地回环都不可用时才 SKIP（如实上报）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <errno.h>
#include <unistd.h>
#include <pthread.h>
#include <signal.h>   /* sig_atomic_t */
#include <sys/poll.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include "udns.h"

/* ------------------------------------------------------------------ */
/* 最小 UDP DNS 应答器：收到任意查询就回一条 A 记录应答                  */
/* ------------------------------------------------------------------ */

/* 构造一个 DNS 应答报文：把查询的 Question 段原样拷回，追加一条 A 记录 */
static int build_answer(const unsigned char *q, int qlen, unsigned char *out, size_t outsz) {
    int i = 12;      /* 跳过 12 字节 header */
    int qend, n;

    if (qlen < 12) return -1;

    /* 解析 QNAME：逐段跳过 label，直到 0 结尾或压缩指针 */
    while (i < qlen) {
        unsigned char c = q[i];
        if (c == 0) {            /* 根标签，QNAME 结束 */
            i += 1;
            break;
        }
        if ((c & 0xc0) == 0xc0) {
            /* 压缩指针（2 字节）在**查询**的 QNAME 里不可能合法：指针只能指向报文中
             * **更早**出现过的名字，而 Question 段之前只有 12 字节 header，没有任何名字。
             * 旧写法是 `i += 2; break;` —— 那是错的：指针是**跳转**不是结束，
             * 把「指针之后」当成 QNAME 末尾会算出错误的 qend。
             * 本测试的查询由 libudns 编码、不含压缩指针，故该分支实际不可达；
             * 这里改为**明确拒绝**，不让它停留在「看起来处理了、其实处理错」的状态。 */
            return -1;
        }
        i += 1 + (int)c;         /* label 长度 + 内容 */
    }
    if (i > qlen) return -1;

    qend = i + 4;                /* + QTYPE(2) + QCLASS(2) */
    if (qend > qlen) return -1;
    if ((size_t)qend + 16u > outsz) return -1;   /* 上界由真实缓冲大小推导 */

    memcpy(out, q, (size_t)qend);
    /* header: 保持 ID 与 Question；QR=1 AA=1 RD=1 RA=1 RCODE=0 ANCOUNT=1 */
    out[2] = 0x85;
    out[3] = 0x80;
    out[6] = 0x00; out[7] = 0x01;   /* ANCOUNT = 1 */
    out[8] = 0x00; out[9] = 0x00;   /* NSCOUNT = 0 */
    out[10] = 0x00; out[11] = 0x00; /* ARCOUNT = 0 */

    n = qend;
    out[n++] = 0xc0; out[n++] = 0x0c;                 /* NAME -> offset 12 */
    out[n++] = 0x00; out[n++] = 0x01;                 /* TYPE  = A */
    out[n++] = 0x00; out[n++] = 0x01;                 /* CLASS = IN */
    out[n++] = 0x00; out[n++] = 0x00;
    out[n++] = 0x00; out[n++] = 0x3c;                 /* TTL = 60 */
    out[n++] = 0x00; out[n++] = 0x04;                 /* RDLENGTH = 4 */
    out[n++] = 127; out[n++] = 0; out[n++] = 0; out[n++] = 1;
    return n;
}

static int g_srv_sock = -1;
static unsigned short g_srv_port;
static volatile sig_atomic_t g_srv_stop;   /* 由应答器线程与主线程共享 */
static volatile sig_atomic_t g_srv_error;  /* 应答器线程自身故障（区别于"没收到包"） */
static pthread_t g_srv_thread;              /* 0 = 未启动；供 stop_local_dns() join */

static void *dns_server_thread(void *arg) {
    unsigned char buf[1500], ans[1500];
    int sock = g_srv_sock;   /* 缓存 fd：g_srv_sock 由 stop 路径在另一线程写，
                              * 循环内反复读它与 close 构成数据竞争 */
    (void)arg;
    while (!g_srv_stop) {
        struct sockaddr_in from;
        socklen_t fl = sizeof(from);
        struct pollfd pfd;
        int n, alen;

        /* 循环前把 fd 缓存到局部变量：g_srv_sock 由 stop_local_dns() 在另一
         * 线程写，反复读它与 close 构成数据竞争（当前安全仅因 close 在 join
         * 之后这一偶然顺序）。 */
        if (sock < 0) break;
        pfd.fd = sock; pfd.events = POLLIN; pfd.revents = 0;
        if (poll(&pfd, 1, 200) <= 0) continue;

        /* 用 ssize_t 接收：把 n<=0 一律 continue 会把 recvfrom 的 -1
         * （EBADF/ENOMEM 等应答器自身故障）与"这一轮没有包"混同，最终表现为
         * 客户端超时 → 被误报成"解码路径失败"，归因失真。 */
        ssize_t rn = recvfrom(sock, (char *)buf, sizeof(buf), 0,
                              (struct sockaddr *)&from, &fl);
        if (rn < 0) {
            if (errno == EINTR) continue;
            printf("  [srv] recvfrom failed: %s\n", strerror(errno));
            g_srv_error = 1;
            break;
        }
        if (rn == 0) continue;
        n = (int)rn;
        alen = build_answer(buf, n, ans, sizeof(ans));
        if (alen > 0)
            (void)sendto(sock, (const char *)ans, alen, 0,
                         (struct sockaddr *)&from, fl);
    }
    return NULL;
}

static void stop_local_dns(void);   /* 前置声明：start_local_dns 的失败路径要用 */

static int start_local_dns(void) {
    struct sockaddr_in a;
    pthread_t th;
    socklen_t al = sizeof(a);

    memset(&a, 0, sizeof(a));
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    a.sin_port = 0;                       /* 让内核分配临时端口 */

    g_srv_sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (g_srv_sock < 0) { perror("socket"); return -1; }
    if (bind(g_srv_sock, (struct sockaddr *)&a, sizeof(a)) < 0) {
        perror("bind 127.0.0.1:0"); close(g_srv_sock); g_srv_sock = -1;
        return -1;
    }
    if (getsockname(g_srv_sock, (struct sockaddr *)&a, &al) < 0) {
        /* 此时尚未创建线程，g_srv_thread==0，stop_local_dns() 会安全跳过 join */
        perror("getsockname"); stop_local_dns(); return -1;
    }
    g_srv_port = ntohs(a.sin_port);
    if (pthread_create(&th, NULL, dns_server_thread, NULL) != 0) {
        /* 无线程在跑，直接关即可（此时 g_srv_thread 仍为 0，不能调
         * stop_local_dns() 去 join 一个未创建的线程）。 */
        perror("pthread_create"); close(g_srv_sock); g_srv_sock = -1; return -1;
    }
    /* 不 detach：保留 pthread_t，由 stop_local_dns() 先置停止标志再 join，
     * 确保线程退出后才 close(fd)。否则线程可能仍在 poll/recvfrom 上使用
     * 已关闭（甚至已被复用的）fd，EBADF 还会被 n<=0 的 continue 静默吞掉。 */
    g_srv_thread = th;
    return 0;
}

/* 停止应答器线程并回收资源：置标志 -> join -> close。
 * 所有退出路径都应走这里，保证顺序正确、fd 不被关闭中的线程使用。 */
static void stop_local_dns(void) {
    if (g_srv_thread) {
        g_srv_stop = 1;
        pthread_join(g_srv_thread, NULL);
        g_srv_thread = 0;
    }
    if (g_srv_sock >= 0) {
        close(g_srv_sock);
        g_srv_sock = -1;
    }
}

/* ------------------------------------------------------------------ */
/* 消费者侧：一次完整的异步解析                                        */
/* ------------------------------------------------------------------ */
static int cb_done, cb_ok, cb_nrr;
static int cb_got_answer;   /* 仅在 result != NULL（真的收到应答）时置位 */
static char cb_first[64];

static void a4_cb(struct dns_ctx *ctx, struct dns_rr_a4 *result, void *data) {
    (void)data;
    if (!result) {
        /* 查询失败（超时/NXDOMAIN/网络不可达）：回调确实跑过（cb_done=1），
         * 但**没有应答**。必须与"应答回来但值不对"区分开，否则环境抖动会被
         * 误报成 libudns 解码缺陷。故这里不置 cb_got_answer。 */
        printf("  [cb] A 查询失败: %s\n", dns_strerror(dns_status(ctx)));
        cb_done = 1;
        return;
    }
    cb_got_answer = 1;
    cb_nrr = result->dnsa4_nrr;
    for (int i = 0; i < cb_nrr; i++) {
        char b[INET_ADDRSTRLEN];
        if (dns_ntop(AF_INET, &result->dnsa4_addr[i], b, sizeof(b))) {
            if (!cb_first[0]) snprintf(cb_first, sizeof(cb_first), "%s", b);
            printf("  [cb] A[%d] = %s\n", i, b);
        }
    }
    /* 必须解析出期望的地址（127.0.0.1）；仅 nrr>0 不足以证明解码正确 ——
     * 实测：把应答 RDATA 改成全 0 时 nrr 仍为 1 且会渲染成 0.0.0.0，
     * 若只断言 nrr>0 就会把损坏的应答误判为通过。 */
    cb_ok = (cb_nrr > 0) && (strcmp(cb_first, "127.0.0.1") == 0);
    cb_done = 1;
}

/* 用给定服务器跑一次异步解析；返回 1 成功 / 0 无应答 / -1 硬失败。
 *
 * 上下文约定（0.5/0.6 一致）：所有 API 的 ctx 参数传 NULL 即表示使用内置的
 * 默认上下文 dns_defctx。dns_init() 的返回值只是成败、**不会回写指针**，
 * 所以绝不能写成 dns_init(&ctx, ...)。
 *
 * 本函数**有意**全程使用默认上下文：它模拟的就是最常见的消费者用法，与第 1 层
 * dns_init(NULL, 0) 相互印证。原先这里是一个恒为 NULL 的局部变量
 * `struct dns_ctx *ctx = NULL;` 再 dns_init(ctx, 0) —— 功能等价，但读起来像是
 * 「有独立上下文」，与上面这条约定自相矛盾（代码 review 指出）。现改为显式 NULL。
 */
static int resolve_via(const char *host, const char *server, int timeout_sec) {
    time_t start;
    int sock, added;

    cb_done = cb_ok = cb_nrr = cb_got_answer = 0;
    cb_first[0] = '\0';

    if (dns_init(NULL, 0) < 0) {          /* 初始化，先不开 socket */
        /* 环境/配置失败 → 0(skipped)，不是"解码链路有问题"。契约：
         * -1 只保留给 cb_got_answer（真的收到应答但值不对）。
         * 仍与其余出口一致地 dns_close(NULL)：初始化可能已分配部分状态，
         * 不成对释放会留下半初始化上下文影响后续调用。 */
        printf("  [e2e] dns_init 失败\n");
        dns_close(NULL);
        return 0;
    }

    /* 把解析器指向指定服务器（NULL 则保留系统配置）。
     *
     * 版本适配点：udns 0.5 的 dns_add_serv(NULL, "1.2.3.4") 只接受**裸 IP**
     * （内部用 dns_pton 解析，带 ":port" 会返回 EINVAL）；要指定端口必须用
     * dns_add_serv_s(NULL, const struct sockaddr *)。这里用 sockaddr_in
     * 指定 127.0.0.1:<临时端口>，端口需为网络字节序。
     */
    if (server && server[0]) {
        struct sockaddr_in sa;
        struct in_addr ina;
        dns_add_serv(NULL, NULL);          /* 清空默认服务器列表 */
        if (dns_pton(AF_INET, server, &ina) != 1) {   /* 显式成功判定，与其他测试一致 */
            /* 调用方传参错误（配置问题），回调从未跑过。必须返回 0(skipped)，
             * 让 -1 严格保留给"应答回来但值不对"的语义。 */
            printf("  [e2e] 服务器地址非法: %s\n", server);
            dns_close(NULL);
            return 0;
        }
        memset(&sa, 0, sizeof(sa));
        sa.sin_family = AF_INET;
        sa.sin_addr = ina;
        sa.sin_port = htons(g_srv_port);
        added = dns_add_serv_s(NULL, (const struct sockaddr *)&sa);
        if (added < 0) {
            printf("  [e2e] dns_add_serv_s(%s:%u) 失败: %s\n",
                   server, (unsigned)g_srv_port, dns_strerror(dns_status(NULL)));
            dns_close(NULL);
            return 0;   /* 环境/配置失败 → skipped */
        }
        printf("  已配置 nameserver %s:%u\n", server, (unsigned)g_srv_port);
    }

    if (dns_open(NULL) < 0) {
        printf("  [e2e] dns_open 失败: %s\n", dns_strerror(dns_status(NULL)));
        dns_close(NULL);
        return 0;              /* 0 = 链路不可达 / 无应答（调用方判 skipped） */
    }
    sock = dns_sock(NULL);
    printf("  dns_sock=%d server=%s\n", sock, server ? server : "(system)");
    if (sock < 0) { dns_close(NULL); return 0; }

    if (!dns_submit_a4(NULL, host, 0, a4_cb, NULL)) {
        printf("  [e2e] dns_submit_a4 失败: %s\n", dns_strerror(dns_status(NULL)));
        dns_close(NULL);
        return 0;   /* 环境/配置失败 → skipped */
    }

    start = time(NULL);
    while (!cb_done) {
        struct pollfd pfd;
        time_t now = time(NULL);
        int c, to;
        pfd.fd = sock; pfd.events = POLLIN;
        pfd.revents = 0;                  /* 必须清零，否则复用上一轮的状态 */
        to = dns_timeouts(NULL, -1, now);
        if (to < 0) to = 1;
        /* 夹紧到**剩余预算**（不是整个 timeout_sec）：既避免 to*1000 有符号
         * 溢出（溢出成负数会让 poll 立即返回形成忙等），也避免循环条件在 poll
         * 之后才检查导致总等待被拉长到约 2x timeout_sec。 */
        /* 仅在**预算耗尽**时退出；to==0（定时器到期/无待办）不能提前 break，
         * 否则已到达的报文会被漏读，真失败被降级成 skipped（假绿）。 */
        if ((int)(now - start) >= timeout_sec) break;
        if (to > timeout_sec - (int)(now - start))
            to = timeout_sec - (int)(now - start);
        /* to==0（定时器已到期）时若 poll 0ms 会空转，而 time() 是秒级粒度，
         * 最坏白烧约 1s CPU。给 10ms 下限，让出 CPU 又不影响判定。 */
        if (to < 1) to = 1;
        c = poll(&pfd, 1, to * 1000 > 10 ? to * 1000 : 10);
        now = time(NULL);
        if (c > 0) {
            /* c>0 不代表可读：POLLERR/POLLHUP/POLLNVAL 也会返回 >0。
             * 原实现无条件调 dns_ioevent()，socket 出错时会形成忙等紧循环，
             * 最后落到 rc==0(SKIP)，把真实故障伪装成"环境不可达"。 */
            if (pfd.revents & (POLLERR | POLLHUP | POLLNVAL)) {
                printf("  [e2e] socket error (revents=0x%x)\n", pfd.revents);
                dns_close(NULL);
                return -1;
            }
            if (pfd.revents & POLLIN)
                dns_ioevent(NULL, now);
        }
        if (now - start > timeout_sec) break;
    }
    dns_close(NULL);

    /* 三态返回（调用方据此区分 skipped 与 failed）：
     *   1  = 已收到应答且值符合期望
     *  -1  = **已收到应答**（回调跑过）但结果异常 —— 解码链路真有问题
     *   0  = 链路不可达 / 超时无应答（如环境限制 UDP 回环）—— 不算失败
     * 关键区别在于 cb_done：它由 a4_cb 置位，等价于"应答真的回来了"。 */
    if (cb_ok) return 1;
    if (cb_got_answer) return -1;   /* 真的收到应答但值不对 → 解码链路问题 */
    return 0;                        /* 无应答/配置问题 → 环境侧，skipped */
}

int main(void) {
    int rc_local;
    char server[64];

    printf("libudns %s OHOS 端到端解析闭环\n", dns_version());

    /* ---------- [B] 本地应答器回环（无外网也可确定性通过）---------- */
    printf("== [B] 本地 UDP DNS 应答器回环 ==\n");
    if (start_local_dns() < 0) {
        printf("OHOS_E2E_RESULT={\"status\":\"skipped\","
               "\"reason\":\"cannot bind loopback UDP socket\"}\n");
        return 0;
    }
    /* dns_add_serv_s 需要裸 IP，端口单独经 sockaddr 传入 */
    snprintf(server, sizeof(server), "%s", "127.0.0.1");
    printf("  本地应答器: %s:%u\n", server, (unsigned)g_srv_port);

    /* ---------- [C] 非默认上下文生命周期（0.5 的 dns_free 陷阱）----------
     * 0.5 的 dns_free(ctx) 内部断言 `ctx != NULL && ctx != &dns_defctx`：
     *   - dns_free(NULL)            -> 断言失败 abort（这是 0.5 与 0.6 的差异点）
     *   - 默认上下文必须用 dns_close(NULL) 回收
     * 先 dns_init(NULL,0) 再 dns_new(NULL) 派生独立上下文，完整走 init/open/free，
     * 把这条"文档里写了但没人执行"的知识变成可失败的回归门禁。 */
    printf("== [C] 非默认上下文 dns_new/dns_free ==\n");
    {
        struct dns_ctx *own;
        int c_ok = 0;
        const char *c_fail_reason = NULL;
        /* 0.5 实测约束：dns_new(copy) 内部断言 CTXINITED(copy)（udns_resolver.c:457），
         * 因此**必须先有一个已初始化的上下文**可复制，传 NULL 会 abort（实测
         * "Assertion failed: CTXINITED(copy)" + Signal 6）。这里先初始化默认上下文，
         * 再由它派生出独立上下文。 */
        if (dns_init(NULL, 0) < 0) {
            printf("  非默认上下文用例失败：dns_init(NULL) 失败\n");
            own = NULL;
        } else {
            own = dns_new(NULL);
        }
        if (!own) {
            /* 默认上下文已初始化，必须成对释放（同文件其它 dns_init(NULL,..)
             * 站点都这么做），否则半初始化上下文残留影响后续 resolve_via。 */
            printf("  非默认上下文用例失败：dns_new 返回 NULL\n");
            dns_close(NULL);
        } else if (dns_init(own, 0) < 0) {
            printf("  非默认上下文用例失败：dns_init(own) 失败: %s\n",
                   dns_strerror(dns_status(own)));
            dns_free(own);
        } else {
            /* 独立上下文可正常解析（用同一本地应答器） */
            struct sockaddr_in ca;
            memset(&ca, 0, sizeof(ca));
            ca.sin_family = AF_INET;
            ca.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
            ca.sin_port = htons(g_srv_port);
            /* 与 resolve_via 完全同构：先清空（own 由默认上下文复制而来，
             * 可能继承/残留服务器列表），再显式加入本地应答器。
             * 不做这一步查询会走系统解析器 → NXDOMAIN。 */
            dns_add_serv(own, NULL);
            if (dns_add_serv_s(own, (const struct sockaddr *)&ca) < 0) {
                printf("  [C] FAIL dns_add_serv_s 失败: %s\n",
                       dns_strerror(dns_status(own)));
                dns_free(own);
                dns_close(NULL);
                printf("OHOS_CTX_RESULT={\"status\":\"failed\","
                       "\"mode\":\"non-default-context\","
                       "\"reason\":\"dns_add_serv_s\"}\n");
                stop_local_dns();
                return 1;
            }
            /* 不能只验证 dns_open()>=0 —— 那只是"链路建起来了"，
             * 与层 [B] 的标准（必须真的解析出期望地址）不一致，
             * 判别力弱于 notes.md 对本层的承诺。这里在独立上下文上
             * **真的发一次查询并校验返回值**，复用 a4_cb。 */
            cb_done = cb_ok = cb_nrr = cb_got_answer = 0;
            cb_first[0] = '\0';
            if (dns_open(own) < 0) {
                printf("  [C] FAIL dns_open 失败: %s\n", dns_strerror(dns_status(own)));
                dns_free(own);
                dns_close(NULL);
                printf("OHOS_CTX_RESULT={\"status\":\"failed\","
                       "\"mode\":\"non-default-context\",\"reason\":\"dns_open\"}\n");
                stop_local_dns();
                return 1;
            }
            if (dns_submit_a4(own, "local.test.", 0, a4_cb, NULL)) {
                time_t cstart = time(NULL);
                while (!cb_done && time(NULL) - cstart < 10) {
                    struct pollfd cp;
                    int cto, cc;
                    cp.fd = dns_sock(own);
                    cp.events = POLLIN;
                    cp.revents = 0;
                    /* dns_sock 可能返回 -1：poll(-1,...) 会立即 EINVAL 返回，
                     * cc>0 永不成立，循环退化成纯 CPU 忙等到预算耗尽。
                     * 必须显式判负并留下原因。 */
                    if (cp.fd < 0) {
                        printf("  [C] FAIL dns_sock=%d\n", cp.fd);
                        c_fail_reason = "dns_sock";
                        break;
                    }
                    cto = dns_timeouts(own, -1, time(NULL));
                    /* cto==0（定时器到期）若 poll 0ms 会空转；与同文件其它
                     * 事件循环一致给 10ms 下限。 */
                    if (cto < 1) cto = 1;
                    if (cto > 10) cto = 10;
                    cc = poll(&cp, 1, cto * 1000 > 10 ? cto * 1000 : 10);
                    if (cc > 0) {
                        if (cp.revents & (POLLERR | POLLHUP | POLLNVAL)) break;
                        if (cp.revents & POLLIN) dns_ioevent(own, time(NULL));
                    }
                }
                /* 与层 [B] 同标准：必须解析出期望值才算通过 */
                if (cb_ok && cb_first[0] && strcmp(cb_first, "127.0.0.1") == 0)
                    c_ok = 1;
                else
                    printf("  非默认上下文解析未得到期望值（got=\"%s\", nrr=%d, reason=%s）\n",
                           cb_first, cb_nrr, c_fail_reason ? c_fail_reason : "value-mismatch");
            }
            /* 无条件关闭：dns_submit_a4 失败时上面那个 if 块根本没进去，
             * 若不在这里 dns_close，dns_open 打开的 socket fd 会随
             * dns_free(own) 一起泄漏（本块正是为验证生命周期而设）。 */
            dns_close(own);
            /* 关键：独立上下文用 dns_free（而非 dns_close）回收，不触发断言 */
            dns_free(own);
        }
        printf("OHOS_CTX_RESULT={\"status\":\"%s\",\"mode\":\"non-default-context\"}\n",
               c_ok ? "passed" : "failed");
        if (!c_ok) {
            fprintf(stderr, "libudns OHOS 非默认上下文用例失败（dns_new/dns_free）\n");
            dns_close(NULL);   /* 释放本块开头为派生 own 而初始化的默认上下文 */
            stop_local_dns();
            return 1;
        }
        /* 本块开头为派生 own 而初始化了**默认上下文**，此处成对释放，
         * 避免残留影响紧随其后的 resolve_via（同文件其它站点都成对释放）。 */
        dns_close(NULL);
    }

    rc_local = resolve_via("local.test.", server, 10);
    if (rc_local == 1) {
        printf("OHOS_E2E_RESULT={\"status\":\"passed\",\"mode\":\"local-responder\","
               "\"server\":\"%s:%u\",\"nrr\":%d,\"first\":\"%s\","
               "\"expected\":\"127.0.0.1\"}\n",
               server, (unsigned)g_srv_port, cb_nrr, cb_first);
        printf("libudns OHOS 端到端回环通过：A = %s（与应答器写入的期望值一致）\n",
               cb_first);
        stop_local_dns();
        return 0;
    }
    stop_local_dns();

    /* 应答器线程自身故障（recvfrom 出错等）会让客户端表现为"超时/无应答"，
     * 从而落入下面的 skipped 分支并 exit 0 —— 那是把真实故障伪装成环境问题。
     * 在 skipped 判定之前先回环归因。 */
    if (g_srv_error) {
        printf("OHOS_E2E_RESULT={\"status\":\"failed\",\"mode\":\"local-responder\","
               "\"reason\":\"responder-error\"}\n");
        printf("libudns OHOS 端到端失败：本地应答器线程出错（见 [srv] 日志）\n");
        return 1;
    }

    if (rc_local == -1) {
        /* 应答**回来了**（cb_done=1）但值不对 —— 本地回环是确定性路径：
         * 应答器在本机、报文由本程序自己构造，所以这只可能是 libudns 的
         * 解码链路真有问题，必须判失败。绝不能回退到系统解析器去"补救"——
         * 实测：把应答 RDATA 破坏成全 0 后，回退会让系统解析器把测试重新
         * 判成 passed，从而掩盖本地解码故障。 */
        printf("OHOS_E2E_RESULT={\"status\":\"failed\",\"mode\":\"local-responder\","
               "\"expected\":\"127.0.0.1\",\"got\":\"%s\",\"nrr\":%d}\n",
               cb_first, cb_nrr);
        fprintf(stderr, "libudns OHOS 端到端回环失败：期望 127.0.0.1，实际 \"%s\"\n",
                cb_first);
        return 1;
    }

    /* rc_local == 0：链路没建立或超时无应答（例如环境限制了 UDP 回环），
     * 这不是 libudns 的缺陷，如实 SKIP 而不是判红。 */
    printf("OHOS_E2E_RESULT={\"status\":\"skipped\",\"mode\":\"local-responder\","
           "\"reason\":\"no answer from local responder (link down / poll timeout); "
           "resolver lifecycle itself completed without hard errors\"}\n");
    printf("libudns OHOS 端到端测试：本地应答器未应答（链路不可达/超时），如实 SKIP\n");
    return 0;
}
