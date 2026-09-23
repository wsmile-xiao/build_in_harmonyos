#!/usr/bin/env python3
"""Conan recipe for the cimfomfa C utility library (libtingea)."""

import json
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CimfomfaConan(ConanFile):
    name = "cimfomfa"
    version = "21-361"
    description = "C utility library used by MCL and zoem"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/micans/cimfomfa"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The Git tag omits generated Autotools files. CI provides autoconf,
        # but its minimal OHOS image has no automake/aclocal.
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        # This project always builds a static archive and does not use
        # Libtool, so its configure script has no shared/static switches.
        for argument in ("--disable-shared", "--enable-static"):
            if argument in toolchain.configure_args:
                toolchain.configure_args.remove(argument)
        if str(self.settings.os) == "OHOS":
            # CI workers use HMDFS for TMPDIR. GNU config.guess creates a
            # mode-0700 probe directory there, which becomes unwritable after
            # HMDFS applies setgid and makes its dummy.c probe fail. Supplying
            # the native OHOS build triplet skips config.guess entirely while
            # keeping host == build.
            arch = str(self.settings.arch)
            cpu = "aarch64" if arch == "armv8" else arch
            toolchain.configure_args.append(
                f"--build={cpu}-unknown-linux-ohos"
            )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        # The Git tag intentionally omits generated Autotools files. Recreate
        # them from the upstream template instead of carrying a source patch.
        version_file = os.path.join(self.source_folder, "VERSION")
        configure_template = os.path.join(self.source_folder, "configure.ac.in")
        configure_ac = os.path.join(self.source_folder, "configure.ac")
        save(self, version_file, self.version + "\n")
        with open(configure_template, encoding="utf-8") as handle:
            configure_text = handle.read().replace(
                "setversion_VERSION", str(self.version)
            )
        save(self, configure_ac, configure_text)
        self.run("autoreconf -fi", cwd=self.source_folder)
        if str(self.settings.os) == "OHOS":
            # E129/E011: config.status inherits these mode-0700 temporary
            # directory commands from configure. HMDFS adds setgid to the
            # directory and the worker then cannot create subs1.awk inside it.
            replace_in_file(
                self,
                os.path.join(self.source_folder, "configure"),
                "umask 077",
                "umask 022",
            )

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream provides a check target but registers zero automated tests.
        autotools.make(target="check", args=["-j1"])
        self._run_upstream_programs()

    def _run_upstream_programs(self):
        """Run nine representative programs shipped in src/trumpet."""
        test_dir = os.path.join(self.build_folder, "src", "trumpet")
        fixture = os.path.join(self.build_folder, "cimfomfa-test-data.txt")
        save(self, fixture, "OpenHarmony\nportable C library\n")
        commands = [
            "./cff_pagesize",
            "./cff_link",
            "./cff_bitpat",
            "./cff_let '1+2*3'",
            "./cff_tst hello world 0",
            "./cff_unit_ceilfloor 64 20 2",
            "./cff_optoid -a HarmonyOS",
            f'./cff_match Harmony "{fixture}"',
            f'./cff_read "{fixture}" 4',
        ]
        for command in commands:
            self.run(command, cwd=test_dir)
        result = {
            "status": "passed",
            "framework": "upstream-trumpet-programs",
            "command": "nine representative src/trumpet programs",
            "discovered": len(commands),
            "executed": len(commands),
            "passed": len(commands),
            "failed": 0,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(result, ensure_ascii=False)
        )

    def package(self):
        Autotools(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["tingea"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "cimfomfa")
        self.cpp_info.set_property("cmake_target_name", "cimfomfa::cimfomfa")
