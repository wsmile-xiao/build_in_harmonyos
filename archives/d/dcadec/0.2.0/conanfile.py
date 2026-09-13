#!/usr/bin/env python3
"""Conan recipe for dcadec 0.2.0 on HarmonyOS/OpenHarmony."""

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
    save,
)
from conan.tools.layout import basic_layout


class DcadecConan(ConanFile):
    name = "dcadec"
    version = "0.2.0"
    description = "DTS Coherent Acoustics decoder library and command-line tool"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/foo86/dcadec"
    url = "https://github.com/foo86/dcadec"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(
            self,
            **self.conan_data["test_samples"],
            destination=os.path.join(self.source_folder, "test", "samples"),
            strip_root=True,
        )

    def _checksum_compat(self):
        """Return a sha1sum wrapper compatible with the OHOS check parser."""
        checksum = shutil.which("sha1sum") or shutil.which("shasum")
        if not checksum:
            raise ConanInvalidConfiguration("sha1sum or shasum is required")

        wrapper = os.path.join(self.build_folder, "sha1sum-compat")
        script = """#!/bin/sh
set -eu

real_checksum={checksum}

if [ "$#" -eq 2 ] && [ "$1" = "-c" ]; then
    failed=0
    while IFS= read -r checksum_line || [ -n "$checksum_line" ]; do
        case "$checksum_line" in
            ''|'#'*) continue ;;
        esac
        expected=${{checksum_line%% *}}
        filename=${{checksum_line#* }}
        filename=$(printf '%s\n' "$filename" | sed 's/^[* ]//')
        actual_line=$("$real_checksum" "$filename") || {{
            printf '%s: FAILED\n' "$filename"
            failed=1
            continue
        }}
        actual=${{actual_line%% *}}
        if [ "$actual" = "$expected" ]; then
            printf '%s: OK\n' "$filename"
        else
            printf '%s: FAILED\n' "$filename"
            failed=1
        fi
    done < "$2"
    exit "$failed"
fi

exec "$real_checksum" "$@"
""".format(checksum=shlex.quote(checksum))
        save(self, wrapper, script)
        os.chmod(wrapper, 0o755)
        return wrapper

    def build(self):
        apply_conandata_patches(self)
        work_source = os.path.join(self.build_folder, "source")
        shutil.copytree(self.source_folder, work_source, dirs_exist_ok=True)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or shutil.which("clang") or shutil.which("cc")
        if not cc:
            raise ConanInvalidConfiguration("A C compiler is required")
        ar = compilers.get("ar")
        if not ar:
            ar = os.path.join(os.path.dirname(cc), "llvm-ar")
        if not os.path.isfile(ar):
            ar = shutil.which("llvm-ar") or shutil.which("ar")
        if not ar:
            raise ConanInvalidConfiguration("llvm-ar or ar is required")

        cflags = [
            "-std=gnu99",
            "-D_FILE_OFFSET_BITS=64",
            "-DNDEBUG",
            "-Wall",
            "-Wextra",
            "-O3",
            "-ffast-math",
            "-g",
            "-MMD",
        ]
        if self.options.get_safe("fPIC", False):
            cflags.append("-fPIC")
        variables = [
            "CC={}".format(shlex.quote(cc)),
            "AR={}".format(shlex.quote(ar)),
            "CFLAGS={}".format(shlex.quote(" ".join(cflags))),
        ]
        if self.options.shared:
            variables.append("CONFIG_SHARED=1")

        make = "make -j{} {}".format(
            max(1, min(4, os.cpu_count() or 1)), " ".join(variables)
        )
        self.run(make + " all", cwd=work_source)
        checksum_compat = self._checksum_compat()
        self.run(
            "SHA1SUM={} make {} check".format(
                shlex.quote(checksum_compat), " ".join(variables)
            ),
            cwd=work_source,
        )

    def package(self):
        work_source = os.path.join(self.build_folder, "source")
        copy(
            self,
            "COPYING.LGPLv2.1",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )
        for header in (
            "dca_context.h",
            "dca_frame.h",
            "dca_stream.h",
            "dca_waveout.h",
        ):
            copy(
                self,
                header,
                os.path.join(self.source_folder, "libdcadec"),
                os.path.join(self.package_folder, "include", "libdcadec"),
            )
        copy(self, "dcadec", work_source, os.path.join(self.package_folder, "bin"))

        source_lib = os.path.join(work_source, "libdcadec")
        package_lib = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            copy(self, "libdcadec.so.0.1.0", source_lib, package_lib)
            for name in ("libdcadec.so.0", "libdcadec.so"):
                shutil.copy2(
                    os.path.join(package_lib, "libdcadec.so.0.1.0"),
                    os.path.join(package_lib, name),
                )
        else:
            copy(self, "libdcadec.a", source_lib, package_lib)

        pc = """prefix=${pcfiledir}/../..
exec_prefix=${prefix}
libdir=${prefix}/lib
includedir=${prefix}/include

Name: dcadec
Description: DTS Coherent Acoustics decoder library
Version: 0.2.0
Libs: -L${libdir} -ldcadec -lm
Cflags: -I${includedir}
"""
        save(self, os.path.join(package_lib, "pkgconfig", "dcadec.pc"), pc)

    def package_info(self):
        self.cpp_info.libs = ["dcadec"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "dcadec")
        self.cpp_info.set_property("cmake_target_name", "dcadec::dcadec")
        self.cpp_info.set_property("pkg_config_name", "dcadec")
        if self.options.shared:
            self.cpp_info.defines.append("DCADEC_SHARED")
