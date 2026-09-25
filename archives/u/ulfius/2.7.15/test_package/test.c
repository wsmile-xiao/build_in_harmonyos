/*
 * test.c — test_package consumer test for Ulfius 2.7.15.
 * Real API usage (R34): initialise a framework instance, register a GET
 * endpoint, start the (plain-HTTP) daemon, send a request through ulfius's
 * own HTTP client (curl) and verify the 200 response. HTTPS is intentionally
 * not exercised because libmicrohttpd is published without GnuTLS/HTTPS
 * support (see test_package/MANIFEST.yml audit).
 */
#include <ulfius.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int callback_hello(const struct _u_request * request,
                          struct _u_response * response,
                          void * user_data) {
  (void) request;
  (void) user_data;
  u_map_put(response->map_header, "Content-Type", "text/plain");
  ulfius_set_string_body_response(response, 200, "Hello Ulfius");
  return U_CALLBACK_CONTINUE;
}

int main(void) {
  struct _u_instance instance;
  struct _u_request req;
  struct _u_response resp;
  char url[128];
  int ret = 0;

  memset(&instance, 0, sizeof(instance));
  memset(&req, 0, sizeof(req));
  memset(&resp, 0, sizeof(resp));

  if (ulfius_init_instance(&instance, 18888, NULL, NULL) != U_OK) {
    fprintf(stderr, "ulfius_init_instance failed\n");
    return 1;
  }
  if (ulfius_add_endpoint_by_val(&instance, "GET", "/hello", NULL, 0,
                                 &callback_hello, NULL) != U_OK) {
    fprintf(stderr, "ulfius_add_endpoint_by_val failed\n");
    ulfius_clean_instance(&instance);
    return 2;
  }
  if (ulfius_start_framework(&instance) != U_OK) {
    fprintf(stderr, "ulfius_start_framework failed\n");
    ulfius_clean_instance(&instance);
    return 3;
  }

  ulfius_init_request(&req);
  snprintf(url, sizeof(url), "http://localhost:%u/hello", instance.port);
  req.http_url = strdup(url);
  ulfius_init_response(&resp);

  if (ulfius_send_http_request(&req, &resp) != U_OK) {
    fprintf(stderr, "ulfius_send_http_request failed\n");
    ret = 4;
  } else if (resp.status != 200) {
    fprintf(stderr, "unexpected status %ld\n", resp.status);
    ret = 5;
  } else {
    printf("ulfius consumer test: GET /hello -> status %ld\n", resp.status);
  }

  ulfius_clean_response(&resp);
  ulfius_clean_request(&req);
  ulfius_stop_framework(&instance);
  ulfius_clean_instance(&instance);

  if (ret == 0)
    printf("consumer test PASS\n");
  return ret;
}
