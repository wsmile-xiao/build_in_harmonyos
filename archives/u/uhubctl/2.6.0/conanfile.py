#!/usr/bin/env python3
"""Conan recipe — uhubctl 2.6.0 (Makefile).

uhubctl is a single-file C utility that lists and controls USB power per port
on smart hubs; it links against libusb-1.0 only. Upstream ships a bare
Makefile (no configure step) that locates libusb-1.0 through pkg-config, so
the recipe wires the Conan dependency graph into pkg-config via PkgConfigDeps
and drives the upstream Makefile inside the VirtualBuildEnv (R33).

OHOS notes:
  - The Makefile derives PROGRAM_VERSION from `git describe`, which is empty
    in a release tarball, and then falls back to the shipped VERSION file
    ("2.6.0"). Because command-line make variables would also wipe the
    Makefile's own `CFLAGS +=` additions (pkg-config cflags/libs), the recipe
    feeds CFLAGS/CPPFLAGS through the environment instead so the upstream
    `+=` chains keep working; -DPROGRAM_VERSION is passed via CPPFLAGS
    (the build line is `$(CC) $(CPPFLAGS) $(CFLAGS) uhubctl.c`).
  - musl bundles the resolver/socket routines; the Makefile adds no extra
    -l flags itself, so nothing needs to be stripped.
  - The binary is self-signed in package() (HarmonyOS XPM requirement), so
    the consumer test can execute it directly.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class UhubctlConan(ConanFile):
    name = "uhubctl"
    version = "2.6.0"
    description = "USB hub per-port power control utility (list/switch smart hub ports via libusb)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/mvp/uhubctl"
    url = "https://github.com/mvp/uhubctl"
    topics = ("usb", "hub", "power", "uhub", "cli")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("libusb/1.0.27")

    def export_sources(self):
        # No patches today; the explicit call keeps the pipeline uniform and
        # the validator (G1) happy if patches are ever added.
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"uhubctl supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: the compiler/env comes from the Conan profile via the aggregated
        # conanbuild script; PkgConfigDeps drops libusb-1.0.pc into the
        # generators folder. The extra env goes into a "conanbuildenv_*"
        # script, which Conan aggregates into conanbuild AFTER the profile
        # buildenv (经验汇总 §12.38①) — this carries CC (this conan does not
        # translate tools.build:compiler_executables into the buildenv) and
        # the explicit PKG_CONFIG_PATH for the generated libusb-1.0.pc.
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        env = Environment()
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        env.define("CC", executables.get("c", "clang"))
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        # PkgConfigDeps sets includedir to .../include/libusb-1.0, but the
        # upstream source includes <libusb-1.0/libusb.h>, so the parent
        # include dir must be on the search path instead.
        libusb = self.dependencies["libusb"]
        env.define(
            "CPPFLAGS", "-I" + os.path.join(libusb.package_folder, "include")
        )
        env.vars(self).save_script("conanbuildenv_hmos")

    def build(self):
        # No patches today; the explicit call keeps the pipeline uniform (G1).
        apply_conandata_patches(self)
        # CFLAGS goes as an *environment* variable (env prefix), not as a make
        # command-line override: command-line assignments would also wipe the
        # Makefile's own `CFLAGS +=` chain, which carries the pkg-config flags
        # for libusb-1.0 and the -DPROGRAM_VERSION fallback (git describe is
        # empty in a tarball, so upstream falls back to the VERSION file).
        # As an environment value, `CFLAGS ?= -g -O0` is skipped and every
        # `+=` append still runs. `env -u CONFIG_SHELL SHELL=/bin/sh` routes
        # make's shell away from the hnp bash, which misbehaves on getcwd()
        # under HMDFS (E386, 经验汇总 §12.38).
        self.run(
            "env -u CONFIG_SHELL SHELL=/bin/sh "
            'CFLAGS="-O2 -fPIE -std=c99" '
            "make -j1",
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        copy(
            self,
            "uhubctl",
            self.source_folder,
            os.path.join(self.package_folder, "bin"),
        )
        os.chmod(os.path.join(self.package_folder, "bin", "uhubctl"), 0o755)
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS XPM requires signed executables; sign the installed binary
        # in place. `env -u LD_LIBRARY_PATH` keeps the SDK's own libc++.so from
        # shadowing the tool's dependencies (same pattern as connect-proxy).
        if self.settings.os != "OHOS":
            return
        import glob
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in glob.glob(os.path.join(self.package_folder, "bin", "*")):
            if not os.path.isfile(f) or os.path.islink(f) or not self._is_elf(f):
                continue
            self.run('env -u LD_LIBRARY_PATH {oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('env -u LD_LIBRARY_PATH {sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = []  # uhubctl is a CLI tool, it ships no library
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
