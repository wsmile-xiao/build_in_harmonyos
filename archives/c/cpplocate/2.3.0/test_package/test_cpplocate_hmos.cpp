// cpplocate 2.3.0 — HarmonyOS PC (aarch64) specific verification test.
//
// Part of the cpplocate 2.3.0 delivery evidence (R01, pc1-83; R02 rework).
// Calls the cpplocate public C++ API (getExecutablePath / getModulePath /
// getLibraryPath / pathSeparator / libPrefix / libExtension / homeDir /
// locatePath) and verifies real behavior on the OHOS aarch64 verification
// path (host aarch64 userland, clang 15.0.4 OHOS toolchain, libc++).
//
// Build:
//   /data/service/hnp/bin/aarch64-unknown-linux-ohos-clang++ -std=c++17 \
//     -DSYSTEM_LINUX -I <prefix>/include \
//     test_cpplocate_hmos.cpp -L <build-native> -lcpplocate -llocate -o test_cpplocate_hmos
//
// Run (verification host is aarch64 with OHOS userland):
//   LD_LIBRARY_PATH=<build-native> TMPDIR=<writable dir> ./test_cpplocate_hmos
//
// NOTE: This test is also built and run by test_package/CMakeLists.txt as part
// of the Conan test_package automation gate (R02). CHECK() fails with a
// non-zero exit and works under NDEBUG, so the gate never relies on assert().
#include <cpplocate/cpplocate.h>

#include <cstdio>
#include <cstdlib>
#include <string>
#include <unistd.h>
#include <sys/stat.h>

namespace {

// CHECK: fail fast with a non-zero exit and a message; valid under NDEBUG.
#define CHECK(cond)                                                          \
  do {                                                                       \
    if (!(cond)) {                                                           \
      std::printf("FAIL: %s (line %d)\n", #cond, __LINE__);                  \
      return 1;                                                              \
    }                                                                        \
  } while (0)

bool isAbsPath(std::string const& p) {
  return !p.empty() && p[0] == '/';
}

bool fileExists(std::string const& p) {
  struct stat st;
  return ::stat(p.c_str(), &st) == 0;
}

} // namespace

int main() {
  // 1. Executable / module path must resolve to a real absolute path on OHOS.
  std::string exe = cpplocate::getExecutablePath();
  std::string mod = cpplocate::getModulePath();
  std::string lib = cpplocate::getLibraryPath(reinterpret_cast<void*>(&cpplocate::getExecutablePath));

  std::printf("exe=%s\n", exe.c_str());
  std::printf("module=%s\n", mod.c_str());
  std::printf("lib=%s\n", lib.c_str());

  CHECK(isAbsPath(exe));
  CHECK(isAbsPath(mod));
  CHECK(isAbsPath(lib));
  CHECK(lib.find("cpplocate") != std::string::npos || lib.find("locate") != std::string::npos);

  // 2. OHOS/Linux platform conventions: '/', 'lib', 'so'.
  std::string sep = cpplocate::pathSeparator();
  std::string pre = cpplocate::libPrefix();
  std::string ext = cpplocate::libExtension();

  std::printf("sep=%s prefix=%s ext=%s\n", sep.c_str(), pre.c_str(), ext.c_str());

  CHECK(sep == "/");
  CHECK(pre == "lib");
  CHECK(ext == "so");

  // 3. homeDir must resolve on OHOS userland.
  std::string home = cpplocate::homeDir();
  std::printf("home=%s\n", home.c_str());
  CHECK(isAbsPath(home));

  // 4. locatePath: establish a real, verifiable precondition. Create a data
  //    file in the module directory (next to the executable), then require
  //    locatePath to resolve it to an existing file; fail non-zero otherwise.
  std::string dataFile = mod + "/cpplocate_hmos_data.txt";
  FILE* f = std::fopen(dataFile.c_str(), "w");
  CHECK(f != nullptr);
  std::fputs("cpplocate-hmos\n", f);
  std::fclose(f);

  std::string located = cpplocate::locatePath(
      "cpplocate_hmos_data.txt", "share/cpplocate", reinterpret_cast<void*>(&main));
  std::printf("located=%s\n", located.c_str());

  CHECK(!located.empty());
  CHECK(fileExists(located)); // returned path must be the real located file
  std::remove(dataFile.c_str());

  // 5. profile / config dirs must return non-empty absolute paths (OHOS user dirs).
  std::string profile = cpplocate::profileDir();
  std::string config = cpplocate::configDir("cpplocate-hmos-test");
  std::string docs = cpplocate::documentDir();
  std::string temp = cpplocate::tempDir("cpplocate-hmos-test");
  std::printf("profile=%s\n", profile.c_str());
  std::printf("config=%s\n", config.c_str());
  std::printf("docs=%s\n", docs.c_str());
  std::printf("temp=%s\n", temp.c_str());

  CHECK(isAbsPath(profile));
  CHECK(isAbsPath(config));
  CHECK(isAbsPath(docs));
  CHECK(isAbsPath(temp));

  std::printf("ALL_CPPLOCATE_HMOS_ASSERTIONS_PASSED\n");
  return 0;
}
