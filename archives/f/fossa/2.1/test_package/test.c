/*
 * Consumer-side check for the fossa Conan package.
 *
 * Exercises the packaged libfossa.a through its public ns_* API: pure
 * helpers, the ABI-affecting NS_ENABLE_IPV6 socket_address layout, and a
 * real HTTP request/response round trip through the event manager.
 */
#include "fossa.h"

#include <stdio.h>
#include <string.h>

static int g_assertions = 0;
static int g_failures = 0;

#define CHECK(expr)                                                       \
  do {                                                                    \
    g_assertions++;                                                       \
    if (!(expr)) {                                                        \
      printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #expr);              \
      g_failures++;                                                       \
    }                                                                     \
  } while (0)

static void test_base64(void) {
  char enc[64];
  char dec[64];
  const char *text = "Cesanta";
  int n;

  ns_base64_encode((const unsigned char *) text, (int) strlen(text), enc);
  CHECK(strcmp(enc, "Q2VzYW50YQ==") == 0);
  /* cs_base64_decode() reports the input characters it consumed, and
   * NUL-terminates the destination buffer itself. */
  n = ns_base64_decode((const unsigned char *) enc, (int) strlen(enc), dec);
  CHECK(n == (int) strlen(enc));
  CHECK(strcmp(dec, text) == 0);
  CHECK(ns_base64_decode((const unsigned char *) "AAAA----", 8, dec) == 4);
}

static void test_get_http_var(void) {
  static const char body[] = "key1=value1&key2=value%32&key3=";
  struct ns_str query;
  char val[32];

  query.p = body;
  query.len = strlen(body);
  CHECK(ns_get_http_var(&query, "key2", val, sizeof(val)) > 0);
  CHECK(strcmp(val, "value2") == 0);
  CHECK(ns_get_http_var(&query, "KEY1", val, sizeof(val)) > 0);
  CHECK(strcmp(val, "value1") == 0);
  CHECK(ns_get_http_var(&query, "missing", val, sizeof(val)) == -1);
}

static void test_socket_address_layout(void) {
  union socket_address sa;

  memset(&sa, 0, sizeof(sa));
  /* Only compiles when NS_ENABLE_IPV6 reaches the consumer through
   * cpp_info.defines — the macro changes this union's layout. */
  sa.sin6.sin6_family = AF_INET6;
  CHECK(sizeof(sa) >= sizeof(struct sockaddr_in6));
  CHECK(sa.sin6.sin6_family == AF_INET6);
}

static volatile int g_reply_done = 0;
static char g_reply_body[16];

static void ev_server(struct ns_connection *nc, int ev, void *ev_data) {
  (void) ev_data;
  if (ev == NS_HTTP_REQUEST) {
    ns_printf(nc, "%s", "HTTP/1.1 200 OK\r\nContent-Length: 4\r\n\r\npong");
    nc->flags |= NSF_SEND_AND_CLOSE;
  }
}

static void ev_client(struct ns_connection *nc, int ev, void *ev_data) {
  struct http_message *hm = (struct http_message *) ev_data;

  (void) nc;
  if (ev == NS_HTTP_REPLY && !g_reply_done) {
    size_t n = hm->body.len < sizeof(g_reply_body) - 1
                   ? hm->body.len : sizeof(g_reply_body) - 1;
    memcpy(g_reply_body, hm->body.p, n);
    g_reply_body[n] = '\0';
    g_reply_done = 1;
  }
}

static void test_http_round_trip(void) {
  struct ns_mgr mgr;
  struct ns_connection *listener;
  int i;

  ns_mgr_init(&mgr, NULL);
  listener = ns_bind(&mgr, "127.0.0.1:17777", ev_server);
  CHECK(listener != NULL);
  if (listener != NULL) {
    ns_set_protocol_http_websocket(listener);
    CHECK(ns_connect_http(&mgr, ev_client, "http://127.0.0.1:17777/ping",
                          NULL, NULL) != NULL);
    for (i = 0; i < 200 && !g_reply_done; i++) {
      ns_mgr_poll(&mgr, 10);
    }
    CHECK(g_reply_done == 1);
    CHECK(strcmp(g_reply_body, "pong") == 0);
  }
  ns_mgr_free(&mgr);
}

static void write_result(const char *path) {
  FILE *fp;

  if (path == NULL || path[0] == '\0') return;
  fp = fopen(path, "w");
  if (fp == NULL) return;
  fprintf(fp, "executed=1 assertions=%d failures=%d\n", g_assertions, g_failures);
  fclose(fp);
}

int main(int argc, char *argv[]) {
  const char *result_path = argc > 1 ? argv[1] : "";

  test_base64();
  test_get_http_var();
  test_socket_address_layout();
  test_http_round_trip();

  printf("fossa test_package: %d assertions, %d failures -> %s\n",
         g_assertions, g_failures, g_failures == 0 ? "PASS" : "FAIL");
  write_result(result_path);
  return g_failures == 0 ? 0 : 1;
}
