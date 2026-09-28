// test_mcap_ohos.cpp — HarmonyOS-oriented mcap test (4 assertions).
// Verifies LZ4/ZSTD chunk-compression roundtrips plus TMPDIR writability
// on the OHOS target. Any mismatch returns 1.
#define MCAP_IMPLEMENTATION
#include <mcap/mcap.hpp>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

static int failures = 0;
#define CHECK(cond, msg)                                              \
  do {                                                                \
    if (!(cond)) {                                                    \
      std::cerr << "FAIL: " << msg << " (" << __LINE__ << ")\n";      \
      ++failures;                                                     \
    } else {                                                          \
      std::cout << "ok: " << msg << "\n";                             \
    }                                                                 \
  } while (0)

static std::string tmpPath(const char* name) {
  const char* tmp = std::getenv("TMPDIR");
  if (!tmp || !*tmp) tmp = std::getenv("TMP");
  if (!tmp || !*tmp) tmp = std::getenv("TEMP");
  if (!tmp || !*tmp) tmp = ".";
  return std::string(tmp) + "/" + name;
}

static bool roundtrip(mcap::Compression comp, const std::string& path) {
  std::remove(path.c_str());
  {
    mcap::McapWriter writer;
    mcap::McapWriterOptions opts("test");
    opts.compression = comp;
    opts.forceCompression = true;
    if (!writer.open(path, opts).ok()) return false;
    mcap::Schema schema("s", "enc", "ab");
    writer.addSchema(schema);
    mcap::Channel channel("t", "enc", schema.id);
    writer.addChannel(channel);
    std::vector<std::byte> data = {std::byte(1), std::byte(2), std::byte(3)};
    mcap::Message msg;
    msg.channelId = channel.id;
    msg.sequence = 0;
    msg.logTime = 2;
    msg.publishTime = 1;
    msg.data = data.data();
    msg.dataSize = data.size();
    if (!writer.write(msg).ok()) return false;
    writer.close();
  }
  {
    mcap::McapReader reader;
    if (!reader.open(path).ok()) return false;
    size_t count = 0;
    for (const auto& view : reader.readMessages()) {
      if (view.message.dataSize != 3) return false;
      ++count;
    }
    reader.close();
    if (count != 1) return false;
  }
  std::remove(path.c_str());
  return true;
}

int main() {
  CHECK(roundtrip(mcap::Compression::Lz4, tmpPath("ohos_lz4.mcap")), "LZ4 roundtrip via TMPDIR");
  CHECK(roundtrip(mcap::Compression::Zstd, tmpPath("ohos_zstd.mcap")), "ZSTD roundtrip via TMPDIR");
  CHECK(roundtrip(mcap::Compression::None, tmpPath("ohos_none.mcap")), "uncompressed roundtrip");
  // TMPDIR itself must be writable on the OHOS target (HMBS injects a task-local TMPDIR).
  {
    std::string probe = tmpPath("ohos_wprobe.bin");
    FILE* f = std::fopen(probe.c_str(), "wb");
    bool ok = (f != nullptr);
    if (f) {
      std::fwrite("x", 1, 1, f);
      std::fclose(f);
      std::remove(probe.c_str());
    }
    CHECK(ok, "TMPDIR writable");
  }

  if (failures != 0) {
    std::cerr << "test_mcap_ohos FAILED: " << failures << " assertion(s)\n";
    return 1;
  }
  std::cout << "test_mcap_ohos PASSED: 4/4 assertions\n";
  return 0;
}
