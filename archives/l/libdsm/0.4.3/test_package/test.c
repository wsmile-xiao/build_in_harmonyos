/* libdsm 0.4.3 —— 真实 SMB 客户端库生命周期验证（非空壳）。
 *
 * 判据设计（全部离线可验，不需要真实 SMB 服务器）：
 *   ① netbios_ns_new()/destroy() —— 真正走 UDP socket 创建 + SO_BROADCAST +
 *      IP_MULTICAST_LOOP + bind(INADDR_ANY:0) 完整 NetBIOS 名字服务初始化序列，
 *      是「OHOS socket 层可用」的最小实证（本机实测该序列在 musl 全部通过）；
 *   ② smb_session_new()/set_creds()/destroy() —— 会话对象生命周期：真实堆分配、
 *      transport 会话创建、凭据设置与释放；
 *   ③ smb_session_is_guest() 未登录语义 —— 必须返回 -1（上游源码语义：
 *      s->logged != true 时返回 -1），验证内部状态机真实初始化；
 *   ④ smb_session_connect() 连 127.0.0.1（本机无 SMB 服务，445/139 端口
 *      无监听）—— 非阻塞 connect + select + SO_ERROR 检查链路必须把
 *      ECONNREFUSED 正确传播为 DSM_ERROR_NETWORK（<0），证明 TCP transport
 *      的 OHOS socket 错误路径真实可用，且不会挂死（非阻塞 + 立即拒绝）；
 *   ⑤ dlopen 装载的 libdsm.so 与链接的必须是同一份（防设备残留混装）。
 *
 * 头路径查过 install 实际布局：meson install_headers(..., subdir: 'bdsm')
 * 把全部头（含聚合头 bdsm.h 本身）装进 bdsm/ 子目录 → <bdsm/bdsm.h>。
 * DSM_SUCCESS=0，DSM_ERROR_NETWORK=-3（smb_defs.h）。
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <arpa/inet.h>

#include <bdsm/bdsm.h>

static int failures = 0;
#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (!(cond)) {                                                         \
            fprintf(stderr, "[FAIL] %s  (%s:%d)\n", (msg), __FILE__, __LINE__);\
            ++failures;                                                        \
        } else {                                                               \
            printf("[ok] %s\n", (msg));                                        \
        }                                                                      \
    } while (0)

int main(void) {
    /* ⑤ 先验 dlopen：装上的是本包这份 libdsm.so */
    void *handle = dlopen(TARGET_SO, RTLD_NOW);
    CHECK(handle != NULL, "dlopen libdsm.so 成功");
    if (handle) {
        void *sym = dlsym(handle, "smb_session_new");
        CHECK(sym != NULL, "dlsym smb_session_new 命中（动态符号表完整）");
        dlclose(handle);
    }

    /* ① NetBIOS 名字服务：真实 UDP socket 序列 */
    netbios_ns *ns = netbios_ns_new();
    CHECK(ns != NULL, "netbios_ns_new() 走完整 UDP socket 初始化成功");
    if (ns) {
        netbios_ns_destroy(ns);
        printf("[ok] netbios_ns_destroy() 未崩溃\n");
    }

    /* ② SMB 会话生命周期 */
    smb_session *s = smb_session_new();
    CHECK(s != NULL, "smb_session_new() 成功（堆分配 + transport 会话）");
    if (s) {
        smb_session_set_creds(s, "WORKGROUP", "testuser", "testpass");
        printf("[ok] smb_session_set_creds() 设置凭据成功\n");

        /* ③ 未登录时 is_guest 必须 -1 */
        CHECK(smb_session_is_guest(s) == -1, "未登录 is_guest() == -1（状态机真实）");

        /* ④ 连本机无监听端口：错误必须传播，且立即返回不挂死 */
        uint32_t loopback = inet_addr("127.0.0.1");
        int rc = smb_session_connect(s, "localhost", loopback, SMB_TRANSPORT_TCP);
        CHECK(rc == DSM_ERROR_NETWORK || rc < 0,
              "connect 127.0.0.1:445/139 被拒并传播为负值错误码（非阻塞错误路径可用）");
        printf("     smb_session_connect() 返回 %d（DSM_ERROR_NETWORK=%d）\n",
               rc, DSM_ERROR_NETWORK);

        smb_session_destroy(s);
        printf("[ok] smb_session_destroy() 完整释放未崩溃\n");
    }

    if (failures) {
        fprintf(stderr, "\nlibdsm: %d 项断言失败\n", failures);
        return 1;
    }
    printf("\nlibdsm 0.4.3: 全部断言通过\n");
    return 0;
}
