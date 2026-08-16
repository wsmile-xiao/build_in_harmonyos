#!/usr/bin/env python3
"""Conan recipe for the ACPICA Unix tools 20260408."""

import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    mkdir,
)
from conan.tools.layout import basic_layout


class AcpicaUnixConan(ConanFile):
    name = "acpica-unix"
    version = "20260408"
    description = "ACPICA utilities, including the iASL compiler and disassembler"
    license = "Intel-ACPI OR BSD-3-Clause OR GPL-2.0-only"
    homepage = "https://github.com/acpica/acpica"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "acpica-unix is prepared for Linux and OHOS only"
            )

    def tool_requirements(self):
        self.tool_requires("bash/5.3")
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4")
        self.tool_requires("m4/1.4.19")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(self, **self.conan_data["test_sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        suite_count, selected_count = self._inventory_aslts()

        # OHOS is Unix-like but is not detected by ACPICA's uname-based rules.
        # Select the upstream Linux application service layer explicitly.
        make_args = [
            "make",
            "-j1",
            self._make_assignment("CC", self._compiler_command()),
            "ACPI_HOST=_LINUX",
            "NOWERROR=TRUE",
            "NOFORTIFY=TRUE",
        ]
        self.run(
            " ".join(shlex.quote(arg) for arg in make_args),
            cwd=self.source_folder,
            env="conanbuild",
        )

        # Keep a small table-template probe independent of the separately
        # released ASLTS asset and its selected runtime collection.
        iasl = os.path.join(
            self.source_folder, "generate", "unix", "bin", "iasl"
        )
        template_dir = os.path.join(self.source_folder, "tests", "templates")
        self.run(
            f"{shlex.quote(iasl)} -T DSDT",
            cwd=template_dir,
            env="conanbuild",
        )
        self.run(
            f"{shlex.quote(iasl)} dsdt.asl",
            cwd=template_dir,
            env="conanbuild",
        )
        if not os.path.isfile(os.path.join(template_dir, "dsdt.aml")):
            raise ConanException("ACPICA DSDT template test did not produce dsdt.aml")

        self._run_aslts_subset(suite_count, selected_count)

    def package(self):
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "generate", "unix", "bin"),
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("PATH", bindir)

    def _inventory_aslts(self):
        test_root = os.path.join(self.source_folder, "tests")
        aslt_root = os.path.join(self.source_folder, "tests", "aslts")
        runner = os.path.join(self.source_folder, "tests", "aslts.sh")
        selected_root = os.path.join(
            aslt_root,
            "src",
            "runtime",
            "collections",
            "functional",
            "constant",
        )
        if not os.path.isfile(runner) or not os.path.isdir(selected_root):
            raise ConanException("official ASLTS asset is incomplete")

        suite_count = self._count_files(test_root, ".asl")
        selected_count = self._count_files(selected_root, ".asl")
        if suite_count <= 0 or selected_count <= 0:
            raise ConanException("official ASLTS inventory is empty")

        self.output.info(
            "ASLTS_INVENTORY "
            f"total_asl={suite_count} selected_case=constant "
            f"selected_asl={selected_count} selected_mode=n64"
        )
        return suite_count, selected_count

    def _run_aslts_subset(self, suite_count, selected_count):
        test_dir = os.path.join(self.source_folder, "tests")
        tmp_dir = os.path.join(self.build_folder, "aslts-tmp")
        mkdir(self, tmp_dir)

        test_env = Environment()
        test_env.define("TMPDIR", tmp_dir)
        test_env.define("ASLTS_SKIP_TEMPLATE", "yes")
        test_env.define("ASLTS_SKIP_RESULT_COMPARE", "yes")
        with test_env.vars(self).apply():
            self.run(
                "bash ./aslts.sh -e -u -c constant -m n64",
                cwd=test_dir,
                env="conanbuild",
            )

        generated_count = 0
        aml_root = os.path.join(test_dir, "aslts", "tmp", "aml")
        for root, _, files in os.walk(aml_root):
            generated_count += sum(name == "constant.aml" for name in files)
        if generated_count <= 0:
            raise ConanException("ASLTS constant/n64 did not produce constant.aml")

        passed, failed, tests = self._read_aslts_summary(test_dir)
        if passed <= 0 or failed != 0 or tests <= 0:
            raise ConanException(
                "ASLTS constant/n64 summary is not a non-empty clean pass: "
                f"pass={passed} fail={failed} tests={tests}"
            )

        self.output.info(
            "ASLTS_SUBSET_PASS "
            f"total_asl={suite_count} selected_case=constant "
            f"selected_asl={selected_count} selected_mode=n64 "
            f"generated_aml={generated_count} pass={passed} "
            f"fail={failed} tests={tests}"
        )

    @staticmethod
    def _read_aslts_summary(test_dir):
        results_root = os.path.join(test_dir, "aslts", "tmp", "RESULTS")
        summaries = []
        for root, _, files in os.walk(results_root):
            if "Summary" in files:
                summaries.append(os.path.join(root, "Summary"))
        if not summaries:
            raise ConanException("ASLTS did not produce a Summary file")

        summary_file = max(summaries, key=os.path.getmtime)
        with open(summary_file, encoding="utf-8", errors="replace") as handle:
            summary = handle.read()
        section_match = re.search(
            r"64-bit nopt mode:\s*(.*?)(?:32-bit opt mode:|\Z)",
            summary,
            re.DOTALL,
        )
        if not section_match:
            raise ConanException("ASLTS Summary has no 64-bit nopt section")

        section = section_match.group(1)
        values = []
        for label in ("PASS", "FAIL", "Tests"):
            match = re.search(
                rf"^\s*{label}\s*:\s*(\d+)\s*$", section, re.MULTILINE
            )
            if not match:
                raise ConanException(f"ASLTS Summary has no numeric {label} count")
            values.append(int(match.group(1)))
        return tuple(values)

    @staticmethod
    def _count_files(root, suffix):
        return sum(
            name.endswith(suffix)
            for _, _, files in os.walk(root)
            for name in files
        )

    def _compiler_command(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return executables.get("c", "clang")

    @staticmethod
    def _make_assignment(name, value):
        return f"{name}={value}"
