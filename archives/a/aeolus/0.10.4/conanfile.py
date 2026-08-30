#!/usr/bin/env python3
"""Conan recipe for aeolus 0.10.4 (Fons Adriaensen) — OHOS aarch64.

Pure-Makefile project (source/Makefile), no configure script. Builds the
`aeolus` JACK/ALSA organ synthesizer binary and the `aeolus_txt.so` text-mode
interface plugin. The `aeolus_x11.so` GUI plugin is NOT built: it needs the
X11/Xft/clxclient stack which is not available in the OHOS environment (see
notes.md for the technical evidence).

OHOS portability notes (see notes.md):
  - The upstream Makefile hardcodes `CXXFLAGS += -march=native`; the
    portability patch removes it so the toolchain from the Conan profile
    (tools.build:compiler_executables) controls code generation.
  - The install target now uses `$(INSTALL)` (default /bin/install, toybox)
    and drops the `ldconfig` call; plain `install`/`ldconfig` are not on the
    PATH on OpenHarmony.
  - The install target only builds/installs `aeolus` + `aeolus_txt.so`
    (the x11 plugin is skipped by design).
  - `aeolus_txt.so` additionally links `-lncursesw`: the published readline
    recipe builds static libs and its terminal-cursor symbols (tputs/tgetent
    ...) resolve to ncurses.
  - `LIBDIR` is fixed to `lib` when invoking make (the Makefile otherwise
    derives `lib$(SUFFIX)` from `uname -m`).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AeolusConan(ConanFile):
    name = "aeolus"
    version = "0.10.4"
    package_type = "application"
    description = "Aeolus — synthesised (i.e. not sampled) pipe organ emulator"
    license = "GPL-3.0-or-later"
    homepage = "https://kokkinizita.linuxaudio.org/linuxaudio/"
    url = "https://kokkinizita.linuxaudio.org/linuxaudio/"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("aeolus supports Linux and OHOS only")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("aeolus supports OHOS armv8 only")
        if not self.options.shared:
            raise ConanInvalidConfiguration("aeolus 0.10.4 only builds shared plugins")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zita-alsa-pcmi/0.6.1")
        self.requires("clthreads/2.4.0")
        self.requires("jack/1.9.22")
        self.requires("alsa-lib/1.2.16")
        self.requires("readline/8.3")
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_paths(self):
        """Return (include_flags, lib_flags) from all direct dependencies."""
        include_flags = []
        lib_flags = []
        for dep in ("zita-alsa-pcmi", "clthreads", "jack", "alsa-lib",
                    "readline", "ncurses"):
            pkg = self.dependencies[dep]
            include_flags.append("-I" + os.path.join(pkg.package_folder, "include"))
            lib_flags.append("-L" + os.path.join(pkg.package_folder, "lib"))
        return " ".join(include_flags), " ".join(lib_flags)

    def _sdk_llvm_lib_dir(self, cxx):
        """E132: OHOS SDK 的 lld 动态依赖 libxml2.so.16, 其 RUNPATH 使用
        $ORIGIN/../lib 但 musl ldso 不支持 $ORIGIN 扩展 (E019), 部分 CI
        worker 上因此无法加载 libxml2.so.16 导致链接失败. 返回 SDK
        llvm/lib 目录 (内含 libxml2.so.16), 供 build 注入 LD_LIBRARY_PATH.
        保持 lld 链接 — 不能改用 -fuse-ld=/data/service/hnp/bin/ld:
        GNU ld 链接出的二进制在 OHOS 沙箱中执行时报 Permission denied."""
        try:
            real = os.path.realpath(cxx)
        except OSError:
            return ""
        # .../llvm/bin/clang -> .../llvm/lib
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(real)), "lib")
        if os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
            return llvm_lib
        return ""

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler must come from the Conan profile conf, never a bare
        # shell ${CXX} (empty on CI/release workers).
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        include_flags, lib_flags = self._dep_paths()
        source_dir = os.path.join(self.source_folder, "source")
        # E132: lld 需要 libxml2.so.16, 注入 SDK llvm/lib 到 LD_LIBRARY_PATH.
        env_prefix = ""
        llvm_lib = self._sdk_llvm_lib_dir(cxx)
        if llvm_lib:
            env_prefix = 'export LD_LIBRARY_PATH="{}:${{LD_LIBRARY_PATH:-}}"; '.format(llvm_lib)
        # CPPFLAGS/LDFLAGS are exported through the environment so the
        # Makefile's own `+=` directives (e.g. target-specific `-shared`,
        # `-DVERSION=...`) still apply — passing them on the make command
        # line would override those `+=` appends.
        self.run(
            env_prefix +
            'CPPFLAGS="-DCLTHREADS_NO_PTHREAD_CANCEL {}" '
            'LDFLAGS="{}" '
            'make -C "{}" -j1 CXX="{}" LIBDIR=lib aeolus aeolus_txt.so'.format(
                include_flags, lib_flags, source_dir, cxx
            )
        )
        # Upstream ships no check/test target (`make check` fails with
        # "No rule to make target 'check'"); consumer-side verification is
        # done by test_package/ (runs `aeolus -h` and dlopens aeolus_txt.so).

    def package(self):
        source_dir = os.path.join(self.source_folder, "source")
        self.run(
            'make -C "{}" install PREFIX=/ BINDIR=bin LIBDIR=lib DESTDIR="{}"'.format(
                source_dir, self.package_folder
            )
        )

    def package_info(self):
        # Application package: consumers run the `aeolus` binary and/or
        # dlopen the `aeolus_txt.so` text-mode plugin.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "aeolus")
        self.cpp_info.set_property("cmake_target_name", "aeolus::aeolus")
