/*
 * test.c — httpserver-h 消费者测试
 *
 * 仅通过已安装的公开头文件 <httpserver.h> 使用该库：
 *   1. #define HTTPSERVER_IMPL 在唯一一个 C 文件中展开实现（官方用法）
 *   2. #define EPOLL 选择 epoll 事件后端（OHOS 平台支持 epoll_wait）
 *   3. 启动 HTTP 服务器，客户端 socket 发送 GET 请求，
 *      轮询驱动服务器事件循环，验证 handler 被调用并返回 200 OK。
 *
 * 验证的是真实业务链路：编译 → 链接 → 运行 → 可观察的 HTTP 响应结果。
 */
#define EPOLL
#define HTTPSERVER_IMPL
#include <httpserver.h>

#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define HOST "127.0.0.1"
#define PORT 18080
#define REQUEST "GET /hello HTTP/1.1\r\nHost: " HOST "\r\nConnection: close\r\n\r\n"

static volatile int handler_called = 0;

/* 业务 handler：等价于一个简单业务组件，对 /hello 返回 200 + 文本 */
static void handle_request(struct http_request_s *request) {
  struct http_response_s *response = http_response_init();
  http_response_status(response, 200);
  http_response_header(response, "Content-Type", "text/plain");
  http_response_body(response, "hello httpserver-h consumer", 27);
  http_respond(request, response);
  handler_called = 1;
}

int main(void) {
  struct http_server_s *server = http_server_init(PORT, handle_request);
  if (server == NULL) {
    fprintf(stderr, "FAIL: http_server_init\n");
    return 1;
  }
  http_server_listen_addr_poll(server, HOST);

  /* 客户端连接 */
  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock < 0) {
    fprintf(stderr, "FAIL: socket\n");
    return 2;
  }
  struct sockaddr_in addr;
  memset(&addr, 0, sizeof(addr));
  addr.sin_family = AF_INET;
  addr.sin_port = htons(PORT);
  addr.sin_addr.s_addr = inet_addr(HOST);
  if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) != 0) {
    perror("connect");
    return 3;
  }
  if (send(sock, REQUEST, (int)strlen(REQUEST), 0) < 0) {
    perror("send");
    return 4;
  }

  /* 轮询驱动服务器事件循环直到 handler 被调用 */
  int spins = 0;
  while (handler_called == 0 && spins < 2000) {
    http_server_poll(server);
    usleep(1000);
    spins++;
  }
  if (handler_called == 0) {
    fprintf(stderr, "FAIL: handler never called after %d spins\n", spins);
    return 5;
  }

  /* 读取 HTTP 响应并验证 200 OK */
  char buf[4096];
  memset(buf, 0, sizeof(buf));
  ssize_t n = recv(sock, buf, sizeof(buf) - 1, 0);
  close(sock);
  if (n <= 0) {
    fprintf(stderr, "FAIL: no response bytes (n=%zd)\n", n);
    return 6;
  }
  if (strstr(buf, "200 OK") == NULL) {
    fprintf(stderr, "FAIL: response missing '200 OK', got:\n%s\n", buf);
    return 7;
  }
  if (strstr(buf, "hello httpserver-h consumer") == NULL) {
    fprintf(stderr, "FAIL: response body missing, got:\n%s\n", buf);
    return 8;
  }

  printf("PASS: HTTP 200 OK, body verified, handler_called=%d\n", handler_called);
  return 0;
}