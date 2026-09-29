#!/usr/bin/env python3
"""Conan recipe for oidentd 3.1.0 (upstream autotools build).

Upstream: https://github.com/janikrabe/oidentd (tag v3.1.0).
Source: official release asset, which ships the pre-generated `configure`,
`config.sub`, `install-sh` and the flex/bison outputs
(`src/cfg_scan.c`, `src/cfg_parse.c`), so no autoreconf bootstrap is needed.

Optional upstream features are all disabled (masquerading/NAT, and the
libnetfilter_conntrack code path they imply) => zero runtime dependencies;
the binary only needs libc/POSIX interfaces from the OHOS sysroot.
"""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OidentdConan(ConanFile):
    name = "oidentd"
    version = "3.1.0"
    description = "Flexible RFC 1413 (Ident) daemon"
    license = "GPL-2.0-only"
    homepage = "https://oidentd.janikrabe.com"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # Upstream configure is in-source: it appends
        # `cp -f $srcdir/src/kernel/$os_src src/os.c` after config.status, so the
        # generated os.c is expected next to the sources. Build in place.
        self.folders.build = "."

    def build_requirements(self):
        # configure hard-errors when no lexer/parser generator is found
        # (configure.ac: AC_PROG_LEX / AC_PROG_YACC), and automake's
        # BUILT_SOURCES list (cfg_parse.h/cfg_parse.c/cfg_scan.c) may still be
        # regenerated when tarball mtimes are not ordered. The pre-generated
        # sources alone would make these optional, but the configure-time
        # probes make them mandatory.
        self.tool_requires("flex/2.6.4")
        self.tool_requires("bison/3.8.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "oidentd/3.1.0 currently supports only OHOS armv8"
            )

        tc = AutotoolsToolchain(self)
        # All optional features off => no libnetfilter_conntrack, no NAT/masq.
        # `--disable-nat` also folds into masq_support, but pass both so the
        # intent is explicit and survives upstream default changes.
        tc.configure_args.extend([
            "--disable-masq",
            "--disable-nat",
            "--disable-libnfct",
        ])

        if self.settings.os == "OHOS":
            # AutotoolsToolchain does not derive OHOS triplets on its own
            # (tools.gnu:host_triplet is unset in the ohos-aarch64 profile),
            # and upstream config.sub predates HarmonyOS. The linux-ohos
            # triplet is accepted thanks to 0001-config.sub-linux-ohos.patch.
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])

        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # R9: keep the build single-threaded.
        autotools.make(args=["-j1"])

    def package(self):
        # AutotoolsToolchain emits --sbindir=${prefix}/<first bindir> == "bin",
        # so the upstream `sbin_PROGRAMS = oidentd` install target lands in
        # bin/ without an extra fold step. man pages go to share/man
        # (prebuilt in the tarball; the asciidoctor rule is not triggered
        # because the shipped man pages are newer than their .adoc sources).
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
