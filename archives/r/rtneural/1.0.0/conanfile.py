#!/usr/bin/env python3
"""Conan recipe for RTNeural 1.0.0 — real-time neural network inference
(header-only C++ library, STL backend).

Header-only: package just copies the RTNeural/ header tree. The STL
backend needs no Eigen/xsimd, so there are no extra requires.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class RTNeuralConan(ConanFile):
    name = "rtneural"
    version = "1.0.0"
    description = "Real-time neural network inference library (header-only, STL backend)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/jatinchowdhury18/RTNeural"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "header-library"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def package(self):
        # Copy the header tree (RTNeural/ dir) into include/
        src_hdr = os.path.join(self.source_folder, "RTNeural")
        if not os.path.isdir(src_hdr):
            raise ConanException(f"RTNeural headers missing: {src_hdr}")
        dst_hdr = os.path.join(self.package_folder, "include", "RTNeural")
        shutil.copytree(src_hdr, dst_hdr)
        # model_loader.h does `#include "../modules/json/json.hpp"` — bundle
        # the upstream nlohmann json.hpp so the relative include resolves.
        src_json = os.path.join(self.source_folder, "modules", "json", "json.hpp")
        if os.path.isfile(src_json):
            dst_json = os.path.join(self.package_folder, "include", "modules",
                                    "json", "json.hpp")
            os.makedirs(os.path.dirname(dst_json), exist_ok=True)
            shutil.copy2(src_json, dst_json)
        # Verify key headers
        for h in ("RTNeural.h", "Layer.h", "Model.h"):
            if not os.path.isfile(os.path.join(dst_hdr, h)):
                raise ConanException(f"missing header: {h}")

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
