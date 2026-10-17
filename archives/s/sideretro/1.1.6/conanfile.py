#!/usr/bin/env python3
"""Conan recipe — sideretro 1.1.6 (sideRETRO, Meson).

sideretro is a C pipeline for detecting Somatic Insertion of DE novo
RETROcopies. Meson build; the deliverable is the `sider` CLI (three
subcommands: process-sample, merge-call, make-vcf), statically linking an
internal libsider. Dependencies: htslib / sqlite3 / zlib, plus check
(optional, only for the upstream unit-test runner).
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class SideretroConan(ConanFile):
    name = "sideretro"
    version = "1.1.6"
    description = "sideRETRO — pipeline for detecting Somatic Insertion of DE novo RETROcopies"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/galantelab/sideRETRO"
    url = "https://github.com/galantelab/sideRETRO"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1", transitive_headers=True, transitive_libs=True)
        self.requires("sqlite3/3.49.1", transitive_headers=True, transitive_libs=True)
        self.requires("htslib/1.24-r0", transitive_headers=True, transitive_libs=True)
        # check is used only by the upstream unit-test runner (tests/), not by
        # libsider or the sider CLI itself; keep it a private dependency.
        self.requires("check/0.15.2", visible=False)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # Do not let Meson fall back to downloading wrap files:
        # dependencies are provided by Conan (pkg-config).
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_meson_tools()

    def build(self):
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            # Run the upstream unit tests (check framework; registered as a
            # single `test('all', ...)` in tests/meson.build). If libcheck is
            # absent for any reason Meson emits a warning and testing is
            # disabled — here check/0.15.2 is always injected.
            meson.test()

    def package(self):
        # IMPORTANT: do NOT use Meson.install() here. Meson's install step
        # rewrites the binary's RUNPATH (removes build rpath), which alters
        # the file after the linker filled .codesign — the OHOS sandbox then
        # refuses to exec the mismatched binary with EPERM
        # ("Operation not permitted"). Copy the build artifact verbatim so the
        # .codesign section stays valid; runtime deps are resolved via
        # LD_LIBRARY_PATH provided by the conanrun environment (test_package
        # runs with env="conanrun").
        bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        copy(self, "sider", src=os.path.join(self.build_folder, "src"),
             dst=bin_dst, keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # CLI tool: only bin/sider is shipped.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

    # ── helpers (patterns proven in accountsservice/polkit recipes) ────────

    def _sdk_llvm_root(self):
        """Return the OHOS SDK LLVM root (…/ohos/native/llvm), derived from the
        configured clang realpath so the recipe does not hard-code a specific
        SDK version directory. Falls back to the known default SDK layout when
        the clang path cannot be resolved (e.g. conf key missing)."""
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or ""
        if cc and os.path.sep in cc:
            real_cc = os.path.realpath(cc)
            # …/ohos/native/llvm/bin/clang -> llvm root is two levels up
            llvm_root = os.path.dirname(os.path.dirname(real_cc))
            if os.path.isdir(os.path.join(llvm_root, "bin")):
                return llvm_root
        default_root = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm"
        return default_root if os.path.isdir(default_root) else ""

    def _sdk_cxx_lib(self):
        """SDK libc++ runtime directory (lib/aarch64-linux-ohos/c++)."""
        llvm_root = self._sdk_llvm_root()
        if not llvm_root:
            return ""
        return os.path.join(llvm_root, "lib", "aarch64-linux-ohos", "c++")

    def _build_environment(self):
        environment = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        # ninja is a C++ binary on OHOS and needs libc++_shared.so at runtime;
        # meson probes `ninja --version` while discovering the backend and
        # fails (rc=127 "Error loading shared library libc++_shared.so") when
        # the SDK libc++ directory is not on LD_LIBRARY_PATH, which aborts
        # meson setup with "Could not detect Ninja v1.8.2 or newer".
        sdk_cxx_lib = self._sdk_cxx_lib()
        if sdk_cxx_lib and os.path.isdir(sdk_cxx_lib):
            environment.prepend_path("LD_LIBRARY_PATH", sdk_cxx_lib)
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                environment.prepend_path("PATH", bin_dir)
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        return environment

    def _inject_meson_tools(self):
        """Fill in ar / ranlib / pkg-config in the Meson machine files.

        MesonToolchain does not always emit these on OHOS (clang toolchain in
        /data/service/hnp/bin); Meson then falls back to 'ar' on PATH which
        does not exist. Inject llvm-ar / llvm-ranlib / pkg-config like the
        accountsservice recipe does.
        """
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or ""
        bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
        sdk_bin = os.path.join(self._sdk_llvm_root(), "bin") if self._sdk_llvm_root() else ""
        ar = compilers.get("ar")
        ranlib = compilers.get("ranlib")
        candidates = [sdk_bin, bindir, "/data/service/hnp/bin"]
        for directory in candidates:
            if not directory:
                continue
            if not ar:
                candidate = os.path.join(directory, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
            if not ranlib:
                candidate = os.path.join(directory, "llvm-ranlib")
                if os.path.isfile(candidate):
                    ranlib = candidate
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insert = []
            # 去重守卫用正则锚定行首（兼容行首无前置换行），避免
            # "\nar =" 字面量在 ar 位于文件首行时漏匹配导致重复注入
            if ar and not re.search(r"(^|\n)\s*ar\s*=", content):
                insert.append(f"ar = '{ar}'")
            if ranlib and not re.search(r"(^|\n)\s*ranlib\s*=", content):
                insert.append(f"ranlib = '{ranlib}'")
            if pkg_config and not re.search(r"(^|\n)\s*pkg-?config\s*=", content):
                insert.append(f"pkg-config = '{pkg_config}'")
            if insert:
                content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1)
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)