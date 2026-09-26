#!/usr/bin/env python3
"""Conan recipe for turnstile 0.1.11 — independent session/login tracker.

HarmonyOS PC adaptation:
- Meson build (turnstiled daemon + pam_turnstile PAM module + configs).
- Dependency: linux-pam/1.7.2 (provides pam/pam_misc pkg-config components).
- man pages disabled (-Dman=false) to avoid the scdoc build-time dependency
  (documentation only, not required for the daemon functionality).
- pam_moddir pinned to lib/security inside the package prefix (meson would
  otherwise derive it from the linux-pam .pc libdir, which points into the
  conan cache on OHOS).
- meson runs a C++ sanity-check probe (project is ['cpp','c']) whose binary
  links libc++_shared.so. The runtime loader only searches the profile
  LD_LIBRARY_PATH (llvm/lib, for libxml2), not the aarch64-linux-ohos
  subdir where libc++_shared.so lives, so the probe exits 127. Inject the
  SDK subdir via a generated env script in generate() (pattern proven in
  ast/2020.0.0) so it is aggregated into the conanbuild environment.
- CI worker PATH omits hnp/bin (no llvm-ar): meson configure fails with
  "Unknown linker(s): [['llvm-ar']]". Inject absolute llvm-ar/llvm-ranlib
  paths into the meson native file (pattern proven in linux-pam/1.7.2).
"""
import glob
import os
import re

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class TurnstileConan(ConanFile):
    name = "turnstile"
    version = "0.1.11"
    package_type = "application"
    description = "Independent session/login tracker (turnstiled daemon + PAM module)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/chimera-linux/turnstile"
    url = "https://github.com/chimera-linux/turnstile"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("linux-pam/1.7.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        # man pages need scdoc (build-time only, doc-only) — disable
        tc.project_options["man"] = "false"
        # pin PAM module dir inside the package (relative to prefix)
        tc.project_options["pam_moddir"] = "lib/security"
        tc.generate()
        self._inject_meson_archiver()

        # meson C++ sanity-check probe links libc++_shared.so from the SDK
        # llvm/lib/aarch64-linux-ohos dir; the shared profile only adds
        # llvm/lib (libxml2). Save an env script so the directory is part of
        # the aggregated conanbuild environment inherited by meson (and by the
        # probe subprocess). Pattern: archives/a/ast/2020.0.0; SDK root comes
        # from OHOS_SDK_ROOT (fallback to the default install prefix) and the
        # version segment is discovered via glob to stay valid across SDK
        # upgrades.
        if self.settings.os == "OHOS":
            sdk_root = os.environ.get(
                "OHOS_SDK_ROOT", "/data/service/hnp/ohos-sdk.org")
            sdk_libs = sorted(glob.glob(os.path.join(
                sdk_root, "*/ohos/native/llvm/lib/aarch64-linux-ohos")))
            if not sdk_libs:
                self.output.warning(
                    "turnstile: OHOS SDK libc++ dir not found under %s; "
                    "meson C++ sanity check may fail (LD_LIBRARY_PATH not "
                    "extended). Set OHOS_SDK_ROOT if the SDK lives "
                    "elsewhere." % sdk_root)
            else:
                env = Environment()
                for sdk_lib in sdk_libs:
                    env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
                env.vars(self).save_script("turnstile_sdk_lib")

    def _inject_meson_archiver(self):
        """注入 llvm-ar/llvm-ranlib 到 meson native 文件（linux-pam 1.7.2 先例）。

        CI worker PATH 不含 hnp/bin（实测 PATH=/data/app/bin:/system/bin:...），
        meson 配置阶段探测 llvm-ar 失败报 "Unknown linker(s): [['llvm-ar']]"。
        从 tools.build:compiler_executables 的 c/cpp 编译器目录推导 llvm-ar/llvm-ranlib
        绝对路径写入 conan_meson_native.ini [binaries]。

        W4 复检 P3 闭环：
        - P3-1: 无论 ar 来自 conf 显式配置还是目录派生，都从 ar 所在目录补齐 ranlib；
        - P3-2: native 文件已有裸名 ar 行时替换为绝对路径（不静默跳过），并告警；
        - P3-3: 本方法紧跟 generate() 定义（辅助方法紧随其调用方）。
        """
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar:
            compiler = executables.get("c") or executables.get("cpp") or ""
            bindir = os.path.dirname(compiler) if compiler and os.path.sep in compiler else ""
            candidate = os.path.join(bindir, "llvm-ar") if bindir else ""
            if candidate and os.path.isfile(candidate):
                ar = candidate
        # P3-1: 无论 ar 来源都从 ar 所在目录补齐 ranlib
        if ar and os.path.sep in ar:
            ar_bindir = os.path.dirname(ar)
            candidate_ranlib = os.path.join(ar_bindir, "llvm-ranlib")
            if not ranlib and os.path.isfile(candidate_ranlib):
                ranlib = candidate_ranlib
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not ar or not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "[binaries]" not in content:
            return
        # P3-2: 已有 ar 行（裸名）时替换为绝对路径，避免静默失效
        if re.search(r"^ar\s*=", content, re.M):
            self.output.warning(
                "turnstile: replacing bare 'ar = ...' with absolute "
                "llvm-ar path in conan_meson_native.ini")
            content = re.sub(r"^ar\s*=.*$", "ar = '%s'" % ar,
                             content, count=1, flags=re.M)
            if ranlib:
                if re.search(r"^ranlib\s*=", content, re.M):
                    content = re.sub(r"^ranlib\s*=.*$",
                                     "ranlib = '%s'" % ranlib,
                                     content, count=1, flags=re.M)
                else:
                    content = content.replace(
                        "[binaries]\n", "[binaries]\nranlib = '%s'\n" % ranlib, 1)
        else:
            binaries = "[binaries]\nar = '%s'\n" % ar
            if ranlib:
                binaries += "ranlib = '%s'\n" % ranlib
            content = content.replace("[binaries]\n", binaries, 1)
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()

    def package_info(self):
        # turnstile is an application: turnstiled daemon + PAM module.
        # No linkable library is produced when the default meson option
        # (library=disabled) is kept.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        bin_dir = os.path.join(self.package_folder, "bin")
        self.conf_info.define("user.turnstile:exe", os.path.join(bin_dir, "turnstiled"))
