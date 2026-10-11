// Consumer-side verification for kodi-pvr-iptvsimple/21.11.0.
//
// pvr.iptvsimple is a Kodi PVR client add-on: a module dlopen()ed by the Kodi
// host, with no standalone entry point. This test verifies the packaged
// artifact itself, headlessly:
//
// Part 1 — Kodi 21 binary add-on contract (dlopen + ADDONCREATOR entry points)
//   the module loads and exports ADDON_Create / ADDON_GetTypeVersion /
//   ADDON_GetTypeMinVersion; the versioned C ABI is identical to the vendored
//   xbmc 21.3-Omega SDK headers (kodi/versions.h): main 2.0.2/2.0.0,
//   general 1.0.5/1.0.4, PVR instance 8.3.0/8.2.0, unknown types "0.0.0".
//
// Part 2 — real functionality through the packaged code
//   the add-on's internal FileUtils decompression helpers are exported by the
//   module and exercised directly: GzipInflate() (zlib inflate path, ZLIB) and
//   XzDecompress() (liblzma path) must decode their respective streams byte
//   for byte, and PathCombine() must build POSIX paths. This proves the
//   compiled module really carries the zlib/lzma code paths it links.
//
// A test-only forward declaration of the internal helper class is used
// because the add-on installs no public headers (the symbols are resolved
// from the packaged module).

#include <dlfcn.h>

#include <cstdio>
#include <cstring>
#include <string>

namespace iptvsimple
{
namespace utilities
{
// Declared only; definitions are provided by the packaged module (symbols are
// exported — see the module's dynamic symbol table).
class FileUtils
{
public:
  static std::string PathCombine(const std::string& path, const std::string& fileName);
  static bool GzipInflate(const std::string& compressedBytes, std::string& uncompressedBytes);
  static bool XzDecompress(const std::string& compressedBytes, std::string& uncompressedBytes);
};
}  // namespace utilities
}  // namespace iptvsimple

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

void CheckString(const char* actual, const char* expected, const char* what)
{
  if (actual == nullptr)
  {
    std::fprintf(stderr, "FAIL - %s ()\n", what);
    ++g_failures;
    return;
  }
  if (std::strcmp(actual, expected) == 0)
  {
    std::printf("ok   - %s (%s)\n", what, actual);
  }
  else
  {
    std::fprintf(stderr, "FAIL - %s: got \"%s\", expected \"%s\"\n", what, actual, expected);
    ++g_failures;
  }
}

// gzip("pvr.iptvsimple gzip round-trip\n"), produced by gzip with mtime=0.
const unsigned char kGzipSample[] = {
    0x1f, 0x8b, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0xff, 0x2b, 0x28, 0x2b, 0xd2, 0xcb,
    0x2c, 0x28, 0x29, 0x2b, 0xce, 0xcc, 0x2d, 0xc8, 0x49, 0x55, 0x48, 0xaf, 0xca, 0x2c, 0x50,
    0x28, 0xca, 0x2f, 0xcd, 0x4b, 0xd1, 0x2d, 0x29, 0xca, 0x2c, 0xe0, 0x02, 0x00, 0xae, 0xc8,
    0x7c, 0xde, 0x1f, 0x00, 0x00, 0x00};

// xz("pvr.iptvsimple xz round-trip\n").
const unsigned char kXzSample[] = {
    0xfd, 0x37, 0x7a, 0x58, 0x5a, 0x00, 0x00, 0x04, 0xe6, 0xd6, 0xb4, 0x46, 0x02, 0x00, 0x21,
    0x01, 0x16, 0x00, 0x00, 0x00, 0x74, 0x2f, 0xe5, 0xa3, 0x01, 0x00, 0x1c, 0x70, 0x76, 0x72,
    0x2e, 0x69, 0x70, 0x74, 0x76, 0x73, 0x69, 0x6d, 0x70, 0x6c, 0x65, 0x20, 0x78, 0x7a, 0x20,
    0x72, 0x6f, 0x75, 0x6e, 0x64, 0x2d, 0x74, 0x72, 0x69, 0x70, 0x0a, 0x00, 0x00, 0x00, 0x00,
    0x37, 0xe9, 0xc4, 0x73, 0xc5, 0x46, 0xb1, 0x13, 0x00, 0x01, 0x35, 0x1d, 0x44, 0x1b, 0xb1,
    0xe1, 0x1f, 0xb6, 0xf3, 0x7d, 0x01, 0x00, 0x00, 0x00, 0x00, 0x04, 0x59, 0x5a};

constexpr int kAddonGlobalMain = 0;
constexpr int kAddonGlobalGeneral = 3;
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

  void* handle = dlopen(module_path, RTLD_NOW | RTLD_LOCAL);
  if (handle == nullptr)
  {
    std::fprintf(stderr, "FAIL - dlopen(%s): %s\n", module_path, dlerror());
    return 1;
  }
  std::printf("ok   - dlopen(%s)\n", module_path);

  using GetTypeVersionFn = const char* (*)(int);
  auto get_type_version = reinterpret_cast<GetTypeVersionFn>(
      dlsym(handle, "ADDON_GetTypeVersion"));
  auto get_type_min_version = reinterpret_cast<GetTypeVersionFn>(
      dlsym(handle, "ADDON_GetTypeMinVersion"));
  void* addon_create = dlsym(handle, "ADDON_Create");

  Check(addon_create != nullptr, "module exports ADDON_Create");
  Check(get_type_version != nullptr, "module exports ADDON_GetTypeVersion");
  Check(get_type_min_version != nullptr, "module exports ADDON_GetTypeMinVersion");

  // Part 1: Kodi binary add-on C ABI contract.
  CheckString(get_type_version(kAddonInstancePvr), "8.3.0",
              "PVR instance API version is 8.3.0");
  CheckString(get_type_min_version(kAddonInstancePvr), "8.2.0",
              "PVR instance minimum API version is 8.2.0");
  CheckString(get_type_version(kAddonGlobalMain), "2.0.2", "global main API version is 2.0.2");
  CheckString(get_type_min_version(kAddonGlobalMain), "2.0.0",
              "global main minimum API version is 2.0.0");
  CheckString(get_type_version(kAddonGlobalGeneral), "1.0.5",
              "global general API version is 1.0.5");
  CheckString(get_type_min_version(kAddonGlobalGeneral), "1.0.4",
              "global general minimum API version is 1.0.4");
  CheckString(get_type_version(9999), "0.0.0", "unknown add-on type reports 0.0.0");

  // Part 2: real functionality through the packaged module.
  {
    std::string in(reinterpret_cast<const char*>(kGzipSample), sizeof(kGzipSample));
    std::string out;
    const bool ok = iptvsimple::utilities::FileUtils::GzipInflate(in, out);
    Check(ok && out == "pvr.iptvsimple gzip round-trip\n",
          "GzipInflate() decodes a gzip stream through the zlib path");
  }
  {
    std::string in("not-a-gzip-stream");
    std::string out;
    iptvsimple::utilities::FileUtils::GzipInflate(in, out);
    Check(out.empty(), "GzipInflate() yields no data for an invalid gzip stream");
  }
  {
    std::string in(reinterpret_cast<const char*>(kXzSample), sizeof(kXzSample));
    std::string out;
    const bool ok = iptvsimple::utilities::FileUtils::XzDecompress(in, out);
    Check(ok && out == "pvr.iptvsimple xz round-trip\n",
          "XzDecompress() decodes an xz stream through the liblzma path");
  }
  {
    std::string in("not-an-xz-stream");
    std::string out;
    iptvsimple::utilities::FileUtils::XzDecompress(in, out);
    Check(out.empty(), "XzDecompress() yields no data for an invalid xz stream");
  }
  {
    const std::string combined =
        iptvsimple::utilities::FileUtils::PathCombine("/userdata/addon_data", "playlist.m3u");
    Check(combined == "/userdata/addon_data/playlist.m3u",
          "PathCombine() builds a POSIX path");
  }

  dlclose(handle);

  if (g_failures != 0)
  {
    std::fprintf(stderr, "%d assertion(s) failed\n", g_failures);
    return 1;
  }
  std::printf("all kodi-pvr-iptvsimple consumer assertions passed\n");
  return 0;
}
