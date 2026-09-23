#!/usr/bin/env python3
"""Conan recipe — libgzstream 1.5-git20171107.9a20658 (Makefile)."""

import glob
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


class LibgzstreamConan(ConanFile):
    name = "libgzstream"
    version = "1.5-git20171107.9a20658"
    description = "C++ iostream classes wrapping the zlib compression library"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/kanedo/gzstream"
    url = "https://github.com/kanedo/gzstream"

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "zlib/1.3.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            strip_root=True,
        )

    def _resolve_tool(self, key, fallbacks):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = str(executables.get(key) or "")
        if configured and os.path.isabs(configured):
            if os.path.isfile(configured) and os.access(configured, os.X_OK):
                return configured
            self.output.warning(
                "Configured {} tool is unavailable: {}; using PATH".format(
                    key, configured
                )
            )
        elif configured:
            resolved = shutil.which(configured)
            if resolved:
                return resolved
        for name in fallbacks:
            resolved = shutil.which(name)
            if resolved:
                return resolved
        raise ConanInvalidConfiguration(
            "Required build tool is unavailable: {}".format("/".join(fallbacks))
        )

    def _zlib_archive(self):
        zlib_info = self.dependencies["zlib"].cpp_info
        for libdir in zlib_info.libdirs:
            candidates = sorted(glob.glob(os.path.join(libdir, "libz.a")))
            if candidates:
                return candidates[0]
        raise ConanInvalidConfiguration("zlib dependency does not contain libz.a")

    def _compile(self, cxx, source, output, include_flags):
        optimization = "-O2" if str(self.settings.build_type) == "Release" else "-O0 -g"
        command = "{} -std=c++17 {} -fPIC {} -c {} -o {}".format(
            shlex.quote(cxx),
            optimization,
            include_flags,
            shlex.quote(source),
            shlex.quote(output),
        )
        self.run(command, cwd=self.build_folder)

    def build(self):
        apply_conandata_patches(self)
        os.makedirs(self.build_folder, exist_ok=True)
        cxx = self._resolve_tool("cpp", ("clang++", "c++"))
        ar = self._resolve_tool("ar", ("llvm-ar", "ar"))
        zlib_info = self.dependencies["zlib"].cpp_info
        zlib_archive = self._zlib_archive()

        include_flags = " ".join(
            "-I{}".format(shlex.quote(path)) for path in zlib_info.includedirs
        )
        # The upstream root contains an extensionless file named `version`.
        # `-I.` lets it shadow libc++'s <version>; -idirafter keeps angle-form
        # <gzstream.h> working while giving system C++ headers precedence.
        include_flags += " -idirafter {}".format(shlex.quote(self.source_folder))

        object_file = os.path.join(self.build_folder, "gzstream.o")
        library_file = os.path.join(self.build_folder, "libgzstream.a")
        self._compile(
            cxx,
            os.path.join(self.source_folder, "gzstream.C"),
            object_file,
            include_flags,
        )
        self.run(
            "{} rcs {} {}".format(
                shlex.quote(ar),
                shlex.quote(library_file),
                shlex.quote(object_file),
            ),
            cwd=self.build_folder,
        )

        test_binaries = {}
        for test_name in ("test_gzip", "test_gunzip"):
            test_object = os.path.join(self.build_folder, test_name + ".o")
            test_binary = os.path.join(self.build_folder, test_name)
            self._compile(
                cxx,
                os.path.join(self.source_folder, test_name + ".C"),
                test_object,
                include_flags,
            )
            self.run(
                "{} {} {} {} -o {}".format(
                    shlex.quote(cxx),
                    shlex.quote(test_object),
                    shlex.quote(library_file),
                    shlex.quote(zlib_archive),
                    shlex.quote(test_binary),
                ),
                cwd=self.build_folder,
            )
            test_binaries[test_name] = test_binary

        gzip = shutil.which("gzip")
        gunzip = shutil.which("gunzip")
        diff = shutil.which("diff")
        if not gzip or not gunzip or not diff:
            raise ConanInvalidConfiguration(
                "Upstream tests require gzip, gunzip, and diff"
            )

        fixture = os.path.join(self.source_folder, "COPYING.LIB")
        generated_gzip = os.path.join(self.build_folder, "generated.gz")
        generated_plain = os.path.join(self.build_folder, "generated.txt")
        external_gzip = os.path.join(self.build_folder, "external.gz")
        external_plain = os.path.join(self.build_folder, "external.txt")

        # Upstream case 1: test_gzip output must be readable by gunzip.
        self.run(
            "{} {} {}".format(
                shlex.quote(test_binaries["test_gzip"]),
                shlex.quote(fixture),
                shlex.quote(generated_gzip),
            ),
            cwd=self.build_folder,
        )
        self.run(
            "{} -c {} > {}".format(
                shlex.quote(gunzip),
                shlex.quote(generated_gzip),
                shlex.quote(generated_plain),
            ),
            cwd=self.build_folder,
        )
        self.run(
            "{} {} {}".format(
                shlex.quote(diff),
                shlex.quote(fixture),
                shlex.quote(generated_plain),
            ),
            cwd=self.build_folder,
        )

        # Upstream case 2: test_gunzip must read standard gzip output.
        self.run(
            "{} -c {} > {}".format(
                shlex.quote(gzip),
                shlex.quote(fixture),
                shlex.quote(external_gzip),
            ),
            cwd=self.build_folder,
        )
        self.run(
            "{} {} {}".format(
                shlex.quote(test_binaries["test_gunzip"]),
                shlex.quote(external_gzip),
                shlex.quote(external_plain),
            ),
            cwd=self.build_folder,
        )
        self.run(
            "{} {} {}".format(
                shlex.quote(diff),
                shlex.quote(fixture),
                shlex.quote(external_plain),
            ),
            cwd=self.build_folder,
        )

        result = {
            "status": "passed",
            "framework": "upstream-make-test",
            "command": "equivalent of make test",
            "discovered": 2,
            "executed": 2,
            "passed": 2,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, sort_keys=True)
        )

    def package(self):
        copy(
            self,
            "gzstream.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libgzstream.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "COPYING.LIB",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["gzstream"]
        self.cpp_info.set_property("cmake_file_name", "libgzstream")
        self.cpp_info.set_property(
            "cmake_target_name", "libgzstream::libgzstream"
        )
