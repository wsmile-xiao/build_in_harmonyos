// test_consumer.cpp — quickfix 1.15.1 consumer test (OHOS adaptation).
//
// Real consumer: includes the installed quickfix headers, links the
// installed libquickfix, builds a FIX 4.4 message, serializes it to wire
// format, parses it back, and exercises Dictionary/SessionID.  Compiled as
// C++11 because the quickfix 1.15.1 headers use dynamic exception
// specifications (`throw(...)`), which C++17 removed.
//
// NOTE: quickfix 1.15.1 has no version macro in its public API (upstream
// configure.ac itself is stale at 1.14.3), so the consumer asserts behavior,
// not a version string.  The release identity is anchored by the
// sha256-pinned v1.15.1 tag archive in conandata.yml.

#include "Message.h"
#include "Dictionary.h"
#include "SessionID.h"
#include "Values.h"

#include <iostream>
#include <string>

static int g_failures = 0;

static void check(bool condition, const char* name)
{
  if (condition)
  {
    std::cout << "PASS: " << name << std::endl;
  }
  else
  {
    std::cout << "FAIL: " << name << std::endl;
    ++g_failures;
  }
}

int main()
{
  // 1. Build a FIX 4.4 heartbeat and serialize it to wire format.
  FIX::Message msg;
  msg.getHeader().setField(FIX::BeginString("FIX.4.4"));
  msg.getHeader().setField(FIX::SenderCompID("OHOS-SENDER"));
  msg.getHeader().setField(FIX::TargetCompID("OHOS-TARGET"));
  msg.getHeader().setField(FIX::MsgType("0" /* Heartbeat */));
  msg.setField(FIX::TestReqID("ping-1"));

  const std::string raw = msg.toString();
  check(raw.find("8=FIX.4.4") != std::string::npos,
        "serialized header carries BeginString(8)=FIX.4.4");
  check(raw.find("35=0") != std::string::npos,
        "serialized MsgType(35)=Heartbeat");
  check(raw.find("112=ping-1") != std::string::npos,
        "serialized TestReqID(112)=ping-1");
  check(raw.find("10=") != std::string::npos,
        "serialized checksum trailer (10=)");

  // 2. Parse the wire bytes back (no validation: no DataDictionary needed).
  FIX::Message parsed;
  parsed.setString(raw, false);
  FIX::BeginString beginString;
  parsed.getHeader().getField(beginString);
  check(beginString.getValue() == "FIX.4.4",
        "parsed BeginString round-trips");
  check(parsed.getHeader().getField(FIX::FIELD::MsgType) == "0",
        "parsed MsgType round-trips");
  check(parsed.getField(FIX::FIELD::TestReqID) == "ping-1",
        "parsed TestReqID round-trips");

  // 3. Dictionary set/get.
  FIX::Dictionary dict;
  dict.setString("SessionQualifier", "OHOS");
  check(dict.getString("SessionQualifier") == "OHOS",
        "Dictionary string round-trip");

  // 4. SessionID component access.
  FIX::SessionID sessionId(FIX::BeginString("FIX.4.4"),
                           "SENDER", "TARGET");
  check(sessionId.getSenderCompID().getValue() == "SENDER",
        "SessionID sender component");

  std::cout << (g_failures == 0 ? "CONSUMER TEST OK"
                                : "CONSUMER TEST FAILED")
            << " (failures=" << g_failures << ")" << std::endl;
  return g_failures == 0 ? 0 : 1;
}
