/*
 * Conan L1 consumer test for iwnet 1.3.1.
 *
 * 真实消费者用例：仅通过 iwnet 已安装/导出的公开头文件与公开 API 使用该库，
 * 验证第三方使用者能够编译、链接、调用并获得可观察的业务结果。
 * 使用 iwnet 公开 API（iwn_poller_create / iwn_http_server_create /
 * iwn_http_response_*）创建 HTTP 服务器，并以标准 socket 客户端发起
 * 真实 HTTP 请求，断言 200 + 期望响应体。
 */
#include "iwnet/iwn_http_server.h"
#include "iwnet/iwn_poller.h"

#include <iowow/iwlog.h>
#include <iowow/iwp.h>

#include <arpa/inet.h>
#include <netinet/in.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define TEST_PORT 9393
#define EXPECTED_BODY "conan-consumer-ok"

static struct iwn_poller *g_poller = NULL;

static bool _request_handler(struct iwn_http_req *req) {
  iwrc rc = 0;
  iwn_http_response_body_set(req, EXPECTED_BODY, (ssize_t)sizeof(EXPECTED_BODY) - 1, 0);
  rc = iwn_http_response_end(req);
  if (rc) {
    iwlog_ecode_error3(rc);
  }
  return true;
}

static int _client_check(void) {
  int fd = socket(AF_INET, SOCK_STREAM, 0);
  if (fd < 0) {
    perror("socket");
    return 1;
  }
  struct sockaddr_in addr;
  memset(&addr, 0, sizeof(addr));
  addr.sin_family = AF_INET;
  addr.sin_port = htons(TEST_PORT);
  addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
  if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) != 0) {
    perror("connect");
    close(fd);
    return 1;
  }
  const char *req = "GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n";
  if (write(fd, req, strlen(req)) != (ssize_t)strlen(req)) {
    perror("write");
    close(fd);
    return 1;
  }
  char buf[1024];
  ssize_t n = read(fd, buf, sizeof(buf) - 1);
  close(fd);
  if (n <= 0) {
    perror("read");
    return 1;
  }
  buf[n] = '\0';
  if (strstr(buf, "HTTP/1.1 200") == NULL || strstr(buf, EXPECTED_BODY) == NULL) {
    fprintf(stderr, "FAIL: bad response:\n%s\n", buf);
    return 1;
  }
  printf("consumer ok: HTTP 200 + expected body\n");
  return 0;
}

int main(void) {
  iwrc rc = 0;
  iwlog_init();
  signal(SIGPIPE, SIG_IGN);
  signal(SIGTERM, SIG_IGN);

  rc = iwn_poller_create(1, 1, &g_poller);
  if (rc) {
    fprintf(stderr, "iwn_poller_create rc=%lu\n", rc);
    return 1;
  }
  struct iwn_http_server_spec spec = {
    .request_handler = _request_handler,
    .poller = g_poller,
    .listen = "127.0.0.1",
    .port = TEST_PORT,
    .socket_queue_size = 64,
  };
  rc = iwn_http_server_create(&spec, 0);
  if (rc) {
    fprintf(stderr, "iwn_http_server_create rc=%lu\n", rc);
    iwn_poller_destroy(&g_poller);
    return 1;
  }
  pthread_t thr;
  rc = iwn_poller_poll_in_thread(g_poller, "iwnet-test", &thr);
  if (rc) {
    fprintf(stderr, "iwn_poller_poll_in_thread rc=%lu\n", rc);
    iwn_poller_destroy(&g_poller);
    return 1;
  }
  usleep(300000);
  int fail = _client_check();
  iwn_poller_shutdown_request(g_poller);
  pthread_join(thr, NULL);
  iwn_poller_destroy(&g_poller);
  printf(fail == 0 ? "test_iwnet: PASS\n" : "test_iwnet: FAIL\n");
  return fail;
}