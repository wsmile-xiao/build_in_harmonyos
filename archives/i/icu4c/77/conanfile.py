#!/usr/bin/env python3
"""Conan recipe for icu4c 77."""
import hashlib
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    chdir,
    copy,
    export_conandata_patches,
    get,
    mkdir,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Icu4cConan(ConanFile):
    name = "icu4c"
    version = "77"
    description = "International Components for Unicode"
    license = "Unicode-3.0"
    homepage = "https://icu.unicode.org/"
    url = ""
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        target_os = str(self.settings.os)
        if target_os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if target_os == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds currently support armv8 only")
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "icu4c is static-only to avoid collisions with system ICU libraries"
            )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    @property
    def _source_subdir(self):
        return os.path.join(self.source_folder, "source")

    @property
    def _autotools_build_dir(self):
        build_key = hashlib.sha256(
            os.path.abspath(self.build_folder).encode("utf-8")
        ).hexdigest()[:16]
        return os.path.join(
            os.path.expanduser("~"),
            "tmp",
            f"icu4c-{build_key}",
        )

    def _prepare_autotools_env(self):
        tmpdir = os.path.join(self._autotools_build_dir, "tmp")
        mkdir(self, tmpdir)
        os.environ["TMPDIR"] = tmpdir

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "")
        bindir = os.path.dirname(cc) if os.path.isabs(cc) else ""
        gawk = os.path.join(bindir, "gawk") if bindir else ""
        awk = (
            gawk if gawk and os.path.exists(gawk)
            else shutil.which("gawk") or shutil.which("awk")
        )
        if not awk:
            raise ConanInvalidConfiguration("ICU requires an awk implementation")
        os.environ["AWK"] = awk
        os.environ["ac_cv_prog_AWK"] = awk
        return awk

    def generate(self):
        awk = self._prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"AWK={awk}",
            f"ac_cv_prog_AWK={awk}",
            "--disable-samples",
            "--enable-tests",
            "--disable-extras",
            "--disable-layout",
            "--disable-layoutex",
            "--disable-shared",
            "--enable-static",
            "--with-data-packaging=static",
        ])
        if str(self.settings.os) == "OHOS":
            # The competition worker builds and runs natively on OHOS armv8.
            # Keeping build and host identical prevents ICU from entering its
            # external cross-build-tools mode while preserving OHOS detection.
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])
        tc.generate()

    def build(self):
        rmdir(self, self._autotools_build_dir)
        mkdir(self, self._autotools_build_dir)
        self._prepare_autotools_env()
        autotools = Autotools(self)
        with chdir(self, self._autotools_build_dir):
            autotools.configure(build_script_folder=self._source_subdir)
            autotools.make(args=["-j1"])
            autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        with chdir(self, self._autotools_build_dir):
            autotools.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["icui18n", "icuuc", "icudata"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.set_property("pkg_config_name", "icu-uc")
        self.cpp_info.set_property("cmake_file_name", "icu4c")
        self.cpp_info.set_property("cmake_target_name", "icu4c::icu4c")
        self.cpp_info.system_libs = ["m", "pthread"]
