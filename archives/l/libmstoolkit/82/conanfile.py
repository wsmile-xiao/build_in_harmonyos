#!/usr/bin/env python3
"""Conan recipe for MSToolkit rev82.

The upstream Makefile hard-codes host compilers and builds bundled, obsolete
copies of Expat, SQLite, and zlib. This recipe compiles the exact MSToolkit and
mzParser source census with the Conan profile compiler, while using released
Conan packages for those three external libraries.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LibmstoolkitConan(ConanFile):
    name = "libmstoolkit"
    version = "82"
    description = "C++ toolkit for reading, writing, and manipulating mass spectrometry data"
    license = "Apache-2.0 AND BSD-2-Clause AND Artistic-1.0-Perl AND Zlib"
    homepage = "https://github.com/mhoopmann/mstoolkit"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    _mzparser_sources = (
        "MSNumpress.cpp",
        "mzp_base64.cpp",
        "BasicSpectrum.cpp",
        "mzParser.cpp",
        "RAMPface.cpp",
        "saxhandler.cpp",
        "saxmzmlhandler.cpp",
        "saxmzxmlhandler.cpp",
        "Czran.cpp",
        "mz5handler.cpp",
        "mzpMz5Config.cpp",
        "mzpMz5Structs.cpp",
        "BasicChromatogram.cpp",
        "PWIZface.cpp",
    )
    _mstoolkit_sources = (
        "Spectrum.cpp",
        "MSObject.cpp",
        "mzMLWriter.cpp",
        "pepXMLWriter.cpp",
        "MSReader.cpp",
    )
    _public_headers = (
        "MSNumpress.hpp",
        "MSObject.h",
        "MSReader.h",
        "MSToolkitTypes.h",
        "RAWReader.h",
        "Spectrum.h",
        "mzMLWriter.h",
        "mzParser.h",
        "pepXMLWriter.h",
    )

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "*.txt",
            src=os.path.join(self.recipe_folder, "licenses"),
            dst=os.path.join(self.export_sources_folder, "licenses"),
        )

    def requirements(self):
        self.requires("expat/2.8.2.1.1", transitive_headers=True)
        self.requires("sqlite3/3.49.1", transitive_headers=True)
        self.requires("zlib/1.3.2", transitive_headers=True)

    def validate(self):
        if str(self.settings.os) not in ("OHOS", "Linux", "Macos"):
            raise ConanInvalidConfiguration(
                "libmstoolkit is supported on OHOS, Linux, and Macos"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _tool(self, key, fallbacks):
        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        candidate = str(configured.get(key) or "").strip()
        if candidate:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
            if os.sep not in candidate and shutil.which(candidate):
                return shutil.which(candidate)
            raise ConanInvalidConfiguration(
                "configured {} tool is unavailable: {}".format(key, candidate)
            )
        for fallback in fallbacks:
            resolved = shutil.which(fallback)
            if resolved:
                return resolved
        raise ConanInvalidConfiguration(
            "no usable {} tool found (tried {})".format(key, ", ".join(fallbacks))
        )

    def _run(self, arguments, cwd=None):
        env = os.environ.copy()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.update({"TMPDIR": tmpdir, "TMP": tmpdir, "TEMP": tmpdir})
        self.output.info("+ " + " ".join(arguments))
        process = subprocess.run(
            arguments,
            cwd=cwd or self.build_folder,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1200,
        )
        if process.stdout:
            self.output.info(process.stdout[-12000:])
        if process.returncode != 0:
            raise ConanException(
                "command failed with exit code {}: {}".format(
                    process.returncode, " ".join(arguments)
                )
            )

    def _dependency_include_flags(self):
        flags = []
        for name in ("expat", "sqlite3", "zlib"):
            info = self.dependencies[name].cpp_info.aggregated_components()
            for include_dir in info.includedirs:
                flag = "-I{}".format(include_dir)
                if flag not in flags:
                    flags.append(flag)
        return flags

    def _cppstd_flag(self):
        cppstd = str(self.settings.get_safe("compiler.cppstd") or "11")
        if cppstd.startswith("gnu"):
            return "-std=gnu++{}".format(cppstd[3:])
        return "-std=c++{}".format(cppstd)

    def build(self):
        cxx = self._tool("cpp", ("clang++", "c++"))
        ar = self._tool("ar", ("llvm-ar", "ar"))
        object_dir = os.path.join(self.build_folder, "objects")
        os.makedirs(object_dir, exist_ok=True)

        flags = [
            self._cppstd_flag(),
            "-fPIC",
            "-D_LARGEFILE_SOURCE",
            "-D_FILE_OFFSET_BITS=64",
            "-DGCC",
        ]
        if str(self.settings.build_type) == "Debug":
            flags.extend(("-O0", "-g"))
        else:
            flags.append("-O2")
        flags.extend(self._dependency_include_flags())
        flags.append("-I{}".format(os.path.join(self.source_folder, "include")))
        # The patched compatibility header preloads declared dependency headers
        # and scopes the one Clang diagnostic needed by this legacy source.
        flags.extend(("-include", "ohpcd_mstoolkit_compat.h"))

        sources = [
            os.path.join(self.source_folder, "src", "mzParser", name)
            for name in self._mzparser_sources
        ] + [
            os.path.join(self.source_folder, "src", "MSToolkit", name)
            for name in self._mstoolkit_sources
        ]
        objects = []
        for index, source in enumerate(sources):
            stem = os.path.splitext(os.path.basename(source))[0]
            obj = os.path.join(object_dir, "{:02d}_{}.o".format(index, stem))
            source_flags = list(flags)
            if os.path.basename(source) == "mzp_base64.cpp":
                source_flags.append("-Wno-register")
            self._run([cxx] + source_flags + ["-c", source, "-o", obj])
            objects.append(obj)

        library = os.path.join(self.build_folder, "libmstoolkit.a")
        self._run([ar, "rcs", library] + objects)

        upstream = {
            "status": "no_tests",
            "framework": "none",
            "command": "N/A (upstream rev82 has no test target or test suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "rev82 archive has no tests/test directory, no registered test "
                "framework, and its Makefile defines only all, lite, and clean"
            ),
        }
        marker = json.dumps(upstream, ensure_ascii=False)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + marker)
        with open(
            os.path.join(self.build_folder, "upstream_test_result.json"),
            "w",
            encoding="utf-8",
        ) as result_file:
            result_file.write(marker)

    def package(self):
        copy(
            self,
            "libmstoolkit.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        for header in self._public_headers:
            copy(
                self,
                header,
                src=os.path.join(self.source_folder, "include"),
                dst=os.path.join(self.package_folder, "include"),
                keep_path=False,
            )
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "*.txt",
            src=os.path.join(self.source_folder, "licenses"),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        notice_sources = (
            (os.path.join("src", "MSToolkit"), "MSReader.cpp"),
            ("include", "mzParser.h"),
            (os.path.join("src", "mzParser"), "saxhandler.cpp"),
            (os.path.join("src", "mzParser"), "saxmzmlhandler.cpp"),
            (os.path.join("src", "mzParser"), "saxmzxmlhandler.cpp"),
            (os.path.join("src", "mzParser"), "Czran.cpp"),
            ("include", "zlib.h"),
        )
        for source_dir, notice_file in notice_sources:
            copy(
                self,
                notice_file,
                src=os.path.join(self.source_folder, source_dir),
                dst=os.path.join(self.package_folder, "licenses", "notices"),
                keep_path=False,
            )
        copy(
            self,
            "upstream_test_result.json",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "res"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["mstoolkit"]
        self.cpp_info.defines = ["_LARGEFILE_SOURCE", "_FILE_OFFSET_BITS=64", "GCC"]
        self.cpp_info.requires = ["expat::expat", "sqlite3::sqlite3", "zlib::zlib"]
        if str(self.settings.os) in ("OHOS", "Linux"):
            self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "libmstoolkit")
        self.cpp_info.set_property(
            "cmake_target_name", "libmstoolkit::libmstoolkit"
        )
        self.cpp_info.set_property("pkg_config_name", "libmstoolkit")
