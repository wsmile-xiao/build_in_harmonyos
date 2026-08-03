#!/usr/bin/env python3
"""Conan recipe - hexagonrpcd 0.4.0 (Meson).

Daemon to communicate with Qualcomm DSPs via the FastRPC protocol.
Upstream: https://github.com/linux-msm/hexagonrpc (tag v0.4.0)
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

class HexagonrpcdConan(ConanFile):
    name = "hexagonrpcd"
    version = "0.4.0"
    description = "Daemon to communicate with Qualcomm DSPs via the FastRPC protocol"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/linux-msm/hexagonrpc"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.generate()
        self._inject_ar_ranlib()

    def _inject_ar_ranlib(self):
        """OHOS 工具链不提供裸 ar/ranlib，需将 llvm-ar/llvm-ranlib 注入 meson native 文件。"""
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = compiler_executables.get("ar")
        ranlib = compiler_executables.get("ranlib")
        if not ar:
            cc = compiler_executables.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(ranlib_candidate):
                        ranlib = ranlib_candidate
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if ar and os.path.isfile(native_file):
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()
            if "\nar =" not in content and "[binaries]" in content:
                insertion = "[binaries]\nar = '{}'\n".format(ar)
                if ranlib:
                    insertion += "ranlib = '{}'\n".format(ranlib)
                content = content.replace("[binaries]\n", insertion, 1)
                with open(native_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()
        # Upstream meson.build does not install the public headers;
        # copy include/libhexagonrpc into the package manually.
        hdr_src = os.path.join(self.source_folder, "include", "libhexagonrpc")
        hdr_dst = os.path.join(self.package_folder, "include", "libhexagonrpc")
        copy(self, "*.h", src=hdr_src, dst=hdr_dst, keep_path=False)
        copy(self, "*.def", src=os.path.join(hdr_src, "interfaces"),
             dst=os.path.join(hdr_dst, "interfaces"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["hexagonrpc"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
