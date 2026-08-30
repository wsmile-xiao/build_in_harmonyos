#!/usr/bin/env python3
"""Conan recipe for cbftp 1.0.0 — advanced multi-purpose FTP/FXP client.

Pure Makefile build (no configure). Produces three command-line tools:
  bin/cbftp          - ncurses-based FTP/FXP client (main binary)
  bin/datafilecat    - decrypts a cbftp data file (AES-256)
  bin/datafilewrite  - encrypts a plain text data file (AES-256)

Build deps (upstream README): make g++ libssl-dev libncursesw5-dev.
On OHOS these map to the openssl and ncurses conan packages. The wide-char
ncurses flavour (libncursesw) is required because the UI renders unicode;
the Makefile falls back to -lncurses on non-Debian systems, so we pass
LINKFLAGS explicitly with -lncursesw.

Adaptation notes:
  - CC/CXX/AR/RANLIB are taken from the Conan toolchain conf (R33).
  - openssl/ncurses include+lib dirs are fed via CXXFLAGS/CFLAGS/LINKFLAGS
    from conan dependencies.
  - The Makefile rule for datafilecat/datafilewrite originally used only
    $(STATIC_SSL_INCLUDE)/$(SSL_LINKFLAGS); we changed them to use the
    unified $(CXXFLAGS)/$(LINKFLAGS) so dependency flags propagate (patch).
  - The OHOS lld needs the SDK llvm/lib in LD_LIBRARY_PATH to load libxml2.
"""

import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CbftpConan(ConanFile):
    name = "cbftp"
    version = "1.0.0"
    description = "Advanced multi-purpose FTP/FXP client with a ncurses interface"
    license = "MIT"
    homepage = "https://cbftp.glftpd.io/"
    url = "https://github.com/cbftp/cbftp-svn"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1.1")
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)
        # cbftp builds in-source (Makefile writes src/*.o and bin/)
        self.folders.build = "."

    def source(self):
        # The codeload URL does not end in .tar.gz, so conan cannot infer the
        # archive format and would try zip -> BadZipFile. Give an explicit
        # filename so get() selects the tar.gz decompressor.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="cbftp-1.0.0.tar.gz")

    def _get_toolchain(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"
        return cc, cxx, ar, ranlib

    def _dep_flags(self, dep_name):
        """Return (cflags, ldflags) for a conan dependency."""
        try:
            dep = self.dependencies[dep_name]
            incdirs = dep.cpp_info.includedirs
            libdirs = dep.cpp_info.libdirs
        except Exception as exc:  # pragma: no cover - defensive
            self.output.warning(
                f"_dep_flags: cannot read cpp_info for '{dep_name}' ({exc})")
            return "", ""
        cflags = " ".join(f"-I{d}" for d in incdirs) if incdirs else ""
        ldflags = " ".join(f"-L{d}" for d in libdirs) if libdirs else ""
        return cflags, ldflags

    def _sdk_llvm_lib(self):
        """Locate the OHOS SDK llvm/lib directory dynamically.

        Prefer $OHOS_SDK_LLVM_ROOT, otherwise scan /data/service/hnp/ohos-sdk.org
        for the newest SDK and use its llvm/lib (avoids hardcoding a version).
        Returns the directory or "" if not found.
        """
        env_root = os.environ.get("OHOS_SDK_LLVM_ROOT")
        if env_root and os.path.isdir(env_root):
            return env_root
        base = "/data/service/hnp/ohos-sdk.org"
        if not os.path.isdir(base):
            return ""
        for entry in sorted(os.listdir(base), reverse=True):
            llvm_lib = os.path.join(base, entry, "ohos", "native", "llvm", "lib")
            if os.path.isdir(llvm_lib):
                return llvm_lib
        return ""

    def build(self):
        apply_conandata_patches(self)

        cc, cxx, ar, ranlib = self._get_toolchain()

        # Dependency include/lib dirs
        ssl_cflags, ssl_ldflags = self._dep_flags("openssl")
        ncurses_cflags, ncurses_ldflags = self._dep_flags("ncurses")

        # Optimization level follows build_type (R33: no hardcoded -O2).
        opt = "-O2" if str(self.settings.build_type) == "Release" else "-O0 -g"
        cxxflags = " ".join(filter(None, [
            opt, "-std=c++11", ssl_cflags, ncurses_cflags]))
        cflags = " ".join(filter(None, [
            opt, ssl_cflags, ncurses_cflags]))
        # ncurses package only ships the wide-char library (libncursesw.a)
        linkflags = " ".join(filter(None, [
            ssl_ldflags, ncurses_ldflags,
            "-lssl", "-lcrypto", "-lpthread", "-lncursesw"]))

        # The OHOS lld needs the SDK llvm/lib to locate libxml2 at link time.
        ld_library_path = ""
        if self.settings.os in ("Linux", "OHOS"):
            sdk_llvm_lib = self._sdk_llvm_lib()
            if sdk_llvm_lib:
                ld_library_path = (f"LD_LIBRARY_PATH={sdk_llvm_lib}"
                                   ":$LD_LIBRARY_PATH ")
            else:
                self.output.warning(
                    "OHOS SDK llvm/lib not found; lld may fail to load libxml2")

        make_prefix = (f"{ld_library_path}CC={cc} CXX={cxx} AR={ar} RANLIB={ranlib} "
                       f"CXXFLAGS=\"{cxxflags}\" CFLAGS=\"{cflags}\" "
                       f"LINKFLAGS=\"{linkflags}\"")

        self.run(f"cd {self.source_folder} && {make_prefix} make -j1")
        # Ensure all three tools are present
        for tool in ("cbftp", "datafilecat", "datafilewrite"):
            if not os.path.exists(os.path.join(self.source_folder, "bin", tool)):
                raise Exception(f"cbftp build did not produce bin/{tool}")

    def package(self):
        src_bin = os.path.join(self.source_folder, "bin")
        dst_bin = os.path.join(self.package_folder, "bin")
        copy(self, "cbftp", src_bin, dst_bin)
        copy(self, "datafilecat", src_bin, dst_bin)
        copy(self, "datafilewrite", src_bin, dst_bin)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
