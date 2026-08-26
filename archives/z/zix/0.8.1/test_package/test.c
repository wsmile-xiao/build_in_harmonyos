#include <zix/allocator.h>
#include <zix/digest.h>
#include <zix/path.h>
#include <zix/status.h>
#include <zix/string_view.h>

#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int
fail(const char* const message)
{
  fprintf(stderr, "FAIL: %s\n", message);
  return 1;
}

static int
expect_view(const ZixStringView view,
            const char* const   expected,
            const char* const   label)
{
  const size_t expected_len = strlen(expected);

  if (view.length != expected_len) {
    fprintf(stderr,
            "FAIL: %s length: expected %zu, got %zu\n",
            label,
            expected_len,
            view.length);
    return 1;
  }

  if (memcmp(view.data, expected, expected_len)) {
    fprintf(stderr, "FAIL: %s value mismatch\n", label);
    return 1;
  }

  return 0;
}

static int
test_digest(void)
{
  const char* const data = "zix consumer test on HarmonyOS";
  const size_t      len  = strlen(data);

  const uint32_t hash32_a = zix_digest32(0U, data, len);
  const uint32_t hash32_b = zix_digest32(0U, data, len);
  const uint32_t hash32_c = zix_digest32(0U, "different input", 15U);
  const uint64_t hash64   = zix_digest64(0U, data, len);

  if (!hash32_a || !hash64) {
    return fail("digest functions returned zero for non-empty input");
  }

  if (hash32_a != hash32_b) {
    return fail("zix_digest32 is not deterministic");
  }

  if (hash32_a == hash32_c) {
    return fail("zix_digest32 produced the same value for different inputs");
  }

  return 0;
}

static int
test_status_and_views(void)
{
  const char* const ok = zix_strerror(ZIX_STATUS_SUCCESS);
  if (!ok || strcmp(ok, "Success")) {
    return fail("zix_strerror did not describe success");
  }

  const ZixStringView view = zix_string("zix");
  if (expect_view(view, "zix", "zix_string")) {
    return 1;
  }

  const ZixStringView filename = zix_path_filename("/tmp/zix/sample.txt");
  if (expect_view(filename, "sample.txt", "zix_path_filename")) {
    return 1;
  }

  const ZixStringView extension = zix_path_extension("/tmp/zix/sample.txt");
  if (expect_view(extension, ".txt", "zix_path_extension")) {
    return 1;
  }

  return 0;
}

static int
test_allocator_and_path_join(void)
{
  ZixAllocator* const allocator = zix_default_allocator();
  char* const joined = zix_path_join(allocator, "/tmp/zix", "sample.txt");
  if (!joined) {
    return fail("zix_path_join returned NULL");
  }

  const int bad_join = strcmp(joined, "/tmp/zix/sample.txt");
  zix_free(allocator, joined);
  if (bad_join) {
    return fail("zix_path_join returned an unexpected path");
  }

  void* const buffer = zix_malloc(allocator, 32U);
  if (!buffer) {
    return fail("zix_malloc returned NULL");
  }

  memset(buffer, 0x5A, 32U);
  zix_free(allocator, buffer);
  return 0;
}

int
main(void)
{
  return test_digest() || test_status_and_views() || test_allocator_and_path_join();
}
