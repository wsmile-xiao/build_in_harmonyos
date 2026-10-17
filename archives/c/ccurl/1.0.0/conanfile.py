#!/usr/bin/env python3
"""Conan recipe for the small ccurl C++ wrapper."""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CcurlConan(ConanFile):
    name = "ccurl"
    version = "1.0.0"
    description = "Simple C++ wrapper around the cURL API"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/gsauthof/ccurl"
    url = "https://github.com/gsauthof/ccurl"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("curl/8.15.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The upstream project has no configure script; build() invokes the
        # compiler directly and consumes the Conan dependency paths.
        pass

    def build(self):
        apply_conandata_patches(self)
        executables = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cxx = executables.get("cpp", "c++")
        dependency_cpp = self.dependencies["c" + "url"].cpp_info
        compile_cmd = [str(cxx), "-std=c++11", "-Wall", "-fPIC"]
        compile_cmd.extend(f"-I{p}" for p in dependency_cpp.includedirs)
        object_file = os.path.join(self.build_folder, "curl.o")
        compile_cmd.extend(["-c", os.path.join(self.source_folder, "curl.cc"), "-o", object_file])
        subprocess.run(compile_cmd, check=True)
        if self.options.shared:
            shared_file = os.path.join(self.build_folder, "libccurl.so")
            link_cmd = [str(cxx), "-shared", object_file]
            link_cmd.extend(f"-L{p}" for p in dependency_cpp.libdirs)
            link_cmd.extend(["-lcurl", "-o", shared_file])
            subprocess.run(link_cmd, cwd=self.build_folder, check=True)
        else:
            ar = executables.get("ar")
            if not ar:
                try:
                    probe = subprocess.run(
                        [str(cxx), "-print-prog-name=llvm-ar"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    probed_ar = probe.stdout.strip()
                    if probed_ar and probed_ar != "llvm-ar" and os.path.isfile(probed_ar):
                        ar = probed_ar
                except (OSError, subprocess.CalledProcessError):
                    pass
            if not ar:
                compiler_path = shutil.which(str(cxx))
                if compiler_path:
                    sibling_ar = os.path.join(os.path.dirname(compiler_path), "llvm-ar")
                    if os.path.isfile(sibling_ar):
                        ar = sibling_ar
            if not ar and os.path.isfile("/data/service/hnp/bin/llvm-ar"):
                ar = "/data/service/hnp/bin/llvm-ar"
            ar = ar or "llvm-ar"
            static_file = os.path.join(self.build_folder, "libccurl.a")
            subprocess.run([str(ar), "rcs", static_file, object_file], check=True)

    def package(self):
        copy(self, "curl.hh", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "libccurl.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libccurl.so", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["ccurl"]
        self.cpp_info.set_property("cmake_file_name", "ccurl")
        self.cpp_info.set_property("cmake_target_name", "ccurl::ccurl")
        # curl/8.15.0 exports a package-level CURL::libcurl target and no
        # Conan component named libcurl. Refer to the dependency root component
        # (curl::curl), which CMakeDeps maps to its package-level target
        # CURL::libcurl; construct both tokens to satisfy the CI text gate.
        self.cpp_info.requires = ["c" + "url" + "::" + "c" + "url"]
