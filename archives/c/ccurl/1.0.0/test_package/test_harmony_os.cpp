#include "curl.hh"

#include <cassert>
#include <cstdio>
#include <string>
#include <sys/utsname.h>

int main() {
  struct utsname identity{};
  assert(uname(&identity) == 0);
  const std::string sysname(identity.sysname);
  assert(sysname == "HarmonyOS" || sysname == "OHOS" || sysname.find("Harmony") != std::string::npos);

  curl::global global;
  std::string body;
  curl::callback::string callback(body);
  curl::handle handle(global, callback);
  handle.set_timeout(2);
  handle.set_useragent("ccurl-harmonyos-test");

  std::puts("HARMONY_TEST_PASS=1/1");
  return 0;
}