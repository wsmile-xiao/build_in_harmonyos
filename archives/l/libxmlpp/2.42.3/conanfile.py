#!/usr/bin/env python3
"""Conan recipe — libxml++ 2.42.3 (Meson) for HarmonyOS PC (OHOS, aarch64).

libxml++ is a C++ wrapper for the libxml2 XML parser. This recipe ships the
OLD 2.x API line (pc name `libxml++-2.6`) — the ONLY line that synfig 1.5.5
satisfies:
  synfig-core/src/CMakeLists.txt (v1.5.5):
    pkg_check_modules(XMLPP REQUIRED IMPORTED_TARGET libxml++-2.6)
  official docs (synfig-docs-dev.readthedocs.io building/dependencies.html)
  list libxml++-2.6. The 5.x recipe (work/libxml++/conanfile.py, 5.4.0,
  pc `libxml++-5.0`) is a NEW-API line and does NOT satisfy synfig.

OHOS adaptation:
  * glibmm dependency (2.x-line specific — NOT required by 5.x):
      libxml++ 2.x is built on glibmm-2.4 (Glib::ustring / Glib::RefPtr) and its
      meson.build probes dependency('glibmm-2.4', version: '>= 2.32.0').
      ⚠️ 版本裁决修正：glibmm 2.84.0 提供 glibmm-2.68.pc（需 sigc++-3.0），
      不是 glibmm-2.4.pc。glibmm 2.66.x 是最后提供 glibmm-2.4.pc 的 2.4 ABI 线。
      本配方 require **glibmm/2.66.9**（已发布 ohpcd，R36）。
  * libxml2: cmd-pkgs 系统包。本环境只有共享 libxml2.so（无静态 libxml2.a；
      E076 静态化前提在本环境不成立），经系统 libxml-2.0.pc 解析（shared）。
  * libxml++-2.6.so 非系统同名库，允许动态（R26 不适用）。
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain

# Options added at parse time by the mm-common meson module (import('mm-common')).
# libxml++ 2.x tarballs ship no meson_options.txt; these names are the
# standard mm-common set and are valid on the meson command line for every
# GNOME meson project using mm-common (glibmm 2.66 / libsigc++ 2.10.8 use the
# exact same names successfully).
MM_COMMON_OPTIONS = frozenset({
    "maintainer-mode", "build-documentation", "build-examples",
    "build-tests", "validation", "build-pdf",
})


class LibxmlppConan(ConanFile):
    # Conan 2 forbids '+' in package names -> use libxmlpp (same convention as
    # the 5.4.0 recipe and the synfig task). Software name stays libxml++.
    name = "libxmlpp"
    version = "2.42.3"
    description = "libxml++ 2.42.3 — C++ wrapper for libxml2 (OLD 2.6 API line, pc libxml++-2.6; required by synfig 1.5.5)"
    license = "LGPL-2.1-or-later"
    homepage = "https://libxmlplusplus.github.io/libxml++/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libxmlpp is only supported on Linux/OHOS, not %s" % self.settings.os)

    def requirements(self):
        # glibmm 2.66.9 = 最后提供 glibmm-2.4.pc / libglibmm-2.4.so 的 2.4 ABI 线。
        #   ⚠️ 修正 ADAPTATION.md 的错误前提：glibmm 2.84.0 提供 glibmm-2.68.pc
        #   （需要 sigc++-3.0），不是 glibmm-2.4.pc。libxml++ 2.42.3 的 meson.build
        #   探测 dependency('glibmm-2.4', version: '>= 2.32.0')，只能用 glibmm 2.66.x。
        #   glibmm/2.66.9 作为 synfig 依赖项随 PR 从源码构建（R36 fallback：
        #   L0i-1 从 archives 导出本地配方，无 channel 与制品仓其余依赖格式一致）。
        #   不带 user/channel，避免与 synfig 的无 channel 引用产生版本冲突。
        self.requires("glibmm/2.66.9")
        # libxml2 2.15.3 改 conan 依赖（ohpcd 有 libxml2/2.15.3 配方，pkg_config_name
        # = "libxml-2.0"，由 PkgConfigDeps 生成 libxml-2.0.pc）→ 不再依赖 cmd-pkgs
        # 系统 prefix（CI worker 无系统 libxml2，原系统依赖导致构建失败）。
        # 无 channel 与制品仓其余依赖格式一致，避免与 synfig 的无 channel 引用冲突。
        self.requires("libxml2/2.15.3")

    def layout(self):
        basic_layout(self, src_folder=".")

    def export_sources(self):
        # No local patches are shipped (conandata.yml patches: {}); this keeps
        # the framework's G1 recipe-completeness gate happy and is a no-op for
        # patch-less recipes (same pattern as glibmm/2.66.9).
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # ── generate ────────────────────────────────────────────────────────────
    def generate(self):
        # PkgConfigDeps 从 glibmm/2.66.9 与 libxml2/2.15.3 的 cpp_info 生成
        # glibmm-2.4.pc / giomm-2.4.pc / libxml-2.0.pc，使 meson 的
        # dependency('glibmm-2.4') / dependency('libxml-2.0') 可解析（R27/R36
        # 标准 Conan 依赖链；libxml2 已 conan 化，不再依赖 cmd-pkgs 系统 prefix）。
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # libxml++ 2.x 是 C++11 时代的代码库（头文件用 std::auto_ptr，C++17 已移除）。
        # meson.build 声明 cpp_std=c++11，但 profile 的 compiler.cppstd=17 会让
        # MesonToolchain 写 cpp_std='c++17' → 覆盖项目默认 → auto_ptr 编译失败。
        # 共享 profile 不能改，这里在 native file 的 [built-in options] 显式回退到 C++11。
        tc.cpp_std = "c++11"
        self._apply_declared_meson_options(tc)
        # pkg-config 查找顺序：generators（PkgConfigDeps 产物，含 libxml-2.0.pc）。
        pkgconfig_dirs = [self.generators_folder]
        env_pc = os.environ.get("PKG_CONFIG_PATH", "")
        if env_pc:
            pkgconfig_dirs += [d for d in env_pc.split(os.pathsep) if d]
        tc.pkg_config_path = os.pathsep.join(pkgconfig_dirs)
        tc.generate()
        self._inject_meson_archiver()

    def _apply_declared_meson_options(self, tc):
        """Set meson options that are actually declared by libxml++ 2.42.3.

        Passing an undeclared option makes meson setup fail hard. libxml++ 2.42.3
        ships meson_options.txt (maintainer-mode/warnings/build-*/validation/…);
        options there are picked up by the meson.options/meson_options.txt parse
        below. In addition, when import('mm-common') is found in meson.build we
        also trust the standard mm-common option names (glibmm 2.66 / libsigc++
        2.10.8 set them successfully). Built-in meson options (default_library,
        libdir, wrap_mode) are applied unconditionally — they are valid on every
        project regardless of declaration.
        """
        declared = set()
        for name in ("meson.options", "meson_options.txt"):
            path = os.path.join(self.source_folder, name)
            if os.path.isfile(path):
                with open(path, encoding="utf-8", errors="replace") as f:
                    for line in f:
                        m = re.match(r"\s*option\s*\(\s*['\"]([^'\"]+)['\"]", line)
                        if m:
                            declared.add(m.group(1))
        mb = os.path.join(self.source_folder, "meson.build")
        if os.path.isfile(mb):
            with open(mb, encoding="utf-8", errors="replace") as f:
                if "import('mm-common')" in f.read():
                    declared |= MM_COMMON_OPTIONS
        candidates = {
            # Tarball ships generated sources -> no mm-common regeneration.
            "maintainer-mode": "false",
            "build-documentation": "false",
            "build-examples": "false",
            "build-tests": "true",
            "validation": "false",
            "build-pdf": "false",
            "benchmark": "false",
        }
        # Built-in meson options are valid on EVERY project regardless of
        # declaration (glibmm/2.66.9 sets default_library the same way):
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Keep libdir explicit (aarch64 OHOS meson defaults to lib).
        tc.project_options["libdir"] = "lib"
        tc.project_options["wrap_mode"] = "nodownload"
        for opt, val in candidates.items():
            if opt in declared:
                tc.project_options[opt] = val

    def _inject_meson_archiver(self):
        """Write ar/ranlib full paths into the meson native file.

        MesonToolchain only maps the c/cpp entries of tools.build:compiler_executables,
        so meson probes the archiver by bare name (llvm-ar). The clang toolchain
        lives in /data/service/hnp/bin, not on PATH during conan create. Deriving
        the paths from the compiler keeps PATH untouched (same fix as glibmm).
        """
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar:
            compiler = executables.get("cpp") or executables.get("c") or ""
            bindir = os.path.dirname(compiler)
            candidate = os.path.join(bindir, "llvm-ar") if bindir else ""
            if candidate and os.path.isfile(candidate):
                ar = candidate
                candidate_ranlib = os.path.join(bindir, "llvm-ranlib")
                if os.path.isfile(candidate_ranlib):
                    ranlib = candidate_ranlib
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not ar or not os.path.isfile(native_file):
            return
        with open(native_file) as handle:
            content = handle.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        binaries = "[binaries]\nar = '%s'\n" % ar
        if ranlib:
            binaries += "ranlib = '%s'\n" % ranlib
        with open(native_file, "w") as handle:
            handle.write(content.replace("[binaries]\n", binaries, 1))

    # ── build / package ─────────────────────────────────────────────────────
    def build(self):
        # R33: no bare ${CC}/${CFLAGS} — the native file from MesonToolchain
        # carries compiler + flags; PKG_CONFIG_PATH comes from pkg_config_path.
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        self._run_meson(
            'meson setup --native-file "%s" "%s" "%s" --prefix=/'
            % (native_file, self.build_folder, self.source_folder)
        )
        self._run_meson('meson compile -C "%s"' % self.build_folder)
        # 上游官方测试（tests/meson.build 注册的 3 个 saxparser_* 测试，build-tests=true
        # 构建）：CI 门禁要求 build() 执行上游测试。交叉构建（build=Linux / host=OHOS）
        # 时构建机不能 exec aarch64 二进制 → 跳过；原生 OHOS/HarmonyOS 时执行 meson test。
        if cross_building(self):
            self.output.info(
                "cross-building: skip meson test (OHOS binaries not runnable on build host)"
            )
        else:
            # meson test 运行时注入全部依赖 libdir（尤其 glib 包内的 libintl.so.8）：
            # 否则 libglib-2.0.so.0 的 gettext 符号（g_libintl_*）无法解析 → exit 127
            # （CI 实测）。ld_path 与 glibmm test_package 同款。
            libs = []
            for _ref, dep in self.dependencies.items():
                if dep.package_folder:
                    libs.append(os.path.join(dep.package_folder, "lib"))
            ld_path = ":".join(dict.fromkeys(l for l in libs if l))
            self._run_meson(
                'LD_LIBRARY_PATH=%s meson test -C "%s" --print-errorlogs'
                % (ld_path, self.build_folder))

    def _run_meson(self, command):
        """Run a meson/ninja command with a PATH fallback for ninja (R33-safe:
        ninja is derived from PATH / compiler bindir, never from a bare NINJA
        shell variable — same pattern as glibmm/libsigc)."""
        ninja = shutil.which("ninja")
        if not ninja:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict) or {}
            compiler = executables.get("cpp") or executables.get("c") or ""
            candidate = os.path.join(os.path.dirname(compiler), "ninja")
            if compiler and os.path.isfile(candidate):
                ninja = candidate
        if not ninja:
            # profile buildenv PATH (setup.sh) may still expose it; last resort.
            ninja = "ninja"
        ninja_dir = os.path.dirname(ninja)
        if ninja_dir:
            self.run('PATH="%s:$PATH" NINJA="%s" %s' % (ninja_dir, ninja, command))
        else:
            self.run('NINJA="%s" %s' % (ninja, command))

    def package(self):
        self._run_meson(
            'meson install -C "%s" --destdir "%s"'
            % (self.build_folder, self.package_folder)
        )
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        """Native OHOS worker: meson install rewrote rpath, so the built .so
        needs re-codesign before dlopen/exec (E135 — HarmonyOS dynamic linker
        rejects unsigned .so). Same implementation as glibmm/2.66.9. Cross/SDK
        Docker env has no binary-sign-tool -> skip with a warning."""
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        candidates_objcopy = [
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "",
        ]
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            candidates_objcopy.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates_objcopy if p and os.path.isfile(p)), None)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool not found; skip OHOS codesign (cross/SDK env)")
            return
        for so in sos:
            if objcopy:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'
                         .format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'
                     .format(sg=signer, f=so))
            self.output.info("codesigned %s" % os.path.basename(so))

    def package_info(self):
        self.cpp_info.libs = ["xml++-2.6"]
        self.cpp_info.set_property("cmake_file_name", "libxmlpp")
        self.cpp_info.set_property("cmake_target_name", "libxmlpp::libxmlpp")
        # synfig 1.5.5 probes exactly this pc name:
        #   pkg_check_modules(XMLPP REQUIRED IMPORTED_TARGET libxml++-2.6)
        self.cpp_info.set_property("pkg_config_name", "libxml++-2.6")
        # Public headers live below include/libxml++-2.6; libxml++config.h is
        # installed below libdir (GNOME meson convention, same as glibmm).
        # Both candidate roots are exported so consumers resolve either layout.
        self.cpp_info.includedirs = [
            os.path.join("include", "libxml++-2.6"),
            os.path.join("lib", "libxml++-2.6", "include"),
        ]
