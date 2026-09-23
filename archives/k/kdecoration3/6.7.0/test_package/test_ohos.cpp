#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <KDecoration3/Decoration>
#include <KDecoration3/DecorationThemeProvider>
#include <QCoreApplication>
#include <QString>

#include <dlfcn.h>

#include <cstdio>
#include <string>

#if !defined(__OHOS__)
#error "test_kdecoration3_ohos must be compiled by the HarmonyOS toolchain"
#endif

#if !defined(__aarch64__)
#error "HarmonyOS PC kdecoration3 package must target AArch64"
#endif

static_assert(sizeof(void *) == 8, "HarmonyOS PC must use a 64-bit ABI");
static_assert(__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__,
              "HarmonyOS PC AArch64 must use little-endian byte order");

namespace {

bool check(bool condition, const char *message) {
  if (!condition) {
    std::fprintf(stderr, "[ohos] FAIL: %s\n", message);
  }
  return condition;
}

std::string baseName(const char *path) {
  const std::string value = path == nullptr ? std::string() : path;
  const std::string::size_type separator = value.find_last_of('/');
  return separator == std::string::npos ? value : value.substr(separator + 1);
}

} // namespace

int main(int argc, char **argv) {
  QCoreApplication app(argc, argv);
  bool ok = true;

  // The HarmonyOS CMake adaptation supplies a usable SONAME for the public
  // library. Resolve an exported KDecoration3 object and verify that the
  // dynamic loader used that stable SONAME rather than a build-tree path.
  Dl_info publicLibrary = {};
  const int resolved = dladdr(
      static_cast<const void *>(&KDecoration3::Decoration::staticMetaObject),
      &publicLibrary);
  ok &= check(resolved != 0, "dladdr could not resolve KDecoration3");
  ok &= check(publicLibrary.dli_fbase != nullptr,
              "resolved KDecoration3 image has no base address");
  ok &= check(baseName(publicLibrary.dli_fname) == "libkdecorations3.so.6",
              "public library was not loaded through libkdecorations3.so.6");

  // libkdecorations3.so.6 has a patched, SONAME-based NEEDED entry for its
  // private sibling. RTLD_NOLOAD proves that dependency was already loaded
  // when the public library initialized; it does not load a missing library.
  void *privateLibrary =
      dlopen("libkdecorations3private.so.2", RTLD_NOW | RTLD_NOLOAD);
  ok &= check(privateLibrary != nullptr,
              "private sibling was not loaded through its SONAME");
  if (privateLibrary != nullptr) {
    dlclose(privateLibrary);
  }

  // Exercise non-inline exported KDecoration3 code with UTF-8 data on the
  // OHOS libc++/Qt runtime so this remains a real package consumer test.
  KDecoration3::DecorationThemeMetaData metadata;
  const QString visibleName = QStringLiteral("鸿蒙窗口装饰");
  metadata.setVisibleName(visibleName);
  ok &= check(metadata.visibleName() == visibleName,
              "UTF-8 theme metadata did not round-trip");

  const KDecoration3::BorderRadius radius(1.25, 2.5, 3.75, 5.0);
  ok &= check(radius.topLeft() == 1.25 && radius.topRight() == 2.5 &&
                  radius.bottomRight() == 3.75 && radius.bottomLeft() == 5.0,
              "BorderRadius values did not round-trip");

  std::printf("test_kdecoration3_ohos: %s\n", ok ? "PASS" : "FAIL");
  return ok ? 0 : 1;
}
