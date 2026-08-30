// cista 0.16 — HarmonyOS PC (aarch64) specific verification test.
//
// Part of the cista 0.16 local delivery evidence (R02 rework).
// Calls the cista public API (serialize/deserialize roundtrip + mmap
// read/write persistence) and verifies behavior on the OHOS aarch64
// verification path (host aarch64 userland, clang 15.0.4 OHOS toolchain
// from /data/service/hnp/bin, libc++).
//
// Build (OHOS cross):
//   /data/service/hnp/bin/aarch64-unknown-linux-ohos-clang++ -std=c++17 \
//     -I include test_hmos.cpp -o test_hmos
//
// Run (the verification host is aarch64 with OHOS userland):
//   TMPDIR=<writable dir> ./test_hmos
#include "cista/containers.h"
#include "cista/mmap.h"
#include "cista/serialization.h"

#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <unistd.h>
#include <vector>

namespace {

std::string make_tmp_file(char const* tag) {
  char const* env = std::getenv("TMPDIR");
  std::string dir = (env && *env) ? env : "/storage/Users/currentUser";
  std::string tmpl = dir + "/" + tag + "_XXXXXX";
  std::vector<char> buf(tmpl.begin(), tmpl.end());
  buf.push_back('\0');
  int fd = mkstemp(buf.data());
  assert(fd != -1);
  close(fd);
  return std::string(buf.data());
}

void test_serialize_roundtrip() {
  struct payload {
    int a_{0};
    struct inner {
      int b_{0};
      int c_{0};
      cista::raw::string d_;
    } j_;
  };

  cista::byte_buf buf;
  {
    payload obj{1, {2, 3, cista::raw::string{"testtes"}}};
    buf = cista::serialize(obj);
  }
  assert(buf.size() == sizeof(payload));

  auto const serialized =
      cista::deserialize<payload>(&buf[0], &buf[0] + buf.size());
  assert(serialized->a_ == 1);
  assert(serialized->j_.b_ == 2);
  assert(serialized->j_.c_ == 3);
  assert(serialized->j_.d_ == cista::raw::string{"testtes"});
  std::printf("[hmos] serialize/deserialize roundtrip OK\n");
}

void test_mmap_persistence() {
  std::string const path = make_tmp_file("cista_hmos_mmap");

  // pre-size the backing file to 4096 bytes so mmap has a mapping
  {
    std::ofstream ofs(path, std::ios::binary | std::ios::trunc);
    ofs.seekp(4095);
    ofs.put('\0');
    assert(ofs.good());
  }

  {
    // MODIFY ("r+") mapping — WRITE ("w+") would truncate the backing file
    // to 0 bytes, leaving an empty (null data) mapping; MODIFY keeps the
    // pre-sized file mapped read/write.
    cista::mmap m{path.c_str(), cista::mmap::protection::MODIFY};
    assert(m.data() != nullptr);
    auto* p = reinterpret_cast<int*>(m.data());
    p[0] = 12345;
    p[1] = 67890;
    m.sync();
  }

  {
    // READ ("r") mapping, verify persistence
    cista::mmap m{path.c_str(), cista::mmap::protection::READ};
    assert(m.data() != nullptr);
    auto const* p = reinterpret_cast<int const*>(m.data());
    assert(p[0] == 12345);
    assert(p[1] == 67890);
  }

  std::remove(path.c_str());
  std::printf("[hmos] mmap read/write persistence OK\n");
}

}  // namespace

int main() {
  test_serialize_roundtrip();
  test_mmap_persistence();
  std::printf("[hmos] ALL HARMONYOS-SPECIFIC TESTS PASSED\n");
  return 0;
}