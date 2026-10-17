#!/usr/bin/env python3
"""Conan recipe for luvit 2.18.1.1 on OpenHarmony PC.

Luvit is a Lua application/module tree for the external luvi runtime. The
upstream Makefile builds self-contained binaries by downloading lit and luvi,
but neither luvi nor lit is available as an OHPCD Conan package today. This
recipe therefore packages the official Lua resources and entry points without
fabricating a luvi binary.
"""
import json
import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class LuvitConan(ConanFile):
    name = "luvit"
    version = "2.18.1.1"
    description = "Node.js-style Lua APIs for the luvi runtime"
    license = "Apache-2.0"
    homepage = "https://luvit.io/"
    url = "https://github.com/luvit/luvit"
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Lua sources are architecture-independent; luvi is an external runtime.
        pass

    def package(self):
        share_dir = os.path.join(self.package_folder, "share", "luvit")
        copy(self, "*.lua", src=self.source_folder, dst=share_dir)
        copy(self, "*.lua", src=os.path.join(self.source_folder, "deps"), dst=os.path.join(share_dir, "deps"), keep_path=True)
        copy(self, "*", src=os.path.join(self.source_folder, "tests"), dst=os.path.join(share_dir, "tests"), keep_path=True)
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.markdown", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "luvit"))
        copy(self, "ChangeLog", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "luvit"))
        copy(self, "package.lua", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "luvit"))
        self._write_asset_manifest(share_dir)

    def _write_asset_manifest(self, share_dir):
        manifest_path = os.path.join(share_dir, ".luvit-assets.json")
        assets = []
        for dirpath, _dirnames, filenames in os.walk(share_dir):
            for name in sorted(filenames):
                full_path = os.path.join(dirpath, name)
                rel_path = os.path.relpath(full_path, share_dir).replace(os.sep, "/")
                if rel_path == ".luvit-assets.json":
                    continue
                assets.append({"path": rel_path, "size": os.path.getsize(full_path)})
        assets.sort(key=lambda item: item["path"])
        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(assets, handle, ensure_ascii=False, indent=2)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = [os.path.join("share", "luvit")]
