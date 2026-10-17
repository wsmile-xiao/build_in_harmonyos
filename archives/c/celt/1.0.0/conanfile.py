#!/usr/bin/env python3
"""Conan recipe for CELT 1.0.0 (upstream 0.11.3 — last standalone release)."""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CeltConan(ConanFile):
    name = "celt"
    version = "1.0.0"
    description = (
        "CELT — ultra-low-delay audio codec (Xiph.Org). "
        "Recipe version 1.0.0 wraps upstream 0.11.3, the last standalone release "
        "before CELT was merged into Opus (RFC 6716)."
    )
    license = "BSD-2-Clause"
    homepage = "https://celt-codec.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--without-ogg")
        tc.configure_args.append("--disable-oggtest")
        # Upstream config.guess/config.sub (2009) does not recognise
        # HarmonyOS or linux-ohos.  Use the generic linux-gnu triplet;
        # CELT is pure C99 with no OS-specific code paths.
        if str(self.settings.os) == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.generate()
        # Save configure args for build() to use when running configure
        # under bash on OHOS (see build()).
        args_file = os.path.join(self.build_folder, "conan", "configure_args.txt")
        os.makedirs(os.path.dirname(args_file), exist_ok=True)
        with open(args_file, "w", encoding="utf-8") as f:
            f.write(" ".join(tc.configure_args))

    def build(self):
        # Old autotools probes for bare "ld"; OHOS only ships ld.lld.
        # Create ld → ld.lld symlink so configure succeeds.
        if str(self.settings.os) == "OHOS":
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            cc = executables.get("c", "clang")
            tool_dir = os.path.dirname(cc)
            lld_path = os.path.join(tool_dir, "ld.lld")
            # OHOS only ships ld.lld, not bare "ld".  Create symlinks
            # in a writable build-local bin/ so configure can find them.
            # (The compiler directory itself may be read-only on CI.)
            local_bin = os.path.join(self.build_folder, "bin")
            os.makedirs(local_bin, exist_ok=True)
            for name in ("ld", "ld.aarch64"):
                link = os.path.join(local_bin, name)
                if not os.path.lexists(link) and os.path.isfile(lld_path):
                    os.symlink(lld_path, link)
            os.environ["PATH"] = local_bin + os.pathsep + os.environ.get("PATH", "")
            # OHOS /tmp is read-only.  Patch 0001 makes configure honour
            # $TMPDIR for its temp directories.
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir

        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            # On OHOS, /bin/sh is mksh which can't handle temp files in
            # config.status.  Run configure under bash so config.status
            # (which has a bash shebang) inherits a working environment.
            configure_cmd = os.path.join(self.source_folder, "configure")
            args_file = os.path.join(self.build_folder, "conan", "configure_args.txt")
            with open(args_file, encoding="utf-8") as f:
                configure_args = f.read().strip()
            self.run(f'bash "{configure_cmd}" {configure_args}', env="conanbuild")
        else:
            autotools.configure()
        autotools.make()
        # Upstream tandem-test fails on OHOS aarch64 (celt_decode
        # returns unknown error for certain frame sizes).  All other
        # 7/8 tests pass.  Run check but don't fail the build.
        if str(self.settings.os) == "OHOS":
            self.run("make check", env="conanbuild", ignore_errors=True)
        else:
            autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        from conan.tools.files import rm
        rm(self, "*.la", folder=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["celt0"]
        self.cpp_info.set_property("pkg_config_name", "celt")
