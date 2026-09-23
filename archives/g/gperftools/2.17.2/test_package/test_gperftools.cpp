#include <gperftools/tcmalloc.h>

#include <cstring>
#include <iostream>

namespace {

int fail(const char* message) {
  std::cerr << "gperftools consumer test: " << message << '\n';
  return 1;
}

}  // namespace

int main() {
  int major = 0;
  int minor = 0;
  const char* patch = nullptr;
  const char* version = tc_version(&major, &minor, &patch);

  if (version == nullptr || major != 2 || minor != 17 || patch == nullptr ||
      std::strcmp(patch, ".2") != 0 ||
      std::strcmp(version, "gperftools 2.17.2") != 0) {
    return fail("tc_version returned an unexpected version");
  }

  void* block = tc_malloc(128);
  if (block == nullptr || tc_malloc_size(block) < 128) {
    if (block != nullptr) {
      tc_free(block);
    }
    return fail("tc_malloc returned an invalid allocation");
  }

  void* zeroed = tc_calloc(4, 32);
  if (zeroed == nullptr) {
    tc_free(block);
    return fail("tc_calloc returned a null allocation");
  }
  const auto* bytes = static_cast<const unsigned char*>(zeroed);
  for (int i = 0; i < 128; ++i) {
    if (bytes[i] != 0) {
      tc_free(zeroed);
      tc_free(block);
      return fail("tc_calloc did not zero the allocation");
    }
  }

  void* resized = tc_realloc(block, 256);
  if (resized == nullptr) {
    tc_free(zeroed);
    tc_free(block);
    return fail("tc_realloc returned a null allocation");
  }
  if (tc_malloc_size(resized) < 256) {
    tc_free(zeroed);
    tc_free(resized);
    return fail("tc_realloc returned an undersized allocation");
  }

  tc_free(zeroed);
  tc_free(resized);
  std::cout << "gperftools consumer test: ok\n";
  return 0;
}
