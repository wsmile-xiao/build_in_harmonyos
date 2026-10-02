#!/usr/bin/env python3
"""Conan recipe for the Jool 4.1.14 userspace tools."""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class JoolToolsConan(ConanFile):
    name = "jool-tools"
    version = "4.1.14"
    description = "Jool SIIT/NAT64 userspace command-line tools"
    license = "GPL-2.0-only"
    homepage = "https://github.com/NICMx/Jool"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jool-tools supports Linux and OHOS, not {self.settings.os}")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("jool-tools on OHOS currently targets AArch64 only")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac: libnl-genl-3.0 >= 3.2.22; argp is absent from musl.
        self.requires("libnl/3.11.0")
        self.requires("argp-standalone/1.5.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        # Generate libnl-genl-3.0.pc from the libnl component metadata.
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

        # libnl's installed .la files embed libdir='//lib'. Libtool resolves
        # them ahead of the static archives and rejects that stale path during
        # Jool's nested .la link. Use a clean -L directory containing only the
        # dependency's .a files, so libtool treats -lnl-* as ordinary archives.
        import shutil
        libnl_lib = os.path.join(self.dependencies["libnl"].package_folder, "lib")
        nola_dir = os.path.join(self.generators_folder, "libnl-nola")
        os.makedirs(nola_dir, exist_ok=True)
        for filename in os.listdir(libnl_lib):
            if filename.endswith(".a"):
                shutil.copy2(os.path.join(libnl_lib, filename),
                              os.path.join(nola_dir, filename))
        for filename in os.listdir(self.generators_folder):
            if not filename.endswith(".pc"):
                continue
            path = os.path.join(self.generators_folder, filename)
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
            if "-lnl-" in content:
                content = content.replace('-L"${libdir}"', f'-L"{nola_dir}"')
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(content)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--with-xtables=no",  # optional iptables extension is outside this package
            "--with-bash-completion-dir=no",
            f"PKG_CONFIG_PATH={self.generators_folder}",
        ])

        if self.settings.os == "OHOS":
            # The bundled config.sub predates OHOS; a small compatibility patch
            # enables the canonical Linux OHOS target triplet. Conan supplies
            # the real build triplet when cross-building. The OHOS CI uses
            # matching build/host profiles, so explicitly name its native
            # AArch64 OHOS build triplet when Conan omits --build.
            tc.configure_args = [arg for arg in tc.configure_args
                                 if not arg.startswith("--host=")]
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
            if not any(arg.startswith("--build=") for arg in tc.configure_args):
                if self.settings_build.os != "OHOS" or self.settings_build.arch != "armv8":
                    raise ConanInvalidConfiguration(
                        "Unable to infer the OHOS build triplet from settings_build")
                tc.configure_args.append("--build=aarch64-unknown-linux-ohos")

        argp = self.dependencies["argp-standalone"]
        argp_root = getattr(argp, "package_folder", None)
        if not argp_root:
            raise ConanException("argp-standalone package_folder unavailable")
        cppflags = ["-I{}".format(os.path.join(argp_root, "include"))]
        if self.settings.os == "OHOS":
            # libnl's documented OHOS consumer workaround for musl/UAPI socket
            # header conflicts. Do not change Linux's native header selection.
            cppflags.extend(["-D_UAPI_LINUX_SOCKET_H", "-D__kernel_sa_family_t=ushort"])
        tc.configure_args.append("CPPFLAGS=" + " ".join(cppflags))
        tc.configure_args.append("LDFLAGS=-L{}".format(os.path.join(argp_root, "lib")))
        tc.generate()

    def build(self):
        if self.settings.os == "OHOS":
            # The release's config.sub does not know the OHOS triplet, and its
            # umask 077 temp directory is not writable on the CI's HMDFS mount.
            # Keep upstream's secure default unchanged for native Linux builds.
            apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # The release has no upstream TESTS/check_PROGRAMS; keep the upstream
        # Automake check target in the build log as an explicit zero-test check.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        # Stage only userspace tools, manuals, and license. No kernel modules or
        # xtables extension are included in this package.
        bindir = os.path.join(self.package_folder, "bin")
        for subdir, binary in (("nat64", "jool"), ("siit", "jool_siit"),
                               ("joold", "joold")):
            candidate = os.path.join(self.build_folder, "src", "usr", subdir, binary)
            if not os.path.isfile(candidate):
                candidate = os.path.join(self.source_folder, "src", "usr", subdir, binary)
            if not os.path.isfile(candidate):
                raise ConanException(f"expected userspace executable missing: {binary}")
            copy(self, binary, os.path.dirname(candidate), bindir)
            os.chmod(os.path.join(bindir, binary), 0o755)

        mandir = os.path.join(self.package_folder, "share", "man", "man8")
        for subdir, binary in (("nat64", "jool"), ("siit", "jool_siit"),
                               ("joold", "joold")):
            candidate = os.path.join(self.source_folder, "src", "usr", subdir,
                                     binary + ".8")
            if not os.path.isfile(candidate):
                candidate = os.path.join(self.build_folder, "src", "usr", subdir,
                                         binary + ".8")
            if not os.path.isfile(candidate):
                raise ConanException(f"expected userspace manual missing: {binary}.8")
            copy(self, binary + ".8", os.path.dirname(candidate), mandir)

        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
