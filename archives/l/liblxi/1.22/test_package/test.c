/* liblxi 1.22 消费者测试（真机运行）。
 *
 * 以库使用者身份真实调用 lxi_init / lxi_connect / lxi_send / lxi_receive /
 * lxi_disconnect：在本地回环起一个 TCP 监听套接字模拟 RAW 协议仪器，
 * 经 liblxi 的 RAW 路径完成连接→发送 SCPI 查询→接收仪器应答的全链路，
 * 每一步用 CHECK 断言实际行为（退出码 = 全部断言通过与否）。
 */
#include <arpa/inet.h>
#include <netinet/in.h>
#include <string.h>
#include <stdio.h>
#include <sys/socket.h>
#include <unistd.h>

#include <lxi.h>

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg) do { \
    checks++; \
    if (!(cond)) { printf("FAIL: %s (line %d)\n", msg, __LINE__); failures++; } \
    else { printf("PASS: %s\n", msg); } \
} while (0)

int main(void) {
    /* 1. 库初始化 */
    CHECK(lxi_init() == LXI_OK, "lxi_init() returns LXI_OK");

    /* 2. 本地回环监听套接字，模拟一台 RAW/TCP 仪器 */
    int srv = socket(AF_INET, SOCK_STREAM, 0);
    CHECK(srv >= 0, "create loopback listener socket");
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = 0;
    CHECK(bind(srv, (struct sockaddr *)&addr, sizeof(addr)) == 0, "bind loopback");
    socklen_t len = sizeof(addr);
    CHECK(getsockname(srv, (struct sockaddr *)&addr, &len) == 0, "getsockname");
    CHECK(listen(srv, 1) == 0, "listen");
    int port = ntohs(addr.sin_port);

    /* 3. 经库 RAW 协议路径连接（真实 TCP 三次握手） */
    int device = lxi_connect("127.0.0.1", port, NULL, 2000, RAW);
    CHECK(device >= 0, "lxi_connect(RAW) to loopback instrument");

    int peer = accept(srv, NULL, NULL);
    CHECK(peer >= 0, "instrument side accepts connection");

    /* 4. 经库发送 SCPI 查询，仪器端应原样收到 */
    const char *query = "*IDN?";
    CHECK(lxi_send(device, query, (int)strlen(query), 2000) == (int)strlen(query),
          "lxi_send(*IDN?) returns byte count");
    char rxbuf[64];
    ssize_t n = recv(peer, rxbuf, sizeof(rxbuf) - 1, 0);
    CHECK(n == (ssize_t)strlen(query) && memcmp(rxbuf, query, (size_t)n) == 0,
          "instrument receives *IDN? verbatim");

    /* 5. 仪器应答，经库接收并断言内容一致 */
    const char *reply = "HO PC,liblxi-test,1,1.22\n";
    CHECK(send(peer, reply, strlen(reply), 0) == (ssize_t)strlen(reply),
          "instrument replies to query");
    memset(rxbuf, 0, sizeof(rxbuf));
    n = lxi_receive(device, rxbuf, (int)(sizeof(rxbuf) - 1), 2000);
    CHECK(n == (ssize_t)strlen(reply) && memcmp(rxbuf, reply, (size_t)n) == 0,
          "lxi_receive() gets reply verbatim");

    /* 6. 断开 */
    CHECK(lxi_disconnect(device) == LXI_OK, "lxi_disconnect() returns LXI_OK");

    close(peer);
    close(srv);

    printf("checks=%d failures=%d\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
