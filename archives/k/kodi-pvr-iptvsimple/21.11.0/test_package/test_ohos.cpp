// HarmonyOS-specific test for kodi-pvr-iptvsimple/21.11.0.
//
// This test targets platform behaviour that only matters on the OHOS target
// (aarch64-linux-ohos, musl + libc++), i.e. the parts of the adaptation that
// a compile-only check cannot prove:
//
//   1. The module is loadable with RTLD_NOW: on OHOS/musl every relocation of
//      the module (and of its DT_NEEDED entries) must resolve eagerly — a
//      module built with a dangling dependency fails here instead of crashing
//      the Kodi host later.
//   2. The add-on's zlib symbols resolve against the OHOS *system* zlib at
//      runtime. conan zlib/1.3.1 is a static non-PIC archive (system same-name
//      library, R26) and cannot be linked into a shared module, so the recipe
//      links the SDK sysroot libz.so (DT_NEEDED "libz.so"); the loader must
//      find the OHOS system zlib component. Resolving "inflate" through the
//      module handle and dladdr()'ing it yields the file the loader actually
//      mapped, which must be the system libz.
//   3. The Kodi binary add-on ABI version compiled into the module matches the
//      SDK headers used for the OHOS build (PVR instance API 8.3.0, min
//      8.2.0) and the module file name/identity is the packaged pvr.iptvsimple.
//
// Built with -Wall -Wextra -Werror (see test_package/CMakeLists.txt).

#include <dlfcn.h>
#include <link.h>

#include <cstdio>
#include <cstring>

namespace
{
int g_failures = 0;

void Check(bool condition, const char* what)
{
  if (condition)
  {
    std::printf("ok   - %s\n", what);
  }
  else
  {
    std::fprintf(stderr, "FAIL - %s\n", what);
    ++g_failures;
  }
}

constexpr int kAddonInstancePvr = 107;
}  // namespace

int main(int argc, char** argv)
{
  if (argc != 2)
  {
    std::fprintf(stderr, "usage: %s <path to pvr.iptvsimple.so>\n", argv[0]);
    return 2;
  }
  const char* module_path = argv[1];

  // Informational: the test binary does not link zlib, so before the add-on
  // module is loaded the system zlib should not be part of the process.
  if (dlopen("libz.so", RTLD_NOLOAD | RTLD_LAZY) != nullptr)
    std::printf("note - libz.so was already loaded before the add-on module\n");

  // 1. Eager binding: RTLD_NOW must resolve every relocation of the module
  //    and of its DT_NEEDED dependencies.
  void* handle = dlopen(module_path, RTLD_NOW | RTLD_GLOBAL);
  if (handle == nullptr)
  {
    std::fprintf(stderr, "FAIL - dlopen(RTLD_NOW, %s): %s\n", module_path, dlerror());
    return 1;
  }
  std::printf("ok   - module loads with RTLD_NOW (all OHOS relocations resolved)\n");

  // 3. Add-on identity and ABI version (SDK headers = xbmc 21.3-Omega).
  using GetTypeVersionFn = const char* (*)(int);
  auto get_type_version = reinterpret_cast<GetTypeVersionFn>(
      dlsym(handle, "ADDON_GetTypeVersion"));
  auto get_type_min_version = reinterpret_cast<GetTypeVersionFn>(
      dlsym(handle, "ADDON_GetTypeMinVersion"));
  Check(get_type_version != nullptr, "ADDON_GetTypeVersion is exported");
  Check(get_type_min_version != nullptr, "ADDON_GetTypeMinVersion is exported");
  if (get_type_version != nullptr)
  {
    const char* version = get_type_version(kAddonInstancePvr);
    Check(version != nullptr && std::strcmp(version, "8.3.0") == 0,
          "PVR instance API compiled in is 8.3.0");
  }
  if (get_type_min_version != nullptr)
  {
    const char* min_version = get_type_min_version(kAddonInstancePvr);
    Check(min_version != nullptr && std::strcmp(min_version, "8.2.0") == 0,
          "PVR instance minimum API compiled in is 8.2.0");
  }

  {
    void* create = dlsym(handle, "ADDON_Create");
    Check(create != nullptr, "ADDON_Create is exported");
    if (create != nullptr)
    {
      Dl_info info{};
      if (dladdr(create, &info) != 0 && info.dli_fname != nullptr)
      {
        std::printf("note - module mapped from %s\n", info.dli_fname);
        Check(std::strstr(info.dli_fname, "pvr.iptvsimple.so") != nullptr,
              "resolved module file is the packaged pvr.iptvsimple.so");
      }
      else
      {
        Check(false, "dladdr(ADDON_Create) resolves the module path");
      }
    }
  }

  // 2. The system zlib resolved at runtime.
  {
    void* inflate_sym = dlsym(handle, "inflate");
    Check(inflate_sym != nullptr,
          "module zlib symbols (inflate) resolve through its DT_NEEDED libz.so");
    if (inflate_sym != nullptr)
    {
      Dl_info info{};
      if (dladdr(inflate_sym, &info) != 0 && info.dli_fname != nullptr)
      {
        std::printf("note - zlib inflate() resolved from %s\n", info.dli_fname);
        Check(std::strstr(info.dli_fname, "libz") != nullptr,
              "inflate() is provided by the OHOS system zlib library");
      }
      else
      {
        Check(false, "dladdr(inflate) resolves the zlib module path");
      }
    }
  }

  dlclose(handle);

  if (g_failures != 0)
  {
    std::fprintf(stderr, "%d assertion(s) failed\n", g_failures);
    return 1;
  }
  std::printf("all kodi-pvr-iptvsimple HarmonyOS assertions passed\n");
  return 0;
}
