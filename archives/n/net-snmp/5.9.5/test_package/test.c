/* net-snmp 5.9.5 真实功能断言。
 *
 * 消费方 ezsnmp 走两条路，都得验：
 *   ① `net-snmp-config --version` / `--libs` —— 它在 setup.py 里靠这个脚本拿编译参数。
 *      该脚本若没装出来或吐不出东西，ezsnmp 连构建都起不来。（在 test() 里跑，见 conanfile）
 *   ② libnetsnmp 的 C API —— 本文件负责。
 *
 * 断言分两档：
 *   [纯内存] 不需要外部环境的算法验证（任何平台都能跑，CI 交叉编译只验编译）：
 *     · OID 文本 ↔ 二进制的往返（read_objid / snprint_objid）——SNMP 的核心数据模型
 *     · 构造一个真实 GET PDU 并挂上 varbind，断言结构被正确填充
 *     · 会话结构初始化后的默认值（版本/超时/重试）
 *   [鸿蒙 PC 特有 · 端到端] 见 test_harmonyos_udp_loopback_e2e()：
 *     · 进程真建 UDP socket、库真把 BER 报文写进内核网络栈、超时路径真能走通。
 *       全程不碰文件系统（设备上 /tmp 与 /etc 均只读，上游 T004/T020 正是死在这）。
 *
 * 不做「dlopen + dlsym 看指针非空」那种探针：解析到符号不等于函数能用，
 * 本仓已有 5 例缺陷只有真实计算才暴露。
 */
#include <net-snmp/net-snmp-config.h>
#include <net-snmp/net-snmp-includes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

static int test_oid_roundtrip(void)
{
    /* sysDescr.0 —— SNMP 里最标准的一个 OID，数值形式 1.3.6.1.2.1.1.1.0 */
    oid buf[MAX_OID_LEN];
    size_t len = MAX_OID_LEN;

    if (!read_objid("1.3.6.1.2.1.1.1.0", buf, &len)) {
        printf("FAIL read_objid 解析数值 OID 失败\n");
        return 1;
    }
    if (len != 9) { printf("FAIL OID 长度 %zu != 9\n", len); return 1; }

    static const oid expect[9] = {1, 3, 6, 1, 2, 1, 1, 1, 0};
    for (size_t i = 0; i < 9; i++)
        if (buf[i] != expect[i]) {
            printf("FAIL OID[%zu]=%lu 期望 %lu\n", i,
                   (unsigned long)buf[i], (unsigned long)expect[i]);
            return 1;
        }

    /* 反向：二进制 → 文本。用 snprint_objid 而非 print（后者写 stdout 不可断言）。 */
    char out[256];
    int n = snprint_objid(out, sizeof(out), buf, len);
    if (n <= 0) { printf("FAIL snprint_objid 返回 %d\n", n); return 1; }
    /* 不比对完整字符串：是否带 MIB 名（SNMPv2-MIB::sysDescr.0）取决于 MIB 文件是否装好，
     * 两种都算正常。只断言**非空且含结尾的 .0**，确保确实是同一个 OID。 */
    if (strstr(out, ".0") == NULL) {
        printf("FAIL 反解文本 '%s' 不像 sysDescr.0\n", out);
        return 1;
    }
    printf("OID 往返 OK: 1.3.6.1.2.1.1.1.0 -> 9 个子标识 -> \"%s\"\n", out);
    return 0;
}

static int test_pdu_build(void)
{
    /* 造一个真实的 GET PDU 并挂 varbind —— 这是 ezsnmp 每次 get 都要走的路径。 */
    netsnmp_pdu *pdu = snmp_pdu_create(SNMP_MSG_GET);
    if (pdu == NULL) { printf("FAIL snmp_pdu_create 返回 NULL\n"); return 1; }
    if (pdu->command != SNMP_MSG_GET) {
        /* command 在 net-snmp/types.h 里是 int（不是 long），格式符按实际类型给 */
        printf("FAIL pdu->command=%d 期望 SNMP_MSG_GET\n", pdu->command);
        snmp_free_pdu(pdu); return 1;
    }

    oid name[MAX_OID_LEN];
    size_t nlen = MAX_OID_LEN;
    if (!read_objid("1.3.6.1.2.1.1.3.0", name, &nlen)) {   /* sysUpTime.0 */
        printf("FAIL read_objid sysUpTime\n"); snmp_free_pdu(pdu); return 1;
    }
    snmp_add_null_var(pdu, name, nlen);

    if (pdu->variables == NULL) {
        printf("FAIL varbind 没挂上\n"); snmp_free_pdu(pdu); return 1;
    }
    if (pdu->variables->name_length != nlen) {
        printf("FAIL varbind name_length=%zu 期望 %zu\n",
               pdu->variables->name_length, nlen);
        snmp_free_pdu(pdu); return 1;
    }
    if (pdu->variables->type != ASN_NULL) {
        printf("FAIL varbind type=%d 期望 ASN_NULL(%d)\n",
               (int)pdu->variables->type, (int)ASN_NULL);
        snmp_free_pdu(pdu); return 1;
    }
    if (pdu->variables->next_variable != NULL) {
        printf("FAIL varbind 链表应只有 1 个\n"); snmp_free_pdu(pdu); return 1;
    }
    snmp_free_pdu(pdu);
    printf("GET PDU 构造 OK: 1 个 ASN_NULL varbind，OID 长度 %zu\n", nlen);
    return 0;
}

static int test_session_init(void)
{
    netsnmp_session sess;
    memset(&sess, 0xAB, sizeof(sess));    /* 先填脏数据，确保下面的值真是 init 写的 */
    snmp_sess_init(&sess);

    if (sess.version != SNMP_DEFAULT_VERSION) {
        printf("FAIL version=%ld 期望 SNMP_DEFAULT_VERSION\n", sess.version);
        return 1;
    }
    if (sess.retries != SNMP_DEFAULT_RETRIES) {
        printf("FAIL retries=%d 期望 %d\n", sess.retries, SNMP_DEFAULT_RETRIES);
        return 1;
    }
    if (sess.timeout != SNMP_DEFAULT_TIMEOUT) {
        printf("FAIL timeout=%ld 期望 %ld\n",
               (long)sess.timeout, (long)SNMP_DEFAULT_TIMEOUT);
        return 1;
    }
    if (sess.peername != NULL) {
        printf("FAIL peername 应被清空\n"); return 1;
    }
    printf("会话初始化 OK: version/retries/timeout 均为默认值，脏数据已被覆盖\n");
    return 0;
}

/* 在 hay 里找 needle。设备上 memmem() 不保证有（严格方言下不声明），自己写八字节的小搜索。 */
static int has_bytes(const u_char *hay, size_t hn, const u_char *needle, size_t nn)
{
    if (nn == 0 || hn < nn) return 0;
    for (size_t i = 0; i + nn <= hn; i++)
        if (memcmp(hay + i, needle, nn) == 0) return 1;
    return 0;
}

/* ------------------------------------------------------------------ *
 * 鸿蒙 PC 特有端到端测试：真实 UDP 回环上的 SNMP v2c 请求
 *
 * 上面三条断言验的是算法，这一条验的是**平台链路**：进程能不能真的建 socket、
 * 被测库能不能真的把 BER 报文写进内核网络栈、超时路径能不能走通。
 * 调用序列就是消费方 ezsnmp 每次 get 的姿势：
 *   snmp_sess_init → snmp_open → snmp_pdu_create → snmp_add_null_var → snmp_synch_response
 *
 * 做法：自己开一个 127.0.0.1 的 UDP socket 充当"代理侧"，让会话指向它——
 *   ① 请求必须**真的**被发出去：回环 socket 收得到字节 = 平台链路通（收不到 = 库没发）
 *   ② 故意不应答：同步接口必须正确走到 STAT_TIMEOUT，既不挂死也不误报成功
 * 全程不碰文件系统。设备上 /tmp 与 /etc 都是只读的，上游那几个要写文件的用例
 * （T004/T020/T026/T027）在鸿蒙 PC 上正是因此跑不过——所以这条特意做成纯网络路径。
 * ------------------------------------------------------------------ */
static int test_harmonyos_udp_loopback_e2e(void)
{
    int sock = -1, rc = 1;
    netsnmp_session sess;
    netsnmp_session *ss = NULL;
    netsnmp_pdu *pdu = NULL, *resp = NULL;
    oid name[MAX_OID_LEN];
    size_t nlen = MAX_OID_LEN;
    u_char buf[1024];
    ssize_t n;
    char peer[64];
    struct sockaddr_in addr;
    socklen_t alen;

    /* ① 扮演代理侧：回环上一个 UDP socket，端口交给内核挑 */
    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        printf("FAIL socket(AF_INET, SOCK_DGRAM) 建不出来: errno=%d\n", errno);
        return 1;
    }
    memset(&addr, 0, sizeof(addr));
    addr.sin_family      = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port        = 0;
    if (bind(sock, (struct sockaddr *)&addr, sizeof(addr)) != 0) {
        printf("FAIL bind(127.0.0.1:0) 失败: errno=%d\n", errno);
        goto done;
    }
    alen = sizeof(addr);
    if (getsockname(sock, (struct sockaddr *)&addr, &alen) != 0) {
        printf("FAIL getsockname 失败: errno=%d\n", errno);
        goto done;
    }
    snprintf(peer, sizeof(peer), "udp:127.0.0.1:%u", (unsigned)ntohs(addr.sin_port));

    /* ② 用被测库建真实会话（v2c + community），超时 1s、不重试 */
    memset(&sess, 0, sizeof(sess));
    snmp_sess_init(&sess);
    sess.version       = SNMP_VERSION_2c;
    sess.community     = (u_char *)"public";
    sess.community_len = 6;
    sess.peername      = peer;
    sess.retries       = 0;
    sess.timeout       = 1000000;

    ss = snmp_open(&sess);
    if (ss == NULL) {
        printf("FAIL snmp_open(%s) 返回 NULL\n", peer);
        goto done;
    }

    /* ③ 真实 GET 请求：sysDescr.0 */
    pdu = snmp_pdu_create(SNMP_MSG_GET);
    if (pdu == NULL) { printf("FAIL snmp_pdu_create 返回 NULL\n"); goto done; }
    if (!read_objid("1.3.6.1.2.1.1.1.0", name, &nlen)) {
        printf("FAIL read_objid sysDescr.0 失败\n"); goto done;
    }
    snmp_add_null_var(pdu, name, nlen);

    /* ④ 同步发出去：没人应答，平台必须判成超时（而不是成功，也不是挂死） */
    int st = snmp_synch_response(ss, pdu, &resp);
    pdu = NULL;                            /* snmp_synch_response 已接管并释放 */
    if (st != STAT_TIMEOUT) {
        printf("FAIL snmp_synch_response 返回 %d，期望 STAT_TIMEOUT(%d)\n",
               st, STAT_TIMEOUT);
        goto done;
    }

    /* ⑤ 关键：客户端到底有没有把报文真发到网络栈上？回环 socket 说了算 */
    n = recv(sock, buf, sizeof(buf), MSG_DONTWAIT);
    if (n <= 0) {
        printf("FAIL 回环 socket 没收到字节（库没真的发出去）: n=%zd errno=%d\n",
               n, errno);
        goto done;
    }

    /* ⑥ 协议级校验线上报文形状：不依赖 MIB 文件、不依赖任何配置 */
    static const u_char ver_v2c[3]      = {0x02, 0x01, 0x01};   /* INTEGER 1 = SNMPv2c */
    static const u_char get_tag[1]      = {0xa0};               /* GetRequest */
    static const u_char oid_sysdescr[8] = {0x2b, 0x06, 0x01, 0x02, 0x01, 0x01, 0x01, 0x00};

    if (buf[0] != 0x30) {
        printf("FAIL 报文首字节 0x%02x 不是 SEQUENCE(0x30)\n", buf[0]);
        goto done;
    }
    if (n < 7 || memcmp(buf + 2, ver_v2c, sizeof(ver_v2c)) != 0) {
        printf("FAIL 版本字段不是 SNMPv2c(02 01 01)\n");
        goto done;
    }
    if (!has_bytes(buf, (size_t)n, (const u_char *)"public", 6)) {
        printf("FAIL 报文里找不到团体名 public\n");
        goto done;
    }
    if (!has_bytes(buf, (size_t)n, get_tag, sizeof(get_tag))) {
        printf("FAIL 报文里找不到 GetRequest 标签(0xa0)\n");
        goto done;
    }
    if (!has_bytes(buf, (size_t)n, oid_sysdescr, sizeof(oid_sysdescr))) {
        printf("FAIL 报文里找不到 sysDescr.0 的 BER 编码\n");
        goto done;
    }

    printf("鸿蒙 PC 端到端 OK: %s 上真实发出 %zd 字节 v2c GET（BER 形状校验通过），"
           "无应答时正确返回 STAT_TIMEOUT\n", peer, n);
    rc = 0;

done:
    if (resp) snmp_free_pdu(resp);
    if (ss)   snmp_close(ss);
    if (sock >= 0) close(sock);
    return rc;
}

int main(void)
{
    /* 初始化 MIB 子系统。不 init 的话 read_objid 对数值 OID 仍可用，
     * 但走的是退化路径 —— 我们要测的是真实使用姿势。 */
    init_snmp("nettest");

    if (test_oid_roundtrip()) return 1;
    if (test_pdu_build())     return 1;
    if (test_session_init())  return 1;
    /* 鸿蒙 PC 特有：真实 UDP 回环端到端（CI 交叉编译只验编译，设备上真跑） */
    if (test_harmonyos_udp_loopback_e2e()) return 1;

    printf("net-snmp 5.9.5: 全部断言通过\n");
    return 0;
}
