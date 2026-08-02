/* net-snmp 5.9.4 真实功能断言。
 *
 * 消费方 ezsnmp 走两条路，都得验：
 *   ① `net-snmp-config --version` / `--libs` —— 它在 setup.py 里靠这个脚本拿编译参数。
 *      该脚本若没装出来或吐不出东西，ezsnmp 连构建都起不来。（在 test() 里跑，见 conanfile）
 *   ② libnetsnmp 的 C API —— 本文件负责。
 *
 * 断言选的是**不需要网络**的纯本地功能，因为 test_package 在设备上跑、无 SNMP 代理可连：
 *   · OID 文本 ↔ 二进制的往返（read_objid / snprint_objid）——SNMP 的核心数据模型
 *   · 构造一个真实 GET PDU 并挂上 varbind，断言结构被正确填充
 *   · 会话结构初始化后的默认值（版本/超时/重试）
 *
 * 不做「dlopen + dlsym 看指针非空」那种探针：解析到符号不等于函数能用，
 * 本仓已有 5 例缺陷只有真实计算才暴露。
 */
#include <net-snmp/net-snmp-config.h>
#include <net-snmp/net-snmp-includes.h>
#include <stdio.h>
#include <string.h>

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

int main(void)
{
    /* 初始化 MIB 子系统。不 init 的话 read_objid 对数值 OID 仍可用，
     * 但走的是退化路径 —— 我们要测的是真实使用姿势。 */
    init_snmp("nettest");

    if (test_oid_roundtrip()) return 1;
    if (test_pdu_build())     return 1;
    if (test_session_init())  return 1;

    printf("net-snmp 5.9.4: 全部断言通过\n");
    return 0;
}
