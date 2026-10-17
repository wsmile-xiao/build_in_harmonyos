#!/usr/bin/env python3
"""Conan recipe for WASI runtimes 25.0.0 on OpenHarmony PC.

This recipe packages the official WebAssembly/wasi-sdk 25 runtime assets:
the WASI sysroot and compiler-rt builtins archive. It intentionally does
not build the full wasi-sdk LLVM toolchain, which is distributed as a
separate large SDK artifact upstream.
"""
import json
import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class WasiRuntimesConan(ConanFile):
    name = "wasi-runtimes"
    version = "25.0.0"
    description = "WASI sysroot and compiler runtime assets from wasi-sdk 25"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://github.com/WebAssembly/wasi-sdk"
    url = "https://github.com/WebAssembly/wasi-sdk"

    settings = "os", "compiler", "build_type", "arch"

    def package_id(self):
        self.info.clear()

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["sysroot"], destination="sysroot", strip_root=True)
        get(self, **self.conan_data["sources"]["builtins"], destination="builtins", strip_root=True)

    def build(self):
        # Official runtime archives are already built by the wasi-sdk release.
        pass

    def package(self):
        sysroot_dst = os.path.join(self.package_folder, "share", "wasi-sysroot")
        copy(self, "*", src=os.path.join(self.source_folder, "sysroot"), dst=sysroot_dst, keep_path=True)
        copy(self, "*", src=os.path.join(self.source_folder, "builtins"), dst=os.path.join(sysroot_dst, "lib", "wasm32-wasi"), keep_path=True)
        self._write_asset_manifest(sysroot_dst)

    def _write_asset_manifest(self, root):
        manifest_path = os.path.join(root, ".wasi-assets.json")
        assets = []
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in sorted(filenames):
                full_path = os.path.join(dirpath, name)
                rel_path = os.path.relpath(full_path, root).replace(os.sep, "/")
                if rel_path == ".wasi-assets.json":
                    continue
                assets.append({"path": rel_path, "size": os.path.getsize(full_path)})
        assets.sort(key=lambda item: item["path"])
        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(assets, handle, ensure_ascii=False, indent=2)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = [os.path.join("share", "wasi-sysroot", "include")]
        self.cpp_info.libdirs = [os.path.join("share", "wasi-sysroot", "lib", "wasm32-wasi")]
        self.cpp_info.resdirs = [os.path.join("share", "wasi-sysroot")]
