/* test_package for libulfius 2.7.15 — actually exercises the packaged
 * library: start a real ulfius HTTP endpoint on a loopback port, send a
 * request to it with ulfius_send_http_request and verify the callback
 * response round-trips. */
#include <stdio.h>
#include <string.h>
#include <ulfius.h>

#define PORT 28744

static int callback_hello(const struct _u_request * request,
                          struct _u_response * response, void * user_data) {
  (void)request; (void)user_data;
  ulfius_set_string_body_response(response, 200, "hello harmonyos");
  return U_CALLBACK_CONTINUE;
}

int main(void) {
  struct _u_instance instance;
  struct _u_request request;
  struct _u_response response;
  int failed = 0;

  /* 1. init + register endpoint + start the framework (MHD engine) */
  if (ulfius_init_instance(&instance, PORT, NULL, NULL) != U_OK) {
    fprintf(stderr, "FAIL: ulfius_init_instance\n");
    return 1;
  }
  if (ulfius_add_endpoint_by_val(&instance, "GET", NULL, "hello", 0,
                                 &callback_hello, NULL) != U_OK) {
    fprintf(stderr, "FAIL: ulfius_add_endpoint_by_val\n");
    failed = 1;
    goto cleanup;
  }
  if (ulfius_start_framework(&instance) != U_OK) {
    fprintf(stderr, "FAIL: ulfius_start_framework\n");
    failed = 1;
    goto cleanup;
  }

  /* 2. client round trip through ulfius_send_http_request (curl backed) */
  ulfius_init_request(&request);
  ulfius_init_response(&response);
  request.http_url = o_strdup("http://127.0.0.1:28744/hello");
  if (ulfius_send_http_request(&request, &response) != U_OK) {
    fprintf(stderr, "FAIL: ulfius_send_http_request\n");
    failed = 1;
    goto cleanup2;
  }
  if (response.status != 200) {
    fprintf(stderr, "FAIL: unexpected status %ld\n", (long)response.status);
    failed = 1;
    goto cleanup2;
  }
  {
    const char * body = u_map_get(response.map_header, "NotFound");
    size_t len = response.binary_body_length;
    const char * bb = (const char *)response.binary_body;
    if (body) { /* only checking map_header api availability */ }
    if (len != strlen("hello harmonyos") || bb == NULL ||
        strncmp(bb, "hello harmonyos", len) != 0) {
      fprintf(stderr, "FAIL: body mismatch (len=%zu)\n", len);
      failed = 1;
      goto cleanup2;
    }
    printf("round trip OK: status=200 body=%.*s\n", (int)len, bb);
  }

cleanup2:
  ulfius_clean_request(&request);
  ulfius_clean_response(&response);
cleanup:
  ulfius_stop_framework(&instance);
  ulfius_clean_instance(&instance);
  if (!failed) {
    printf("test_ulfius: all checks passed\n");
    return 0;
  }
  return 1;
}
