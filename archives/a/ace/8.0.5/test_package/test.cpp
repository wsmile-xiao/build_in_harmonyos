// test_package consumer test for ace/8.0.5
// Calls real ACE APIs: version string, ACE_OS layer, and a message block.
#include <cstdio>
#include <cstring>

#include "ace/ACE.h"
#include "ace/Version.h"
#include "ace/Message_Block.h"
#include "ace/OS_NS_stdlib.h"

int main() {
  // Real ACE_OS function call (getpid) to prove the library links and runs.
  pid_t pid = ACE_OS::getpid();
  if (pid <= 0) {
    std::printf("FAIL: ACE_OS::getpid() returned %d\n", static_cast<int>(pid));
    return 1;
  }

  // ACE_VERSION comes from ace/Version.h.
  if (std::strncmp(ACE_VERSION, "8.0.5", 5) != 0) {
    std::printf("FAIL: ACE_VERSION = %s (expected 8.0.5)\n", ACE_VERSION);
    return 1;
  }

  // Use a Message_Block to exercise real ACE object construction.
  ACE_Message_Block mb(64);
  std::memcpy(mb.wr_ptr(), "ace-8.0.5", 9);
  mb.wr_ptr(9);
  if (mb.length() != 9) {
    std::printf("FAIL: Message_Block length = %d (expected 9)\n",
                static_cast<int>(mb.length()));
    return 1;
  }

  std::printf("test ace 8.0.5: OK (pid=%d, version=%s, mb_len=%d)\n",
              static_cast<int>(pid), ACE_VERSION, static_cast<int>(mb.length()));
  return 0;
}
