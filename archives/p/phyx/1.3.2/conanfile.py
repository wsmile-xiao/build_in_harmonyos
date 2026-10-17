#!/usr/bin/env python3
"""Conan recipe for phyx 1.3.2, a suite of phylogenetic CLI tools."""

import glob
import os
import platform
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    patch,
    replace_in_file,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


_PROGRAMS = (
    "pxaa2cdn", "pxbdsim", "pxboot", "pxbp", "pxcat", "pxclsq",
    "pxcltr", "pxcolt", "pxcomp", "pxconsq", "pxfqfilt", "pxlog",
    "pxlssq", "pxlstr", "pxmono", "pxmrca", "pxmrcacut", "pxmrcaname",
    "pxnw", "pxpoly", "pxrecode", "pxrevcomp", "pxrls", "pxrlt",
    "pxrmk", "pxrms", "pxrmt", "pxrr", "pxs2fa", "pxs2nex", "pxs2phy",
    "pxseqgen", "pxssort", "pxsstat", "pxsw", "pxt2new", "pxt2nex",
    "pxtcol", "pxtcomb", "pxtgen", "pxtlate", "pxtrt", "pxtscale",
    "pxvcf2fa", "pxbdfit", "pxcontrates", "pxstrec",
)


def _route_profile_shell_to_sh(generators_folder):
    """Avoid profile-selected shell getcwd failures in HMDFS build folders."""
    assignment = re.compile(
        r'^(export (?:CONFIG_)?SHELL=)(["\'])([^"\']+)\2$',
        flags=re.MULTILINE,
    )

    def route(match):
        if match.group(3) == "/bin/sh":
            return match.group(0)
        return f'{match.group(1)}"/bin/sh"'

    for script in glob.glob(os.path.join(generators_folder, "**", "*.sh"),
                            recursive=True):
        with open(script, "r", encoding="utf-8", errors="ignore") as handle:
            data = handle.read()
        routed = assignment.sub(route, data)
        if routed != data:
            with open(script, "w", encoding="utf-8") as handle:
                handle.write(routed)
    for variable in ("SHELL", "CONFIG_SHELL"):
        if os.environ.get(variable) not in (None, "/bin/sh"):
            os.environ[variable] = "/bin/sh"


class PhyxConan(ConanFile):
    name = "phyx"
    version = "1.3.2"
    description = "Phylogenetic tools for sequence, tree, and character-data analyses"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/FePhyFoFum/phyx"
    url = "https://github.com/FePhyFoFum/phyx"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)
        # patch_user entries are deliberately not exported by Conan's helper.
        # This deferred patch targets config.guess after autoreconf refreshes it.
        copy(
            self,
            "0002-config-guess-ohos.patch",
            src=os.path.join(self.recipe_folder, "patches"),
            dst=os.path.join(self.export_sources_folder, "patches"),
        )

    def requirements(self):
        self.requires("armadillo/12.8.4")
        self.requires("nlopt/2.11.0")

    def build_requirements(self):
        self.tool_requires("automake/1.18")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"phyx supports Linux and OHOS, not {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The config.guess entry uses Conan's patch_user metadata, so the
        # standard helper applies only the source-tree patch at this stage.
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Only expose search directories.  Feeding a preassembled dependency
        # closure through LIBS makes AC_SEARCH_LIBS report "none required" and
        # hides the provider name which @LIBS@ must carry into the real links.
        for dependency in self.dependencies.host.values():
            if not dependency.package_folder:
                continue
            for include_dir in dependency.cpp_info.includedirs:
                tc.extra_cflags.append(f"-I{include_dir}")
                tc.extra_cxxflags.append(f"-I{include_dir}")
            for lib_dir in dependency.cpp_info.libdirs:
                tc.extra_ldflags.append(f"-L{lib_dir}")
        tc.generate()
        VirtualRunEnv(self).generate()

    @property
    def _src(self):
        return os.path.join(self.source_folder, "src")

    def _verify_single_math_provider(self):
        """Reject the deceptively-linkable dual BLAS/LAPACK provider graph."""
        if self.settings.os != "OHOS":
            return
        binary = os.path.join(self._src, "pxseqgen")
        executables = self.conf.get("tools.build:compiler_executables", default={},
                                    check_type=dict)
        compiler = executables.get("c", "")
        toolchain_bin = os.path.dirname(os.path.realpath(compiler))
        # Device tool bundles may expose llvm-readelf as a compatibility
        # launcher for llvm-readobj without placing that alias beside clang.
        readelf = (shutil.which("llvm-readelf") or
                   os.path.join(toolchain_bin, "llvm-readelf"))
        nm = (shutil.which("llvm-nm") or
              os.path.join(toolchain_bin, "llvm-nm"))
        dynamic = subprocess.run(
            [readelf, "-d", binary], check=True, text=True,
            capture_output=True).stdout
        forbidden_needed = ("libblas", "liblapack", "libFortranRuntime",
                            "libFortranDecimal")
        found = [name for name in forbidden_needed if name in dynamic]
        if found:
            raise ConanInvalidConfiguration(
                "phyx must use Armadillo's single math backend; unexpected "
                f"ELF dependencies: {', '.join(found)}")
        symbols = subprocess.run(
            [nm, "--defined-only", binary], check=True, text=True,
            capture_output=True).stdout
        duplicate = re.findall(r"\b(?:dgemm_|dgesv_|dgetrf_)$", symbols,
                               flags=re.MULTILINE)
        if duplicate:
            raise ConanInvalidConfiguration(
                "phyx executable statically embeds BLAS/LAPACK symbols in "
                "addition to Armadillo's backend")
        self.output.success(
            "OHOS math-provider check: Armadillo only; no embedded reference BLAS/LAPACK")

    def _can_execute_target(self):
        if cross_building(self):
            return False
        machine = platform.machine().lower()
        if str(self.settings.arch) == "armv8":
            return machine in ("aarch64", "arm64")
        return True

    def build(self):
        _route_profile_shell_to_sh(self.generators_folder)
        automake = self.dependencies.build["automake"]
        automake_share = glob.glob(os.path.join(
            automake.package_folder, "share", "automake-*"))
        if len(automake_share) != 1:
            raise ConanInvalidConfiguration(
                "cannot locate the pinned Automake data directory")
        perl = shutil.which("perl")
        if not perl:
            raise ConanInvalidConfiguration("Perl is required by Automake")
        automake_bin = os.path.join(automake.package_folder, "bin")
        # The published Automake launchers have a device-native Perl shebang.
        # Invoke their packaged implementation explicitly so the same recipe
        # also works in the host-side clean verification environment.
        aclocal = (f'{perl} {automake_bin}/.aclocal-real '
                   f'--automake-acdir={automake.package_folder}/share/aclocal-1.18 '
                   f'--system-acdir={automake.package_folder}/share/aclocal')
        automake_cmd = (f'{perl} {automake_bin}/.automake-real '
                        f'--libdir={automake_share[0]}')
        self.run(
            f'PERL5LIB="{automake_share[0]}" ACLOCAL="{aclocal}" '
            f'AUTOMAKE="{automake_cmd}" autoreconf -fi',
            cwd=self._src, env="conanbuild")
        if self.settings.os == "OHOS":
            # The 2017 upstream snapshot predates the OHOS triplet.  Refresh
            # only the standard GNU canonicalization helpers from the pinned
            # Automake build requirement rather than patching generated files.
            for helper in ("config.sub", "config.guess"):
                copy(self, helper, src=automake_share[0], dst=self._src,
                     keep_path=False)
            patch(
                self,
                base_path=self._src,
                patch_file=os.path.join(
                    self.export_sources_folder,
                    "patches",
                    "0002-config-guess-ohos.patch",
                ),
            )
            # Autoconf's AS_TMPDIR creates config.status scratch directories
            # with umask 077.  HMDFS maps their owner across the sandbox
            # boundary, so config.status cannot write conf*/subs1.awk.  Keep
            # the workaround local to the generated OHOS configure script and
            # retain group write access for the mapped build identity (E011).
            replace_in_file(
                self,
                os.path.join(self._src, "configure"),
                "umask 077",
                "umask 002",
            )
        self.run(
            f'./configure --prefix="{self.package_folder}"',
            cwd=self._src, env="conanbuild")
        self.run("make -j1", cwd=self._src, env="conanbuild")
        self._verify_single_math_provider()
        if self._can_execute_target():
            self.run("make -j1 check", cwd=self._src, env="conanrun")
        else:
            self.output.warning(
                "Cross build cannot execute target binaries; upstream tests run in native OHOS CI")

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        for program in _PROGRAMS:
            copy(self, program, src=self._src, dst=bindir, keep_path=False)
        copy(self, "*.1", src=os.path.join(self._src, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "*", src=os.path.join(self._src, "TEST"),
             dst=os.path.join(self.package_folder, "share", "phyx", "TEST"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        for dependency in self.dependencies.values():
            if not dependency.package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs:
                path = os.path.join(dependency.package_folder, libdir)
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", path)
