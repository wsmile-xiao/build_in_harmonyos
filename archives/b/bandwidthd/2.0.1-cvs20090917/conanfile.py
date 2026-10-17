#!/usr/bin/env python3
"""Conan recipe for bandwidthd 2.0.1-cvs20090917."""

from glob import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BandwidthdConan(ConanFile):
    name = "bandwidthd"
    version = "2.0.1-cvs20090917"
    description = "TCP/IP bandwidth monitor that generates HTML and PNG graphs"
    license = "GPL-2.0-or-later"
    homepage = "https://bandwidthd.sourceforge.net/"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"bandwidthd supports Linux and OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        self.requires("gd/2.3.3.2")
        self.requires("libpcap/1.10.6")
        self.requires("libpng/1.6.58.2")

    def build_requirements(self):
        # The recipe ships the reproducibly generated Autoconf bootstrap files
        # in patches/0004-0007. Do not run autoreconf in the OHOS build
        # context: its Perl XS dependency is installed under /storage and
        # hmmac rejects dlopen(Cwd.so) from that HMDFS path.
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4")

    @staticmethod
    def _autotools_arch(arch):
        return {"armv8": "aarch64", "x86_64": "x86_64"}.get(
            str(arch), str(arch)
        )

    def _build_triplet(self):
        settings_build = getattr(self, "settings_build", None)
        build_arch = self._autotools_arch(getattr(settings_build, "arch", "x86_64"))
        build_os = str(getattr(settings_build, "os", "Linux"))
        if build_os == "OHOS":
            # The current OHOS CI launcher supplies the OHOS profile for both
            # build and host. The compiler still emits an OHOS target binary,
            # but configure cannot execute it from the Conan HMDFS cache.
            # Use a distinct GNU build triplet to force Autoconf's
            # cross-compiling path; WSL/Linux build profiles use their real
            # build triplet below.
            return f"{build_arch}-unknown-linux-gnu"
        if build_os == "Linux":
            return f"{build_arch}-pc-linux-gnu"
        return f"{build_arch}-unknown-{build_os.lower()}"

    def _host_triplet(self):
        host_arch = self._autotools_arch(self.settings.arch)
        if self.settings.os == "OHOS":
            return f"{host_arch}-unknown-linux-ohos"
        if self.settings.os == "Linux":
            return f"{host_arch}-pc-linux-gnu"
        return f"{host_arch}-unknown-{str(self.settings.os).lower()}"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # The legacy Makefile.in has no VPATH or source-prefixed object rules.
        # Autotools.configure()/make() therefore must run where bandwidthd.c,
        # graph.c and the other source files live; otherwise GNU make cannot
        # resolve the first bandwidthd.o prerequisite in Conan's build folder.
        self.folders.build = self.folders.source

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # The 2009 source declares externally visible functions as plain
        # `inline`. Modern clang defaults to C99/C23 inline semantics and
        # otherwise drops the definitions, causing Credit/FindIp linker
        # failures. This flag preserves the upstream GNU89 contract without
        # changing source files.
        tc.extra_cflags.append("-fgnu89-inline")
        if self.settings.os == "OHOS":
            # The CI profile points CC/CXX at the generic OHOS SDK clang
            # binaries. Those drivers do not reliably infer the target from
            # their path, so an unqualified configure link probe can use the
            # build host defaults and fail before any project code is built.
            ohos_target = self._host_triplet()
            tc.extra_cflags.append(f"--target={ohos_target}")
            tc.extra_cxxflags.append(f"--target={ohos_target}")
            tc.extra_ldflags.append(f"--target={ohos_target}")
            # bandwidthd links directly through clang rather than libtool.
            # Keep the linker dynamic because the published OHOS libpng
            # binary provides libpng16.so but no static archive.
        tc.configure_args.extend(
            [
                # Avoid config.guess probing the restricted OHOS executor and
                # preserve the real build/host distinction in WSL cross builds.
                f"--build={self._build_triplet()}",
                f"--host={self._host_triplet()}",
                "--prefix=/",
                "--sysconfdir=/etc",
                "--localstatedir=/var",
                "--with-htdocs-dir=/var/bandwidthd/htdocs",
                "--with-log-dir=/var/bandwidthd",
                "--with-extension-dir=/var/bandwidthd/extensions",
            ]
        )
        if self.settings.os == "OHOS":
            # The SDK lld executable loads libxml2.so.16 from its sibling
            # llvm/lib directory. Discover the installed SDK version instead
            # of assuming one fixed worker image, and expose it to configure,
            # make, and package-time link probes.
            sdk_llvm_libdirs = sorted(
                glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"),
                reverse=True,
            )
            env = tc.environment()
            if sdk_llvm_libdirs:
                env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_libdirs[0])
            tc.generate(env=env)
        else:
            tc.generate()

    def build(self):
        apply_conandata_patches(self)

        for script in ("configure", "config.guess", "config.sub"):
            script_path = os.path.join(self.source_folder, script)
            if os.path.isfile(script_path):
                os.chmod(script_path, os.stat(script_path).st_mode | 0o111)

        autotools = Autotools(self)
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            raise ConanInvalidConfiguration(
                "bootstrap patch did not provide configure; refusing to run autoreconf "
                "in the OHOS build context"
            )

        if self.settings.os == "OHOS":
            # HMDFS does not provide a reliable getcwd() to the HNP bash used
            # by the worker profile. Autoconf re-executes itself through
            # CONFIG_SHELL, so override the profile shell after the generated
            # Conan environment has been loaded by self.run().
            configure_args = autotools._configure_args
            configure = os.path.join(self.source_folder, "configure")
            self.run(
                "export CONFIG_SHELL=/bin/sh SHELL=/bin/sh && "
                f"{configure} {configure_args}"
            )
        else:
            autotools.configure()
        # Makefile.in has a generation race for conf.tab.h/conf.l.o; serial
        # make is required for a reproducible clean build.
        autotools.make(args=["-j1"])
        self.output.info(
            "Upstream source has no check target; CLI behavior is verified by test_package."
        )

    def package(self):
        Autotools(self).install(args=["-j1"])

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
