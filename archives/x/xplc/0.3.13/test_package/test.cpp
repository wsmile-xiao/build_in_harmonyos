/*
 * Consumer test for xplc 0.3.13 (XPLC - Cross-Platform Lightweight Components).
 *
 * Asserts only behaviour a downstream project can observe through the
 * installed headers + libraries, so it genuinely depends on the packaged
 * artifact (R34).  The UUID string cases follow upstream tests/test007.cpp
 * verbatim (braces form) rather than the header comment, because the shipped
 * UuidToString() emits "{...}" while its doc block claims otherwise.
 *
 * Reported as the 鸿蒙特有测试 row in the PR body: these are consumer
 * assertions and are NOT part of the upstream denominator.
 */
#include <cstdio>
#include <cstring>

#include <xplc/core.h>
#include <xplc/IModuleLoader.h>
#include <xplc/utils.h>
#include <xplc/uuidops.h>

static int passed = 0;
static int failed = 0;

static void check(bool cond, const char* what) {
  if (cond) {
    ++passed;
  } else {
    ++failed;
    std::fprintf(stderr, "FAIL: %s\n", what);
  }
}

int main() {
  // 1. UUID is the 16-byte value type every interface id is built from.
  check(sizeof(UUID) == 16, "sizeof(UUID) == 16");

  // 2. Parsing an unbraced UUID string (upstream test007 u2 form).
  const UUID expect = {0xe87db3a0, 0x109a, 0x4ecb,
                       {0x86, 0x64, 0x66, 0x85, 0x45, 0x20, 0xa6, 0xcc}};
  check(UuidFromString("e87db3a0-109a-4ecb-8664-66854520a6cc") == expect,
        "UuidFromString parses the unbraced form");

  // 3. Parsing the braced form (upstream test007 u3 form).
  check(UuidFromString("{e87db3a0-109a-4ecb-8664-66854520a6cc}") == expect,
        "UuidFromString parses the braced form");

  // 4. A half-open brace is rejected and yields UUID_null (test007 u6 form).
  check(UuidFromString("{e87db3a0-109a-4ecb-8664-66854520a6cc") == UUID_null,
        "UuidFromString rejects a half-open brace");

  // 5. UuidToString emits the braced canonical form (upstream behaviour).
  char buf[39];
  std::memset(buf, 0, sizeof(buf));
  UuidToString(expect, buf);
  check(std::strcmp(buf, "{e87db3a0-109a-4ecb-8664-66854520a6cc}") == 0,
        "UuidToString emits the braced form");

  // 6. Round trip survives.
  check(UuidFromString(buf) == expect, "FromString(ToString(u)) == u");

  // 7. Value equality/inequality operators used all over the API.
  check(expect == UuidFromString("{e87db3a0-109a-4ecb-8664-66854520a6cc}"),
        "UUID equality operator");
  check(expect != UUID_null, "UUID inequality operator against UUID_null");

  // 8. The C entry point the whole component system hangs off.
  IServiceManager* servmgr = XPLC_getServiceManager();
  check(servmgr != 0, "XPLC_getServiceManager() returns non-null");
  if (!servmgr) {
    std::fprintf(stderr, "xplc consumer assertions: %d passed, %d failed\n",
                 passed, failed);
    return 1;
  }

  // 9. Resolving the module loader service (upstream tests/test004.cpp shape:
  //    getObject() + mutate<>()).  Reaching it wires up xplc/loader.cpp, so a
  //    successful lookup is the dynamic-loading check for the OHOS target.
  //    NOTE mutate() *consumes* its argument — it releases the inbound
  //    reference itself — so loader_obj must NOT be released again.
  IObject* loader_obj = servmgr->getObject(XPLC_moduleLoader);
  check(loader_obj != 0, "service manager resolves XPLC_moduleLoader");
  if (loader_obj) {
    IModuleLoader* loader = mutate<IModuleLoader>(loader_obj);
    check(loader != 0, "module loader exposes IModuleLoader");
    if (loader) {
      loader->release();
    }
  }
  servmgr->release();

  std::printf("xplc consumer assertions: %d passed, %d failed\n", passed,
              failed);
  return failed ? 1 : 0;
}
