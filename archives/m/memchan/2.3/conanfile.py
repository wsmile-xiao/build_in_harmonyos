#!/usr/bin/env python3
"""Conan recipe for the Memchan 2.3 Tcl channel extension."""

import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MemchanConan(ConanFile):
    name = "memchan"
    version = "2.3"
    package_type = "shared-library"
    description = "Tcl extension providing in-memory, FIFO, null, random and zero channels"
    license = "Tcl"
    homepage = "https://sourceforge.net/projects/memchan/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("tcl/8.6.16")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        tcl_root = self.dependencies["tcl"].package_folder
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend([
            f"--with-tcl={tcl_root}/lib",
            "tcl_cv_sys_version=Linux-6.6",
        ])
        toolchain.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _tcl_command(self, script):
        tclsh = os.path.join(self.dependencies["tcl"].package_folder, "bin", "tclsh8.6")
        runner = self.conf.get(
            "user.memchan:qemu_runner", default="", check_type=str
        ).strip()
        command = f"{shlex.quote(tclsh)} {shlex.quote(script)}"
        return f"{runner} {command}" if runner else command

    def _run_upstream_tests(self):
        library = os.path.join(self.build_folder, "libMemchan2.3.so")
        primary_script = os.path.join(self.build_folder, "run-primary-tests.tcl")
        primary_log = os.path.join(self.build_folder, "upstream-primary.log")
        save(
            self,
            primary_script,
            "load {%s} Memchan\nset VERBOSE 1\ncd {%s}\nsource all\n"
            % (library, os.path.join(self.source_folder, "tests")),
        )
        primary_rc = self.run(
            f"{self._tcl_command(primary_script)} > {shlex.quote(primary_log)} 2>&1",
            env="conanrun",
            ignore_errors=True,
        )
        with open(primary_log, encoding="utf-8", errors="replace") as stream:
            primary_output = stream.read()
        primary_passed = len(re.findall(r"^\+\+\+\+ .* PASSED$", primary_output, re.M))
        primary_failed = len(re.findall(r"^---- .* FAILED$", primary_output, re.M))
        primary_errors = primary_output.count("==== Test generated error:")
        if primary_rc or primary_passed != 38 or primary_failed or primary_errors:
            raise ConanException(
                "Memchan legacy tests failed: "
                f"rc={primary_rc}, passed={primary_passed}/38, "
                f"failed={primary_failed}, errors={primary_errors}; see {primary_log}"
            )

        tea_total = tea_passed = tea_failed = 0
        for test_file in ("fifo_bb.test", "memchan_bb.test"):
            script = os.path.join(self.build_folder, f"run-{test_file}.tcl")
            log = os.path.join(self.build_folder, f"upstream-{test_file}.log")
            save(
                self,
                script,
                "load {%s} Memchan\n"
                "package require tcltest\n"
                "namespace import ::tcltest::*\n"
                "cd {%s}\n"
                "source {%s}\n"
                % (library, os.path.join(self.source_folder, "tea.tests"), test_file),
            )
            rc = self.run(
                f"{self._tcl_command(script)} > {shlex.quote(log)} 2>&1",
                env="conanrun",
                ignore_errors=True,
            )
            with open(log, encoding="utf-8", errors="replace") as stream:
                output = stream.read()
            match = re.search(
                r"Total\s+(\d+)\s+Passed\s+(\d+)\s+Skipped\s+(\d+)\s+Failed\s+(\d+)",
                output,
            )
            if rc or not match:
                raise ConanException(f"TEA test {test_file} did not complete; see {log}")
            tea_total += int(match.group(1))
            tea_passed += int(match.group(2))
            tea_failed += int(match.group(4))

        if (tea_total, tea_passed, tea_failed) != (15, 15, 0):
            raise ConanException(
                f"Memchan TEA tests failed: total={tea_total}, "
                f"passed={tea_passed}, failed={tea_failed}"
            )
        self.output.info(
            "L1_UPSTREAM_RESULT: total=53 passed=53 failed=0 pass_rate=100.00%"
        )

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(target="binaries libraries", args=["-j1"])
        self._run_upstream_tests()

    def package(self):
        autotools = Autotools(self)
        autotools.install(target="install-binaries install-libraries")

    def package_info(self):
        package_dir = os.path.join("lib", "Memchan2.3")
        self.cpp_info.libs = ["Memchan2.3"]
        self.cpp_info.libdirs = [package_dir]
        self.runenv_info.prepend_path(
            "TCLLIBPATH", os.path.join(self.package_folder, package_dir)
        )
