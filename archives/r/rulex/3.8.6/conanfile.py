#!/usr/bin/env python3
"""Conan recipe — rulex 3.8.6 (Autotools)."""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RulexConan(ConanFile):
    name = "rulex"
    version = "3.8.6"
    description = "Russian pronunciation dictionary library and utilities"
    license = "GPL-2.0-or-later AND LGPL-2.1-or-later"
    homepage = "https://github.com/poretsky/rulex"
    url = "https://github.com/poretsky/rulex"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "berkeley-db5/5.3.28",
            transitive_headers=True,
            transitive_libs=True,
        )

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("autoconf-archive/2024.10.16")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rulex supports Linux and OHOS, not {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        db_root = self.dependencies["berkeley-db5"].package_folder
        linkage = "shared" if self.options.shared else "static"
        if str(self.settings.os) == "OHOS" and not cross_building(self):
            # Native HarmonyOS workers cannot execute config.guess probes from
            # every temporary directory, so provide the canonical tuple.
            tc.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-gnu",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )
        tc.configure_args.extend(
            [
                f"--with-libdb={db_root}",
                f"--enable-{linkage}",
                f"--disable-{'static' if self.options.shared else 'shared'}",
            ]
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        libtool_aclocal = os.path.join(
            self.dependencies.build["libtool"].package_folder,
            "share",
            "aclocal",
        )
        autotools.autoreconf(
            args=["-I", libtool_aclocal],
            build_script_folder=self.source_folder,
        )
        # Autoconf's config.status template creates ./confXXXXXX with umask
        # 077.  On HarmonyOS HMFS the directory owner can be remapped while
        # the setgid group is inherited, leaving the current process unable
        # to traverse the mode-0700 directory and create subs1.awk.  Avoid
        # owner-only permissions for these short-lived configure files.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "umask 077",
            "umask 022",
        )
        autotools.configure(build_script_folder=self.source_folder)
        autotools.make(args=["-j1"])

        upstream_data = os.path.join(self.source_folder, "data", "lexicon.test")
        with open(upstream_data, "rb") as stream:
            upstream_count = sum(1 for _ in stream)
        if upstream_count != 430015:
            raise ConanException(
                f"unexpected upstream test count: {upstream_count} (expected 430015)"
            )

        if str(self.settings.os) == "OHOS":
            # The libtool launcher calls pwd to locate .libs/lexholder. HMFS
            # can reject getcwd() in Conan's cache even though the directory
            # and executable are usable, so keep the official make test target
            # but have that target invoke the already-linked ELF directly.
            db = self.dependencies["berkeley-db5"]
            runtime_dirs = [os.path.join(self.build_folder, "src", ".libs")]
            for libdir in db.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(db.package_folder, libdir)
                runtime_dirs.append(libdir)
            runtime_path = os.pathsep.join(runtime_dirs)
            test_makefile = os.path.join(self.build_folder, "data", "Makefile")
            lexholder = os.path.join(
                self.build_folder, "src", ".libs", "lexholder"
            )
            replace_in_file(
                self,
                test_makefile,
                "\t../src/lexholder -v ",
                f'\tLD_LIBRARY_PATH="{runtime_path}:$$LD_LIBRARY_PATH" '
                f'"{lexholder}" -v ',
            )

        autotools.make(target="test", args=["-j1"])
        mismatch_dump = os.path.join(self.build_folder, "data", "lexicon.dump")
        if not os.path.isfile(mismatch_dump):
            raise ConanException("upstream test did not create lexicon.dump")
        if os.path.getsize(mismatch_dump) != 0:
            raise ConanException("upstream dictionary test reported mismatches")
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT: status=passed discovered=430015 "
            "executed=430015 passed=430015 failed=0 skipped=0"
        )

    def package(self):
        Autotools(self).install(args=["-j1"])
        copy(
            self,
            "LICENSE.*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "lexicon.test",
            src=os.path.join(self.source_folder, "data"),
            dst=os.path.join(self.package_folder, "res", "tests"),
        )
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for filename in os.listdir(libdir):
                if filename.endswith(".la"):
                    os.unlink(os.path.join(libdir, filename))

    def package_info(self):
        self.cpp_info.libs = ["rulexdb"]
        self.cpp_info.requires = ["berkeley-db5::berkeley-db5"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "rulex")
        self.cpp_info.set_property("cmake_target_name", "rulex::rulex")
        db = self.dependencies["berkeley-db5"]
        for libdir in db.cpp_info.libdirs:
            if not os.path.isabs(libdir):
                libdir = os.path.join(db.package_folder, libdir)
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", libdir)
