#!/usr/bin/env python3
"""Conan recipe for libfakekey 0.3-git20170516 on HarmonyOS PC."""

import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    copy,
    export_conandata_patches,
    save,
)
from conan.tools.layout import basic_layout
from conan.tools.scm import Git


class LibfakekeyConan(ConanFile):
    name = "libfakekey"
    version = "0.3-git20170516"
    description = "X11 virtual keyboard event injection library"
    license = "LGPL-2.0-or-later"
    homepage = "https://git.yoctoproject.org/libfakekey/"
    url = "https://git.yoctoproject.org/libfakekey/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The public header exposes Xlib types and XTEST symbols, so both
        # dependencies are part of the consumer-facing interface.
        self.requires(
            "libx11/6.4.0",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libxtst/6.1.0",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libfakekey supports Linux and OHOS, not {self.settings.os}"
            )

    def source(self):
        source = self.conan_data["sources"]
        checkout = os.path.join(self.source_folder, "_git_source")
        os.makedirs(checkout, exist_ok=True)
        git = Git(self, checkout)
        git.clone(
            source["url"],
            target=".",
            args=["--branch", source["tag"], "--depth", "1"],
        )
        actual = subprocess.check_output(
            [
                "git",
                "-c",
                f"safe.directory={checkout}",
                "rev-parse",
                "HEAD",
            ],
            cwd=checkout,
            text=True,
        ).strip()
        if actual != source["commit"]:
            raise ConanException(
                f"Unexpected libfakekey source commit: {actual}; "
                f"expected {source['commit']}"
            )
        for item in os.listdir(checkout):
            if item == ".git":
                continue
            shutil.move(os.path.join(checkout, item), self.source_folder)
        shutil.rmtree(checkout)

    def build(self):
        os.makedirs(self.build_folder, exist_ok=True)

        compiler = self._tool("c", "clang")
        archiver = self._tool("ar", "llvm-ar")
        source_file = os.path.join(self.source_folder, "src", "libfakekey.c")
        object_file = os.path.join(self.build_folder, "libfakekey.o")

        # Upstream omitted string.h while using memset/strlen. Force-including
        # the standard header keeps the official source untouched and is
        # portable across Linux and HarmonyOS Clang.
        compile_flags = ["-std=gnu99", "-Wall", "-include", "string.h"]
        if str(self.settings.build_type) == "Debug":
            compile_flags.extend(["-O0", "-g"])
        else:
            compile_flags.append("-O2")
        if self.options.get_safe("fPIC"):
            compile_flags.append("-fPIC")
        compile_flags.extend(self._include_flags())

        self.run(
            " ".join(
                [shlex.quote(compiler), "-c", shlex.quote(source_file),
                 "-o", shlex.quote(object_file)] + compile_flags
            )
        )

        if self.options.shared:
            library = os.path.join(self.build_folder, "libfakekey.so.0.0.1")
            self.run(
                " ".join(
                    [
                        shlex.quote(compiler),
                        "-shared",
                        "-Wl,-soname,libfakekey.so.0",
                        "-o",
                        shlex.quote(library),
                        shlex.quote(object_file),
                    ]
                    + self._library_path_flags()
                    + ["-lXtst", "-lX11"]
                )
            )
            # Physical copies avoid HMDFS symlink replacement limitations.
            shutil.copy2(library, os.path.join(self.build_folder, "libfakekey.so.0"))
            shutil.copy2(library, os.path.join(self.build_folder, "libfakekey.so"))
        else:
            library = os.path.join(self.build_folder, "libfakekey.a")
            self.run(
                f"{shlex.quote(archiver)} rcs {shlex.quote(library)} "
                f"{shlex.quote(object_file)}"
            )

        # Upstream provides one integration test but does not register it in
        # automake TESTS. Compile that exact source here; execution requires a
        # live XTEST-capable display and is recorded separately in notes.md.
        upstream_test = os.path.join(self.build_folder, "fakekey-test")
        self.run(
            " ".join(
                [
                    shlex.quote(compiler),
                    shlex.quote(os.path.join(self.source_folder, "tests", "fakekey-test.c")),
                    "-o",
                    shlex.quote(upstream_test),
                    f"-I{shlex.quote(self.source_folder)}",
                    f"-L{shlex.quote(self.build_folder)}",
                    "-lfakekey",
                ]
                + self._include_flags()
                + self._library_path_flags()
                + ["-lXtst", "-lX11"]
            )
        )

    def package(self):
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "fakekey"),
            dst=os.path.join(self.package_folder, "include", "fakekey"),
        )
        if self.options.shared:
            copy(self, "libfakekey.so*", self.build_folder,
                 os.path.join(self.package_folder, "lib"), keep_path=False)
        else:
            copy(self, "libfakekey.a", self.build_folder,
                 os.path.join(self.package_folder, "lib"), keep_path=False)

        pc = """prefix=${pcfiledir}/../..
exec_prefix=${prefix}
libdir=${prefix}/lib
includedir=${prefix}/include

Name: libfakekey
Description: X Virtual Keyboard Library
Version: 0.3
Requires: x11, xtst
Libs: -L${libdir} -lfakekey
Cflags: -I${includedir}
"""
        save(
            self,
            os.path.join(self.package_folder, "lib", "pkgconfig", "libfakekey.pc"),
            pc,
        )

    def package_info(self):
        self.cpp_info.libs = ["fakekey"]
        self.cpp_info.set_property("cmake_file_name", "libfakekey")
        self.cpp_info.set_property(
            "cmake_target_name", "libfakekey::libfakekey"
        )
        self.cpp_info.set_property("pkg_config_name", "libfakekey")

    def _tool(self, key, fallback):
        configured = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        return configured.get(key, fallback)

    def _include_flags(self):
        flags = [f"-I{shlex.quote(self.source_folder)}"]
        seen = {self.source_folder}
        for dependency in self.dependencies.values():
            for include_dir in dependency.cpp_info.includedirs:
                if include_dir not in seen:
                    flags.append(f"-I{shlex.quote(include_dir)}")
                    seen.add(include_dir)
        return flags

    def _library_path_flags(self):
        flags = []
        seen = set()
        for dependency in self.dependencies.values():
            for library_dir in dependency.cpp_info.libdirs:
                if library_dir not in seen:
                    flags.append(f"-L{shlex.quote(library_dir)}")
                    seen.add(library_dir)
        return flags
