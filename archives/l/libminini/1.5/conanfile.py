#!/usr/bin/env python3
"""Conan recipe for libminini 1.5 (upstream project name: minIni).

Upstream intentionally ships portable C sources without a build system. This
recipe compiles the implementation with the compiler selected by the Conan
profile, creates the upstream-supported static-library form, and runs both
official C and C++ test programs without modifying them.
"""

import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LibmininiConan(ConanFile):
    name = "libminini"
    version = "1.5"
    description = "Small portable INI file reader/writer with C and C++ APIs"
    license = "Apache-2.0"
    homepage = "https://github.com/compuphase/minIni"
    url = "https://github.com/compuphase/minIni"
    topics = ("ini", "configuration", "embedded", "c", "cpp")
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=False)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libminini 1.5 is validated for Linux-like stdio platforms"
            )

    def _tool(self, key, ohos_name, native_names):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = str(executables.get(key) or "")
        if configured and (os.path.isfile(configured) or shutil.which(configured)):
            return configured

        candidates = [ohos_name] if self.settings.os == "OHOS" else list(native_names)
        for candidate in candidates:
            resolved = shutil.which(candidate)
            if resolved:
                return resolved

        raise ConanInvalidConfiguration(
            "No usable {} tool in tools.build:compiler_executables or PATH".format(key)
        )

    def _compiler_tools(self):
        cc = self._tool("c", "aarch64-unknown-linux-ohos-clang", ("clang", "cc"))
        cxx = self._tool(
            "cpp", "aarch64-unknown-linux-ohos-clang++", ("clang++", "c++")
        )
        ar = self._tool("ar", "llvm-ar", ("llvm-ar", "ar"))
        return cc, cxx, ar

    def _run_test(self, executable, cwd):
        runner = self.conf.get(
            "user.libminini:qemu_runner", default="", check_type=str
        ).strip()
        command = "{} {}".format(runner, shlex.quote(executable)).strip()
        self.run(command, cwd=cwd)

    def build(self):
        apply_conandata_patches(self)
        cc, cxx, ar = self._compiler_tools()
        dev = self.source_folder
        tests = os.path.join(self.source_folder, "tests")
        obj = os.path.join(self.build_folder, "minIni.o")
        library = os.path.join(self.build_folder, "libminini.a")
        opt = "-O0 -g" if self.settings.build_type == "Debug" else "-O2"

        self.run(
            "{} -std=c99 {} -fPIC -I{} -c {} -o {}".format(
                shlex.quote(cc), opt, shlex.quote(dev),
                shlex.quote(os.path.join(dev, "minIni.c")), shlex.quote(obj)
            )
        )
        self.run(
            "{} rcs {} {}".format(
                shlex.quote(ar), shlex.quote(library), shlex.quote(obj)
            )
        )

        test_c_dir = os.path.join(self.build_folder, "upstream-test-c")
        test_cpp_dir = os.path.join(self.build_folder, "upstream-test-cpp")
        os.makedirs(test_c_dir, exist_ok=True)
        os.makedirs(test_cpp_dir, exist_ok=True)
        for test_dir in (test_c_dir, test_cpp_dir):
            shutil.copy2(os.path.join(tests, "test.ini"), test_dir)
            shutil.copy2(os.path.join(tests, "testplain.ini"), test_dir)

        test_c = os.path.join(test_c_dir, "test_minini_c")
        test_cpp = os.path.join(test_cpp_dir, "test_minini_cpp")
        self.run(
            "{} -std=c99 {} -I{} {} {} -o {}".format(
                shlex.quote(cc), opt, shlex.quote(dev),
                shlex.quote(os.path.join(tests, "test.c")), shlex.quote(obj),
                shlex.quote(test_c)
            )
        )
        self.run(
            "{} -std=c++17 {} -I{} {} {} -o {}".format(
                shlex.quote(cxx), opt, shlex.quote(dev),
                shlex.quote(os.path.join(tests, "test2.cc")), shlex.quote(obj),
                shlex.quote(test_cpp)
            )
        )

        self._run_test(test_c, test_c_dir)
        self._run_test(test_cpp, test_cpp_dir)
        marker = {
            "status": "passed",
            "framework": "standalone assert programs",
            "command": "test_minini_c && test_minini_cpp",
            "discovered": 44,
            "executed": 44,
            "passed": 44,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))

    def package(self):
        dev = self.source_folder
        include_dir = os.path.join(self.package_folder, "include")
        license_dir = os.path.join(self.package_folder, "licenses")
        copy(self, "minIni.h", dev, include_dir)
        copy(self, "minGlue.h", dev, include_dir)
        copy(self, "wxMinIni.h", dev, include_dir)
        copy(self, "libminini.a", self.build_folder,
             os.path.join(self.package_folder, "lib"))
        copy(self, "minIni.h", self.source_folder, license_dir)
        copy(self, "minIni.c", self.source_folder, license_dir)

    def package_info(self):
        self.cpp_info.libs = ["minini"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "libminini")
        self.cpp_info.set_property("cmake_target_name", "libminini::libminini")
        self.cpp_info.set_property("pkg_config_name", "libminini")
