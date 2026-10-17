// test_mcap.cpp — mcap 0.3.0 consumer test (6 assertions).
// Writes an MCAP file via mcap::McapWriter, reads it back via
// mcap::McapReader, and verifies schema/channel/message roundtrip.
// Any mismatch returns 1 (fails the conan test gate).
#define MCAP_IMPLEMENTATION
#include <mcap/mcap.hpp>

#include <cstdio>
#include <cstring>
#include <iostream>
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

int main() {
  const char* path = "test_mcap.mcap";
  std::remove(path);

  // 1-3: write path (open/schema/channel/write/close).
  {
    mcap::McapWriter writer;
    mcap::McapWriterOptions opts("ros1");
    auto status = writer.open(path, opts);
    CHECK(status.ok(), "writer.open");
    if (!status.ok()) return 1;

    mcap::Schema schema("std_msgs/String", "ros1msg", "string data");
    writer.addSchema(schema);
    CHECK(schema.id != 0, "schema registered");

    mcap::Channel channel("/chatter", "ros1", schema.id);
    writer.addChannel(channel);
    CHECK(channel.id != 0, "channel registered");

    const char* text = "Hello, HarmonyOS!";
    uint32_t len = (uint32_t)std::strlen(text);
    std::vector<std::byte> payload(4 + len);
    std::memcpy(payload.data(), &len, 4);
    std::memcpy(payload.data() + 4, text, len);

    mcap::Message msg;
    msg.channelId = channel.id;
    msg.sequence = 7;
    msg.logTime = 123456789;
    msg.publishTime = 123456789;
    msg.data = payload.data();
    msg.dataSize = payload.size();
    auto wstatus = writer.write(msg);
    CHECK(wstatus.ok(), "writer.write");
    writer.close();
  }

  // 4-6: read path (open/summary/messages/payload).
  {
    mcap::McapReader reader;
    auto status = reader.open(path);
    CHECK(status.ok(), "reader.open");
    if (!status.ok()) return 1;

    size_t count = 0;
    bool payloadOk = false;
    bool seqOk = false;
    for (const auto& view : reader.readMessages()) {
      ++count;
      seqOk = (view.message.sequence == 7);
      std::string data(reinterpret_cast<const char*>(view.message.data),
                       view.message.dataSize);
      payloadOk = (data.find("Hello, HarmonyOS!") != std::string::npos);
      CHECK(view.channel != nullptr, "channel resolved");
    }
    CHECK(count == 1, "exactly one message read");
    CHECK(seqOk, "sequence roundtrip");
    CHECK(payloadOk, "payload roundtrip");
    reader.close();
  }

  if (failures != 0) {
    std::cerr << "test_mcap FAILED: " << failures << " assertion(s)\n";
    return 1;
  }
  std::cout << "test_mcap PASSED: 6/6 assertions\n";
  std::remove(path);
  return 0;
}
