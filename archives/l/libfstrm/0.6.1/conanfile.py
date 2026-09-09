#!/usr/bin/env python3
"""Conan recipe — libfstrm 0.6.1 (farsightsec/fstrm).

Frame Streams data transport protocol C library for HarmonyOS PC.
The upstream tag archive ships no generated `configure` (GitHub archive
tarballs are git-tree snapshots), so build() bootstraps it with
`autoreconf` via the Autotools helper — same approach as the merged
argp-standalone 1.5.0 recipe.

OHOS/HMDFS adaptations:
  - autoreconf bootstrap when configure is absent (GitHub archive);
  - generated configure is patched to drop `umask 077` from the
    config.status temp-dir creation (E011/E114: HMDFS turns a 0700 temp
    dir into an unwritable drwx--S--- dir) — after autoreconf, since the
    bootstrap regenerates configure;
  - make runs with -j1 (E074: HMDFS jobserver fifo EPERM);
  - the library itself is dependency-free; fstrm_capture/replay/dump
    reference programs need libevent>=2 on the host.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import collect_libs, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibfstrmConan(ConanFile):
    name = "libfstrm"
    version = "0.6.1"
    description = "Frame Streams data transport protocol library (fstrm)"
    license = "MIT"
    homepage = "https://github.com/farsightsec/fstrm"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        # Only configure.ac ships in the GitHub archive: must bootstrap with
        # autoreconf; device lacks automake/libtool, so pull them in.
        # tool_requires use the **build profile**, so -pr:h and -pr:b must
        # both be passed to conan create.  autoconf 2.72 comes from the
        # system (argp-standalone precedent; avoids a conan perl toolchain).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libfstrm is only supported on Linux/OHOS, not " +
                str(self.settings.os))

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: system-name library — default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS",
        # kernel "HongMeng Kernel") and fails with "cannot guess build type".
        # Pass the triplet explicitly (config.sub supports *-linux-ohos) so
        # configure never runs the config.guess probe (abiword-plugin
        # precedent).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # fstrm_capture/replay/dump reference programs require libevent >= 2
        # (PKG_CHECK_MODULES in configure.ac); the libfstrm library itself is
        # dependency-free, so disable the optional programs to keep the recipe
        # self-contained (upstream supports --disable-programs).
        tc.configure_args.append("--disable-programs")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # GitHub archive tarballs never contain configure (it is an
        # autoreconf artifact, not committed); bootstrap when absent.
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            autotools.autoreconf()
        # E011/E114: drop umask 077 from the generated configure (HMDFS) —
        # must happen **after** autoreconf, which regenerates configure.
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"),
                              recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = collect_libs(self) or ["libfstrm"]
        self.cpp_info.set_property("cmake_file_name", "libfstrm")
        self.cpp_info.set_property("cmake_target_name", "libfstrm::libfstrm")
