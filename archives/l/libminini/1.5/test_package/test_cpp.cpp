#include <cstdio>
#include <iostream>
#include <string>

#include "minIni.h"

#define CHECK(expr) do { \
  if (!(expr)) { \
    std::cerr << "CHECK failed at " << __FILE__ << ':' << __LINE__ \
              << ": " << #expr << '\n'; \
    return 1; \
  } \
} while (0)

int main()
{
  const std::string filename = "libminini-consumer-cpp.ini";
  minIni ini(filename);

  CHECK(ini.put("profile", "name", "OpenHarmony"));
  CHECK(ini.put("profile", "generation", 6));
  CHECK(ini.put("profile", "ready", true));
  CHECK(ini.gets("profile", "name") == "OpenHarmony");
  CHECK(ini.geti("profile", "generation") == 6);
  CHECK(ini.getbool("profile", "ready"));
  CHECK(ini.gets("profile", "missing", "fallback") == "fallback");
  CHECK(ini.hassection("profile"));
  CHECK(ini.haskey("profile", "generation"));
  CHECK(ini.getsection(0) == "profile");
  CHECK(!ini.getkey("profile", 0).empty());
  CHECK(ini.del("profile", "ready"));
  CHECK(!ini.haskey("profile", "ready"));
  CHECK(ini.del("profile"));
  CHECK(!ini.hassection("profile"));
  CHECK(std::remove(filename.c_str()) == 0);

  std::cout << "libminini C++ consumer test passed\n";
  return 0;
}
