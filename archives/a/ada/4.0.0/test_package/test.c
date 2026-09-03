#include <stdio.h>
#include <string.h>

#include "ada_c.h"

/* test_package consumer test: actually exercise the ada C API. */
int main(void) {
  /* Parse a simple URL using ada's C API */
  const char* input = "https://example.com/path/x?q=1#frag";
  ada_url url = ada_parse(input, strlen(input));
  if (url == NULL) {
    printf("FAIL: ada_parse returned NULL\n");
    return 1;
  }

  ada_string href = ada_get_href(url);
  printf("ada 4.0.0 test: href=%.*s\n", (int)href.length, href.data);

  ada_string host = ada_get_hostname(url);
  printf("ada 4.0.0 test: hostname=%.*s\n", (int)host.length, host.data);

  ada_string proto = ada_get_protocol(url);
  printf("ada 4.0.0 test: protocol=%.*s\n", (int)proto.length, proto.data);

  if (host.length != strlen("example.com") ||
      strncmp(host.data, "example.com", host.length) != 0) {
    printf("FAIL: unexpected hostname\n");
    ada_free(url);
    return 1;
  }

  ada_free(url);

  /* Invalid input must be rejected (ada_parse returns an object; check validity) */
  ada_url bad = ada_parse("http://[::1", 10);
  if (bad != NULL && ada_is_valid(bad)) {
    printf("FAIL: invalid URL accepted\n");
    ada_free(bad);
    return 1;
  }
  ada_free(bad);

  printf("test ada 4.0.0: OK\n");
  return 0;
}