// cpplocate 2.3.0 — Conan test_package consumer verification.
//
// Must actually use the packaged cpplocate API (R34): resolves the current
// executable/module/library paths and checks OHOS/Linux platform conventions.
#include <cpplocate/cpplocate.h>

#include <cstdio>
#include <string>

int main() {
  std::string exe = cpplocate::getExecutablePath();
  std::string module = cpplocate::getModulePath();
  std::string lib = cpplocate::getLibraryPath(reinterpret_cast<void*>(&cpplocate::getExecutablePath));
  std::string sep = cpplocate::pathSeparator();
  std::string prefix = cpplocate::libPrefix();
  std::string ext = cpplocate::libExtension();

  std::printf("exe=%s\nmodule=%s\nlib=%s\nsep=%s prefix=%s ext=%s\n",
              exe.c_str(), module.c_str(), lib.c_str(), sep.c_str(), prefix.c_str(), ext.c_str());

  if (exe.empty() || module.empty() || lib.empty()) {
    std::printf("FAIL: path lookup returned empty\n");
    return 1;
  }
  if (sep != "/" || prefix != "lib" || ext != "so") {
    std::printf("FAIL: unexpected platform conventions\n");
    return 1;
  }
  std::printf("test_cpplocate: OK\n");
  return 0;
}