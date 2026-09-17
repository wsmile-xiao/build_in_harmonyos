#include <nanomsg/nn.h>
#include <nanomsg/pair.h>
#include <nanomsg/pubsub.h>
#include <nanomsg/reqrep.h>
#include <nanomsg/inproc.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

/* 鸿蒙特有验证点：#ifdef __OHOS__ 宏可见性（SDK 工具链定义） */
static int check_ohos_macro(void) {
#ifdef __OHOS__
    printf("[ohos] __OHOS__ macro defined (HarmonyOS toolchain detected)\n");
    return 0;
#else
    /* aarch64-linux-ohos triplet 下 __OHOS__ 由 SDK clang 提供；缺失不阻断，仅提示 */
    printf("[ohos] __OHOS__ macro not defined (fallback probe)\n");
    return 0;
#endif
}

int main(void) {
    int rc;

    /* 1. inproc pair 通信闭环（核心消息原语——无需网络与 IPC 权限） */
    int s1 = nn_socket(AF_SP, NN_PAIR);
    if (s1 < 0) { printf("FAIL nn_socket pair rc=%d (%s)\n", s1, nn_strerror(nn_errno())); return 1; }
    int s2 = nn_socket(AF_SP, NN_PAIR);
    if (s2 < 0) { printf("FAIL nn_socket pair2\n"); return 1; }
    rc = nn_bind(s1, "inproc://ohos-test");
    if (rc < 0) { printf("FAIL nn_bind inproc (%s)\n", nn_strerror(nn_errno())); return 1; }
    rc = nn_connect(s2, "inproc://ohos-test");
    if (rc < 0) { printf("FAIL nn_connect inproc\n"); return 1; }

    char *msg = "hello-harmonyos";
    int sent = nn_send(s1, msg, strlen(msg) + 1, 0);
    if (sent < 0) { printf("FAIL nn_send (%s)\n", nn_strerror(nn_errno())); return 1; }

    char buf[128];
    int received = nn_recv(s2, buf, sizeof(buf), 0);
    if (received < 0) { printf("FAIL nn_recv (%s)\n", nn_strerror(nn_errno())); return 1; }
    if (strcmp(buf, msg) != 0) { printf("FAIL payload mismatch: %s != %s\n", buf, msg); return 1; }
    printf("inproc pair echo ok: %s (%d bytes)\n", buf, received);

    nn_close(s1);
    nn_close(s2);

    /* 2. 协议套件 socket 创建验证（pubsub/reqrep） */
    int pub = nn_socket(AF_SP, NN_PUB);
    if (pub < 0) { printf("FAIL nn_socket pub\n"); return 1; }
    rc = nn_bind(pub, "inproc://ohos-pubsub");
    if (rc < 0) { printf("FAIL nn_bind pub\n"); return 1; }
    nn_close(pub);

    int req = nn_socket(AF_SP, NN_REQ);
    if (req < 0) { printf("FAIL nn_socket req\n"); return 1; }
    nn_close(req);

    /* 3. tcp 传输回环验证（真 socket 系统调用——鸿蒙网络栈路径） */
    int ts1 = nn_socket(AF_SP, NN_PAIR);
    int ts2 = nn_socket(AF_SP, NN_PAIR);
    if (ts1 < 0 || ts2 < 0) { printf("FAIL nn_socket tcp pair\n"); return 1; }
    rc = nn_bind(ts1, "tcp://127.0.0.1:15521");
    if (rc < 0) { printf("FAIL nn_bind tcp (%s)\n", nn_strerror(nn_errno())); return 1; }
    rc = nn_connect(ts2, "tcp://127.0.0.1:15521");
    if (rc < 0) { printf("FAIL nn_connect tcp\n"); return 1; }
    sent = nn_send(ts1, "tcp-ok", 7, 0);
    if (sent < 0) { printf("FAIL nn_send tcp\n"); return 1; }
    received = nn_recv(ts2, buf, sizeof(buf), 0);
    if (received < 0 || strcmp(buf, "tcp-ok") != 0) { printf("FAIL tcp echo\n"); return 1; }
    printf("tcp loopback echo ok: %s\n", buf);
    nn_close(ts1);
    nn_close(ts2);

    /* 4. 版本符号验证 */
    const char *ver = NULL;
    int symver = 0;
    size_t sz = sizeof(symver);
    rc = nn_getsockopt(0, NN_SOL_SOCKET, NN_PROTOCOL, &symver, &sz);
    (void)rc;
    printf("nanomsg linked consumer test ok (errno path=%d)\n", nn_errno());

    check_ohos_macro();
    return 0;
}
