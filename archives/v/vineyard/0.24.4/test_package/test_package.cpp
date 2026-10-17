/**
 * test_package — vineyard (v6d) 0.24.4 consumer smoke test.
 *
 * Verifies that libvineyard_client loads and its public C++ API can be used:
 *   1. include "client/client.h" + "common/util/version.h" compile
 *   2. construct a vineyard::Client (constructor is defined in libvineyard_client
 *      so this forces linking the actual shared library)
 *   3. call stateless helpers that do not require a running vineyardd server
 *      (vineyard::vineyard_version() / vineyard::Client default-construction only)
 */
#include <cstring>
#include <iostream>
#include <limits>

#include "client/client.h"
#include "common/util/version.h"

int main(int argc, char** argv) {
  (void)argc;
  (void)argv;
  int failed = 0;

  // 1. Header-only stateless API: version string is non-empty and sane.
  //    vineyard_version() is declared inside `namespace vineyard` in
  //    common/util/version.h, so it must be called as vineyard::vineyard_version().
  const char* ver = vineyard::vineyard_version();
  std::cout << "vineyard version=" << (ver ? ver : "(null)") << std::endl;
  if (ver == nullptr || std::strlen(ver) == 0) {
    std::cerr << "CHECK FAILED: vineyard_version() returned empty" << std::endl;
    failed++;
  }

  // 2. Construct the client object — forces linking libvineyard_client.so.
  //    (No Connect() is issued, so no vineyardd server is required.)
  {
    vineyard::Client client;
    // Default-constructed client must not be connected yet.
    if (client.Connected()) {
      std::cerr << "CHECK FAILED: brand-new Client reports connected" << std::endl;
      failed++;
    }
  }

  // 3. ObjectID utility: InvalidObjectID() is deterministic (numeric max),
  //    which is a stateless library API and proves the header + library work.
  {
    vineyard::ObjectID oid = vineyard::InvalidObjectID();
    vineyard::ObjectID expected =
        std::numeric_limits<vineyard::ObjectID>::max();
    if (oid != expected) {
      std::cerr << "CHECK FAILED: InvalidObjectID() != numeric max" << std::endl;
      failed++;
    }
  }

  if (failed != 0) {
    std::cerr << "test_package FAILED with " << failed << " check(s)" << std::endl;
    return 1;
  }
  std::cout << "test_package: all checks passed" << std::endl;
  return 0;
}
