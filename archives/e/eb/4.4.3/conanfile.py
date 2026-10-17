#!/usr/bin/env python3
"""Autotools-based Conan recipe for EB Library 4.4.3."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class EbConan(ConanFile):
    name = "eb"
    version = "4.4.3"
    description = "C library and tools for accessing EB and EPWING CD-ROM books"
    license = "BSD-3-Clause"
    homepage = "https://www.mistys-internet.website/eb/index-en.html"
    url = "https://github.com/mistydemeo/eb"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("EB Library supports Linux and OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "zlib/1.3.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self, src_folder=".")
        # Several utility Makefiles only resolve <eb/...> headers when the
        # 2009 release is built in source.
        self.folders.build = "."

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="eb-4.4.3.tar.gz",
            strip_root=True,
        )

    def generate(self):
        AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--prefix=/",
                "--disable-shared",
                "--enable-static",
                "--disable-nls",
                "--enable-pthread",
                "--enable-ebnet",
                "--enable-ipv6",
                "--enable-samples",
            ]
        )

        if self.settings.os == "OHOS":
            # The 2009 config.guess does not recognize HarmonyOS. This is a
            # native build, so a compatible build tuple is sufficient.
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")

            bash = (
                os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash"
            )
            tc.configure_args.append(f"SHELL={bash}")

            tmpdir = os.path.expanduser("~/tmp/eb-conan")
            os.makedirs(tmpdir, exist_ok=True)
            env = Environment()
            env.define_path("TMPDIR", tmpdir)
            env.define_path("CONFIG_SHELL", bash)
            env.define_path("SHELL", bash)
            env.vars(self).save_script("eb_build_env")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

        # Upstream registers no Automake TESTS. The shipped initexit sample is
        # its executable API smoke test and requires no dictionary fixture.
        autotools.make(target="check", args=["-j1"])
        if can_run(self):
            sample = os.path.join(self.build_folder, "samples", "initexit")
            self.run(sample, env="conanbuild")

    def package(self):
        Autotools(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["eb"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = ["zlib::zlib"]
        self.cpp_info.set_property("cmake_file_name", "eb")
        self.cpp_info.set_property("cmake_target_name", "eb::eb")
        self.cpp_info.set_property("pkg_config_name", "eb")
