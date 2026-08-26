#!/usr/bin/env python3
"""Conan recipe for libudfread 1.2.0.

libudfread is VideoLAN's UDF filesystem access library. The upstream 1.2.0
release ships a Meson build system (meson.build + meson_options.txt) and has
no external dependencies beyond the C runtime + pthreads (handled by meson's
dependency('threads')). This recipe uses the upstream Meson as-is with zero
patches; the Conan MesonToolchain injects the OpenHarmony cross toolchain.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibudfreadConan(ConanFile):
    name = "libudfread"
    version = "1.2.0"
    description = "UDF filesystem access library (VideoLAN)"
    license = "LGPL-2.1-or-later"
    homepage = "https://code.videolan.org/videolan/libudfread"
    url = "https://download.videolan.org/pub/videolan/libudfread/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if bool(self.options.shared):
            self.options.rm_safe("fPIC")
        # Pure C library
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="libudfread-1.2.0.tar.xz",
            strip_root=True,
        )

    def generate(self):
        toolchain = MesonToolchain(self)
        # R26: system-name library defaults to static
        toolchain.project_options["default_library"] = (
            "shared" if bool(self.options.shared) else "static"
        )
        # No examples/docs (avoid extra targets; upstream default is off)
        toolchain.project_options["enable_examples"] = "false"
        toolchain.generate()
        self._inject_meson_archive_tools()

    def _inject_meson_archive_tools(self):
        """Fill the archive tool (ar/ranlib) into the meson machine file.

        The OHOS toolchain exports the C/C++ compiler via
        tools.build:compiler_executables, but the meson machine file Conan
        generates may leave `ar`/`ranlib` unset for the cross-build host.
        Without them `static_library` linking fails. Resolve the LLVM tools
        sitting next to the configured compiler.
        """
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        compiler = executables.get("c") or executables.get("cpp") or ""
        bindir = os.path.dirname(compiler) if compiler else ""
        suffix = ".exe" if os.name == "nt" else ""
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar and bindir:
            candidate = os.path.join(bindir, f"llvm-ar{suffix}")
            if os.path.isfile(candidate):
                ar = candidate
        if not ranlib and bindir:
            candidate = os.path.join(bindir, f"llvm-ranlib{suffix}")
            if os.path.isfile(candidate):
                ranlib = candidate

        machine_file = next(
            (
                os.path.join(self.generators_folder, filename)
                for filename in (
                    "conan_meson_cross.ini",
                    "conan_meson_native.ini",
                )
                if os.path.isfile(
                    os.path.join(self.generators_folder, filename)
                )
            ),
            None,
        )
        if not ar or not machine_file:
            return

        with open(machine_file, encoding="utf-8") as handle:
            content = handle.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        archive_tools = (
            "[binaries]\n"
            f"ar = '{ar.replace(os.sep, '/')}'\n"
        )
        if ranlib:
            archive_tools += (
                f"ranlib = '{ranlib.replace(os.sep, '/')}'\n"
            )
        with open(
            machine_file,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(
                content.replace("[binaries]\n", archive_tools, 1)
            )

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Upstream library target is named 'udfread' (see src/meson.build:
        # build_target('udfread', ...)); this recipe forces default_library=static
        # and packages libudfread.a (no .so is produced by this package)
        self.cpp_info.libs = ["udfread"]
        self.cpp_info.set_property("cmake_file_name", "libudfread")
        self.cpp_info.set_property(
            "cmake_target_name", "libudfread::libudfread"
        )
        self.cpp_info.set_property("pkg_config_name", "libudfread")
        # pthread is used for mutex locking (default_blockinput.c, udfread.c)
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
