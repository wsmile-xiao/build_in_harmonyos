#!/usr/bin/env python3
"""Conan recipe — libigl 2.6.0 (header-only C++ geometry processing library)."""
import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LibiglConan(ConanFile):
    name = "libigl"
    version = "2.6.0"
    package_type = "header-library"

    description = "Simple header-only C++ geometry processing library"
    homepage = "https://libigl.github.io/"
    license = "MPL-2.0"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("eigen/3.4.0", transitive_headers=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        # HMBS readonly_tmp: conan get() may stage via /tmp (read-only erofs).
        # Prefer the injected writable chain, fall back to a source-local dir.
        # Only redirects the temp-file root; no test is skipped or removed.
        tmp = None
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            cand = os.environ.get(var, "")
            if cand and cand != "/tmp":
                tmp = cand
                break
        if tmp is None:
            try:
                tmp = os.path.join(self.base_source_folder, "tmp")
            except Exception:
                tmp = None
        if tmp:
            try:
                os.makedirs(tmp, exist_ok=True)
            except Exception:
                pass
            for key in ("TMPDIR", "TMP", "TEMP"):
                os.environ[key] = tmp
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        # Header-only: upstream headers live in include/igl/*.h with paired
        # *.cpp included via "#include *.cpp" (e.g. adjacency_list.h ->
        # adjacency_list.cpp when IGL_STATIC_LIBRARY is unset), so both
        # suffixes must be packaged. NOTE: pattern is relative to src, so
        # src must be the include/ dir itself, otherwise dst gains a doubled
        # include/include/ prefix and consumers fail with
        # "igl/adjacency_list.h file not found".
        for pattern in ("*.h", "*.cpp", "*.hpp"):
            copy(self, pattern,
                 src=os.path.join(self.source_folder, "include"),
                 dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE.*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "*", src=os.path.join(self.source_folder, "cmake"), dst=os.path.join(self.package_folder, "share", "libigl", "cmake"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libigl")
        self.cpp_info.set_property("cmake_target_name", "igl::core")
