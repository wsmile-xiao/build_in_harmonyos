/*
 * test_hos.c — HarmonyOS 专项测试用例
 *
 * 目的：验证 httpserver.h 在 HarmonyOS PC (aarch64-ohos) 平台上 epoll 事件后端
 * 的真实可用性 —— 这不是上游测试的复述，而是针对 OHOS 平台适配点的专项验证：
 *   1. EPOLL 后端事件循环（http_server_listen_addr_poll + http_server_poll）
 *   2. 同一连接上的 HTTP/1.1 keep-alive 多请求处理（timerfd 超时管理路径）
 *   3. 公开 API 业务链路：方法/目标解析 → handler → 响应状态 + 响应体
 *
 * 仅通过已安装公开头文件 <httpserver.h> 使用库。
 */
#define EPOLL
#define HTTPSERVER_IMPL
#include <httpserver.h>

#include <arpa/inet.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

#define HOST "127.0.0.1"
#define PORT 18081
#define REQ1 "GET /hello HTTP/1.1\r\nHost: " HOST "\r\nConnection: keep-alive\r\n\r\n"
#define REQ2 "GET /status HTTP/1.1\r\nHost: " HOST "\r\nConnection: close\r\n\r\n"

static volatile int handler_calls = 0;

/* 业务 handler：两个路由，验证 request_target 解析与响应状态构造 */
static void handle_request(struct http_request_s *request) {
  struct http_response_s *response = http_response_init();
  http_string_t target = http_request_target(request);

  if (target.len == 6 && memcmp(target.buf, "/hello", 6) == 0) {
    http_response_status(response, 200);
    http_response_header(response, "Content-Type", "text/plain");
    http_response_body(response, "hos-hello", 9);
  } else {
    http_response_status(response, 404);
    http_response_header(response, "Content-Type", "text/plain");
    http_response_body(response, "hos-not-found", 13);
  }
  http_respond(request, response);
  handler_calls++;
}

static int pump_server(struct http_server_s *server, int target_calls, int spins_limit) {
  int spins = 0;
  while (handler_calls < target_calls && spins < spins_limit) {
    http_server_poll(server);
    usleep(500);
    spins++;
  }
  return handler_calls >= target_calls;
}

int main(void) {
  struct http_server_s *server = http_server_init(PORT, handle_request);
  if (server == NULL) {
    fprintf(stderr, "HOS-FAIL: http_server_init\n");
    return 1;
  }
  http_server_listen_addr_poll(server, HOST);

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock < 0) {
    fprintf(stderr, "HOS-FAIL: socket\n");
    return 2;
  }
  /* 客户端读超时，避免死等 */
  struct timeval tv = {.tv_sec = 10, .tv_usec = 0};
  setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

  struct sockaddr_in addr;
  memset(&addr, 0, sizeof(addr));
  addr.sin_family = AF_INET;
  addr.sin_port = htons(PORT);
  addr.sin_addr.s_addr = inet_addr(HOST);
  if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) != 0) {
    perror("connect");
    return 3;
  }

  /* 请求 1：keep-alive 连接上的第一个请求 → 200 + hos-hello */
  if (send(sock, REQ1, (int)strlen(REQ1), 0) < 0) {
    perror("send1");
    return 4;
  }
  if (!pump_server(server, 1, 4000)) {
    fprintf(stderr, "HOS-FAIL: request1 handler not called\n");
    return 5;
  }

  /* 请求 2：同一连接第二个请求（keep-alive 路径）→ 404 + hos-not-found */
  if (send(sock, REQ2, (int)strlen(REQ2), 0) < 0) {
    perror("send2");
    return 6;
  }
  if (!pump_server(server, 2, 4000)) {
    fprintf(stderr, "HOS-FAIL: request2 handler not called\n");
    return 7;
  }

  /* 读取完整响应流 */
  char buf[8192];
  char *dst = buf;
  size_t total = 0;
  for (;;) {
    ssize_t n = recv(sock, dst, sizeof(buf) - 1 - total, 0);
    if (n <= 0)
      break;
    dst += n;
    total += (size_t)n;
  }
  close(sock);
  buf[total] = '\0';

  /* 验证可观察结果 */
  int ok_200 = 0, ok_404 = 0, ok_body1 = 0, ok_body2 = 0;
  char *p = buf;
  while ((p = strstr(p, "HTTP/1.1 ")) != NULL) {
    if (strncmp(p + 9, "200 OK", 6) == 0)
      ok_200++;
    if (strncmp(p + 9, "404 Not Found", 13) == 0)
      ok_404++;
    p++;
  }
  ok_body1 = strstr(buf, "hos-hello") != NULL;
  ok_body2 = strstr(buf, "hos-not-found") != NULL;

  printf("HOS: handler_calls=%d 200=%d 404=%d body1=%d body2=%d total=%zu\n",
         handler_calls, ok_200, ok_404, ok_body1, ok_body2, total);

  if (handler_calls == 2 && ok_200 == 1 && ok_404 == 1 && ok_body1 && ok_body2) {
    printf("HOS-PASS: epoll keep-alive HTTP/1.1 双请求验证通过 (OHOS)\n");
    return 0;
  }
  fprintf(stderr, "HOS-FAIL: 结果不匹配\n%s\n", buf);
  return 8;
}