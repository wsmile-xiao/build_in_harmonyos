#!/usr/bin/env python3
"""Conan recipe — ceccomp 4.2.2 (seccomp BPF 过滤器分析工具).

ceccomp is a C command-line tool for analyzing seccomp BPF filters:
assemble, disassemble, emulate and extract (probe/trace) filters.
It is NOT an autotools project: upstream ships a hand-written Python
configure script (argparse based) that reads CC/CFLAGS/LDFLAGS from the
environment and a Makefile.in template — hence this recipe drives it via
conanbuild env instead of the Autotools helper.

On HarmonyOS PC it is adapted as follows (see notes.md):

  * musl/OHOS has no argp.h; upstream configure probes -largp as a
    fallback, but that probe misses the -I/-L system dirs — patched to
    push_sys_dir=True (same as its libseccomp probe). We pass a single
    merged include/lib dir (configure only accepts ONE --includedir and
    ONE --libdir) built from the Conan dependency graph.
  * OHOS SDK sys/prctl.h conflicts with linux/prctl.h (duplicate
    struct prctl_mm_map) — redundant includes dropped.
  * /tmp is not writable on OHOS devices; probe's tmpfile() is replaced
    by a TMPDIR-aware mkstemp+unlink+fdopen helper.
  * i18n (gettext) and docs (asciidoc) disabled via upstream options.
  * make install uses coreutils `install`, absent on OHOS; packaging
    copies the binary/completion manually.

R33: compiler/flags come from the Conan graph (conanbuild env), never
     bare shell variables. Hardening flags mirror the device-verified
     native build (binary is PIE with full RELRO/BIND_NOW).
R38: command-line tool, commands.json declared at software level.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    copy, get, apply_conandata_patches, export_conandata_patches,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class CeccompConan(ConanFile):
    name = "ceccomp"
    version = "4.2.2"
    package_type = "application"

    description = ("seccomp BPF filter analysis tool (assemble, disassemble, "
                   "emulate and trace filters)")
    homepage = "https://github.com/ceccomp/ceccomp"
    license = "GPL-3.0-or-later"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Published on ohpcd with OHOS binaries (W0 verified via
        # conan install --build=never on the device).
        self.requires("libseccomp/2.6.1")
        self.requires("argp-standalone/1.5.0")

    def validate(self):
        # R32: must check in ("Linux", "OHOS"), not == "Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ceccomp only supports Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _merged_dep_dirs(self):
        """Merge dependency include/lib into single dirs.

        Upstream configure accepts only ONE --includedir/--libdir and its
        compile/link probes rely on those dirs, so the two dependency
        packages are merged into build-scoped dirs (never packaged).
        Entries are symlinked, not copied: lib dirs contain .so -> .so.N
        links and Conan 2.29's copy() has no symlinks= support.
        """
        merged_inc = os.path.join(self.build_folder, "merged_include")
        merged_lib = os.path.join(self.build_folder, "merged_lib")
        os.makedirs(merged_inc, exist_ok=True)
        os.makedirs(merged_lib, exist_ok=True)
        for dep in ("libseccomp", "argp-standalone"):
            d = self.dependencies.get(dep)
            if d is None:
                continue
            for inc in d.cpp_info.includedirs:
                self._link_into(inc, merged_inc)
            for lib in d.cpp_info.libdirs:
                self._link_into(lib, merged_lib)
        return merged_inc, merged_lib

    @staticmethod
    def _link_into(src_dir, merged):
        for name in os.listdir(src_dir):
            link = os.path.join(merged, name)
            if not os.path.lexists(link):
                os.symlink(os.path.join(src_dir, name), link)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Mirror the device-verified native build flags; the resulting
        # binary is PIE (DYN) with GNU_RELRO and BIND_NOW (L4 verified).
        tc.extra_cflags.append("-fpie")
        tc.extra_cflags.append("-fstack-protector")
        tc.extra_ldflags.append("-z now")
        tc.extra_ldflags.append("-z noexecstack")
        tc.extra_ldflags.append("-fpie")
        tc.generate()

    def build(self):
        top = self.source_folder
        merged_inc, merged_lib = self._merged_dep_dirs()
        # Upstream supports --without-doc (no asciidoc on OHOS) and
        # --without-i18n (SDK libintl.h lacks gettext declarations).
        self.run(
            f"cd {top} && python3 ./configure --prefix=/ "
            f"--without-doc --without-i18n "
            f"--includedir={merged_inc} --libdir={merged_lib}",
            env="conanbuild",
        )
        # Device default parallelism (workflow 2.1: make -j1).
        self.run(f"cd {top} && make -j1", env="conanbuild")

    def package(self):
        top = self.source_folder
        # Upstream `make install` shells out to coreutils `install`,
        # which does not exist on OHOS; copy the same artifacts manually
        # (bin_install + zsh_cmp_install; doc/i18n are disabled).
        copy(self, "ceccomp", os.path.join(top, "build"),
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "_ceccomp", os.path.join(top, "completions"),
             os.path.join(self.package_folder, "res", "zsh", "site-functions"),
             keep_path=False)
        copy(self, "LICENSE", top,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Standalone terminal binary, not a library.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # Ensure ceccomp is on PATH for VirtualRunEnv (test_package).
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
