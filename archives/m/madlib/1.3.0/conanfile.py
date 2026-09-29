"""MAdLib 1.3.0 (mesh adaptation) for OpenHarmony PC."""

import os
import re
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MAdLibConan(ConanFile):
    name = "madlib"
    version = "1.3.0"
    description = "MAdLib mesh adaptation library"
    license = "LGPL-3.0-or-later"
    homepage = "https://www.madlib.be/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def requirements(self):
        # The published LAPACK package also contains reference BLAS and the
        # static Flang runtime needed to consume these Fortran symbols.
        self.requires("lapack/3.12.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("MADLIB_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration(
                    "MADLIB_SOURCE_ARCHIVE must be a regular file"
                )
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--disable-shared",
                "--enable-static",
                "--enable-blas-lapack",
                "--with-blas-lapack-prefix="
                + self.dependencies["lapack"].package_folder,
                "--disable-gmsh",
                "--disable-mpi",
                "--disable-benchmarks",
                "--disable-moveIt",
            ]
        )
        tc.generate()
        AutotoolsDeps(self).generate()

    def _toolchain_triplet(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("c")
        if not compiler or not Path(compiler).is_file():
            raise ConanInvalidConfiguration("configured C compiler is unavailable")
        result = subprocess.run(
            [compiler, "-dumpmachine"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        triplet = result.stdout.strip()
        if not re.fullmatch(r"[A-Za-z0-9_.+-]+", triplet):
            raise ConanInvalidConfiguration("invalid compiler target triplet")
        return triplet

    def build(self):
        # Bundled configure/Makefile.in are sufficient; autoreconf is not
        # available on every target device and would change the source input.
        triplet = self._toolchain_triplet()
        env = Environment()
        env.define("TMPDIR", self.build_folder)
        with env.vars(self).apply():
            autotools = Autotools(self)
            autotools.configure(args=["--build=" + triplet, "--host=" + triplet])
            config = Path(self.build_folder, "MAdConfig.h")
            if not config.is_file():
                raise ConanInvalidConfiguration("configure omitted MAdConfig.h")
            defines = config.read_text(encoding="utf-8", errors="replace")
            for feature in ("HAVE_BLAS", "HAVE_LAPACK"):
                if not re.search(r"^#define " + feature + r" 1$", defines, re.M):
                    raise ConanInvalidConfiguration(
                        "requested linear-algebra dependency not enabled: " + feature
                    )
            # This target's TMPDIR is on HMDFS, which cannot create GNU
            # make's FIFO jobserver endpoint; use a single job.
            autotools.make(args=["-j1"])
            # No TESTS/check_PROGRAMS are registered by this release. Run
            # its upstream check target and separately exercise the public
            # initialization API from test_package.
            autotools.make(target="check", args=["-j1"])

    def package(self):
        Autotools(self).install()
        copy(
            self,
            "License.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        if not Path(self.package_folder, "lib", "libMAdLib.a").is_file():
            raise ConanInvalidConfiguration("static libMAdLib.a was not installed")
        if not Path(self.package_folder, "include", "MAdLib", "MAdLib.h").is_file():
            raise ConanInvalidConfiguration("public MAdLib.h was not installed")

    def package_info(self):
        self.cpp_info.libs = ["MAdLib"]
        # Automake installs all public headers under include/MAdLib, while
        # those headers refer to each other without the directory prefix.
        self.cpp_info.includedirs = ["include", "include/MAdLib"]
        self.cpp_info.set_property("cmake_file_name", "madlib")
        self.cpp_info.set_property("cmake_target_name", "madlib::madlib")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
