#!/usr/bin/env python3
"""Conan recipe for clipnotify 1.0.2 — X11 clipboard event notification tool.

Upstream is a single C file whose Makefile hardcodes /usr/X11R6 paths;
this recipe compiles the same one-liner directly against the conan X11
dependency packages instead (R36: no host X11 on CI workers/device).
E549: the produced ELF is self-signed with binary-sign-tool
(cc-connect/watchexec precedent) before packaging.  OHOS has no X server —
the consumer test executes the signed ELF and asserts the deterministic
no-X error path (exit 1 + "Can't open X display").
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class ClipnotifyConan(ConanFile):
    name = "clipnotify"
    version = "1.0.2"
    description = "X11 clipboard event notification tool"
    license = "Unlicense"
    homepage = "https://github.com/cdown/clipnotify"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # X11 头文件/库全部来自制品仓 conan 包（xclip 0.13.1 同款依赖组合）
        self.requires("libx11/6.4.0")
        self.requires("libxfixes/6.1.0")
        self.requires("xorgproto/2025.1")

    def layout(self):
        basic_layout(self)

    def generate(self):
        # conanbuild 环境提供 $CC/$CFLAGS/$LDFLAGS（R33：不依赖 shell 预置变量）
        AutotoolsToolchain(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── E549 ELF 签名（cc-connect 同款实现） ──────────────────────

    def _find_tool(self, name):
        import glob as g
        for d in sorted(g.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin")):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
        for d in ("/data/service/hnp/bin",):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
        return shutil.which(name)

    def _sign_elf(self, binary_path):
        from conan.errors import ConanException
        objcopy = self._find_tool("llvm-objcopy")
        sign_tool = self._find_tool("binary-sign-tool")
        if not sign_tool or not objcopy:
            raise ConanException("binary-sign-tool/llvm-objcopy not found (E549)")
        import subprocess
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", binary_path],
            capture_output=True, timeout=30,
        )
        tmp = binary_path + ".signed.tmp"
        for _ in range(3):
            r = subprocess.run(
                [sign_tool, "sign", "-inFile", binary_path,
                 "-outFile", tmp, "-selfSign", "1"],
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode == 0 and os.path.isfile(tmp):
                shutil.move(tmp, binary_path)
                os.chmod(binary_path, 0o775)
                return
        if os.path.exists(tmp):
            os.remove(tmp)
        from conan.errors import ConanException
        raise ConanException(f"signing failed for {binary_path}")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        dep_incs = " ".join(
            f"-I{os.path.join(dep.package_folder, inc)}"
            for dep in self.dependencies.host.values()
            for inc in dep.cpp_info.includedirs
        )
        dep_libs = " ".join(
            f"-L{os.path.join(dep.package_folder, libdir)}"
            for dep in self.dependencies.host.values()
            for libdir in dep.cpp_info.libdirs
        )
        out = os.path.join(self.build_folder, "clipnotify")
        # 上游 Makefile 同一编译式，仅替换其硬编码的 /usr/X11R6 路径
        self.run(
            f'$CC {dep_incs} "{src}/clipnotify.c" -o "{out}" {dep_libs} -lX11 -lXfixes',
            env="conanbuild",
        )
        self._sign_elf(out)

    def package(self):
        copy(self, "clipnotify",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
