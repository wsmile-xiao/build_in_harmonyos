#include <serd/serd.h>

#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int fail(const char* message)
{
  fprintf(stderr, "%s\n", message);
  return 1;
}

int main(void)
{
  const uint8_t* ok = serd_strerror(SERD_SUCCESS);
  if (!ok || strstr((const char*)ok, "Success") == NULL) {
    return fail("unexpected SERD_SUCCESS string");
  }

  SerdNode node = serd_node_from_string(SERD_URI, (const uint8_t*)"http://example.org/s");
  if (node.type != SERD_URI || node.n_bytes != strlen("http://example.org/s")) {
    return fail("serd_node_from_string produced an unexpected node");
  }

  SerdNode copy = serd_node_copy(&node);
  if (!serd_node_equals(&node, &copy)) {
    serd_node_free(&copy);
    return fail("serd_node_copy/equals failed");
  }

  serd_node_free(&copy);
  puts("serd C API smoke passed");
  return 0;
}
