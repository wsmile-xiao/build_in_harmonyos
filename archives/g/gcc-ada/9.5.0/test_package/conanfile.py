#!/usr/bin/env python3
"""Consumer test for a packaged GCC 9.5 GNAT compiler."""

import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class GccAdaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = ("VirtualBuildEnv", "VirtualRunEnv")
    test_type = "explicit"
    exports_sources = (
        "test_gcc_ada.adb",
        "verify_adacgi.py",
        "verify_gcc_ada.py",
        "verify_upstream_ada.py",
        "upstream/adacgi/*",
        "upstream/gnat.dg/gcc-ada.exp",
    )

    _gnat_dg_tests = (
        "modular2",
        "fixedpnt",
        "concat_length",
        "array31",
        "overflow_sum3",
        "access_test",
        "aggr1",
        "array10",
        "alignment2",
        "abstract_with_anonymous_result",
        "array3",
        "array4",
        "array6",
        "array12",
        "array21",
        "array30",
        "array33",
        "array34",
        "array_bounds_test",
        "access4",
        "access_discr2",
        "aggr3",
        "alignment1",
        "alignment7",
        "alignment8",
        "alignment9",
        "alignment10",
        "modular1",
        "modular3",
        "fixedpnt5",
    )
    _acats_tests = (
        "a22006b",
        "c2a021b",
        "c38006a",
        "c54a23a",
        "c95040a",
        "a22006c",
        "a22006d",
        "a35101b",
        "c23006a",
        "c48004a",
        "c55c02a",
    )

    def build_requirements(self):
        # Reuse the already published DejaGNU/Expect/Tcl chain for the
        # upstream GNAT driver.  These are test tools, not package runtime
        # dependencies, so they stay in the build context.
        self.tool_requires("dejagnu/1.6.3.1")
        self.tool_requires("expect/5.45.4")
        self.tool_requires("tcl/8.6.14")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _tool(self, name):
        dependency = self.dependencies["gcc-ada"]
        bindirs = dependency.cpp_info.bindirs
        if not bindirs:
            raise ConanInvalidConfiguration(
                "The gcc-ada package does not declare a binary directory"
            )
        executable = os.path.join(
            dependency.package_folder,
            bindirs[0],
            name,
        )
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                "The packaged {} executable was not found: {}".format(
                    name, executable
                )
            )
        return executable

    def _packaged_upstream_root(self):
        dependency = self.dependencies["gcc-ada"]
        root = os.path.join(
            dependency.package_folder,
            "share",
            "gcc-ada",
            "upstream-tests",
        )
        if not os.path.isdir(root):
            raise ConanInvalidConfiguration(
                "The gcc-ada package does not contain upstream test sources: {}".format(
                    root
                )
            )
        return root

    def _stage_dejagnu_source_root(self):
        package_root = self._packaged_upstream_root()
        packaged_root = os.path.join(package_root, "gnat.dg")
        if not os.path.isdir(packaged_root):
            raise ConanInvalidConfiguration(
                "Packaged GNAT test source directory is missing: {}".format(
                    packaged_root
                )
            )
        staged_root = os.path.join(
            self.build_folder, ".upstream-test-sources", "gnat.dg"
        )
        if os.path.exists(staged_root):
            shutil.rmtree(staged_root)
        os.makedirs(os.path.dirname(staged_root), exist_ok=True)
        shutil.copytree(packaged_root, staged_root)
        driver = os.path.join(
            self.source_folder, "upstream", "gnat.dg", "gcc-ada.exp"
        )
        if not os.path.isfile(driver):
            raise ConanInvalidConfiguration(
                "Package-owned DejaGNU driver is missing: {}".format(driver)
            )
        shutil.copy2(driver, os.path.join(staged_root, "gcc-ada.exp"))
        return staged_root

    def _build_tool(self, package_name, name):
        dependency = self.dependencies.build[package_name]
        # expect/5.45.4 installs its executable under bin/ but predates the
        # bindirs metadata declaration; keep the fallback local to this test
        # package so the published dependency remains untouched.
        bindirs = dependency.cpp_info.bindirs or ["bin"]
        executable = os.path.join(dependency.package_folder, bindirs[0], name)
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                "The packaged {} executable was not found: {}".format(
                    name, executable
                )
            )
        return executable

    def _sign_program(self, path):
        if str(self.settings.os) != "OHOS":
            return
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not (os.path.isfile(signer) and objcopy and readelf):
            raise ConanInvalidConfiguration(
                "Running GNAT output on OHOS requires binary-sign-tool, "
                "llvm-objcopy and llvm-readelf"
            )

        header = subprocess.run(
            [readelf, "-h", path],
            capture_output=True,
            text=True,
            check=True,
        )
        if not re.search(r"Type:\s+(?:EXEC|DYN)\b", header.stdout):
            raise ConanInvalidConfiguration(
                "GNAT did not produce a runnable ELF file: {}".format(path)
            )

        original_mode = stat.S_IMODE(os.stat(path).st_mode)
        with tempfile.TemporaryDirectory(
            prefix=".conan-sign-", dir=os.path.dirname(path)
        ) as temp_dir:
            os.chmod(temp_dir, 0o775)
            unsigned = os.path.join(temp_dir, "unsigned")
            signed = os.path.join(temp_dir, "signed")
            shutil.copy2(path, unsigned)
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", unsigned],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    unsigned,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                check=True,
            )
            sections = subprocess.run(
                [readelf, "-S", signed],
                capture_output=True,
                text=True,
                check=True,
            )
            if ".codesign" not in sections.stdout:
                raise ConanInvalidConfiguration(
                    "Signing did not add .codesign: {}".format(path)
                )
            os.replace(signed, path)
            os.chmod(
                path,
                original_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH,
            )

    def _upstream_executable(self, suite, test_name):
        return os.path.join(
            self.build_folder,
            "upstream",
            suite,
            test_name,
            test_name,
        )

    def _dg_options(self, source):
        with open(source, encoding="utf-8") as source_file:
            contents = source_file.read()
        if not re.search(r"\{\s*dg-do\s+run\s*\}", contents):
            raise ConanInvalidConfiguration(
                "Selected gnat.dg test is not a run test: {}".format(source)
            )
        match = re.search(r'\{\s*dg-options\s+"([^"]*)"\s*\}', contents)
        return shlex.split(match.group(1)) if match else []

    @staticmethod
    def _acats_source_path(source_root, test_name):
        # GCC keeps ACATS sources in chapter directories, not one flat folder.
        chapter = "a" if test_name.startswith("a") else test_name[:2]
        return os.path.join(
            source_root, "tests", chapter, test_name + ".ada"
        )

    def _build_gnat_dg_subset(self, gnatmake):
        source_root = os.path.join(
            self._packaged_upstream_root(), "gnat.dg"
        )
        for test_name in self._gnat_dg_tests:
            source = os.path.join(source_root, test_name + ".adb")
            if not os.path.isfile(source):
                raise ConanInvalidConfiguration(
                    "Selected gnat.dg source is missing: {}".format(source)
                )
            executable = self._upstream_executable(
                "gnat.dg", test_name
            )
            test_dir = os.path.dirname(executable)
            os.makedirs(test_dir, exist_ok=True)
            arguments = [gnatmake, "-q"] + self._dg_options(source) + [
                source,
                "-o",
                executable,
            ]
            self.run(
                shlex.join(arguments),
                cwd=test_dir,
                env="conanrun",
            )
            self._sign_program(executable)

    def _build_acats_subset(self, gnatmake, gnatchop):
        source_root = os.path.join(
            self._packaged_upstream_root(), "acats"
        )
        support_dir = os.path.join(
            self.build_folder, "upstream", "acats", "support"
        )
        os.makedirs(support_dir, exist_ok=True)
        for filename in ("repspec.ada", "repbody.ada"):
            source = os.path.join(source_root, "support", filename)
            if not os.path.isfile(source):
                raise ConanInvalidConfiguration(
                    "Selected ACATS support source is missing: {}".format(
                        source
                    )
                )
            self.run(
                shlex.join([gnatchop, "-w", source]),
                cwd=support_dir,
                env="conanrun",
            )
        for filename in ("report.ads", "report.adb"):
            generated = os.path.join(support_dir, filename)
            if not os.path.isfile(generated):
                raise ConanInvalidConfiguration(
                    "gnatchop did not create ACATS support file: {}".format(
                        generated
                    )
                )

        for test_name in self._acats_tests:
            source = self._acats_source_path(source_root, test_name)
            if not os.path.isfile(source):
                raise ConanInvalidConfiguration(
                    "Selected ACATS source is missing: {}".format(source)
                )
            executable = self._upstream_executable("acats", test_name)
            test_dir = os.path.dirname(executable)
            os.makedirs(test_dir, exist_ok=True)
            self.run(
                shlex.join([gnatchop, "-c", "-w", source]),
                cwd=test_dir,
                env="conanrun",
            )
            main_source = os.path.join(test_dir, test_name + ".adb")
            if not os.path.isfile(main_source):
                raise ConanInvalidConfiguration(
                    "gnatchop did not create ACATS main source: {}".format(
                        main_source
                    )
                )
            arguments = [
                gnatmake,
                "-q",
                "-gnatws",
                "-O2",
                "-gnat95",
                "-I" + support_dir,
                main_source,
                "-o",
                executable,
            ]
            self.run(
                shlex.join(arguments),
                cwd=test_dir,
                env="conanrun",
            )
            self._sign_program(executable)

    def _build_adacgi_integration(self, gnatmake):
        source_root = os.path.join(
            self.source_folder, "upstream", "adacgi"
        )
        required_sources = (
            "cgi.ads",
            "cgi.adb",
            "ustrings.ads",
            "ustrings.adb",
            "test_adacgi.adb",
        )
        missing = [
            filename
            for filename in required_sources
            if not os.path.isfile(os.path.join(source_root, filename))
        ]
        if missing:
            raise ConanInvalidConfiguration(
                "AdaCGI integration sources are missing: {}".format(
                    ", ".join(missing)
                )
            )

        executable = self._upstream_executable(
            "adacgi", "test_adacgi"
        )
        test_dir = os.path.dirname(executable)
        os.makedirs(test_dir, exist_ok=True)
        arguments = [
            gnatmake,
            "-q",
            "-gnata",
            "-O2",
            "-gnat95",
            "-I" + source_root,
            os.path.join(source_root, "test_adacgi.adb"),
            "-o",
            executable,
        ]
        self.run(
            shlex.join(arguments),
            cwd=test_dir,
            env="conanrun",
        )
        self._sign_program(executable)

    def _run_dejagnu_subset(self, gnatmake):
        """Run the selected GNAT sources through the published DejaGNU tool."""
        runtest = self._build_tool("dejagnu", "runtest")
        expect = self._build_tool("expect", "expect")
        tcl = self.dependencies.build["tcl"]
        tcl_library = os.path.join(tcl.package_folder, "lib", "tcl8.6")
        tcl_libdir = os.path.join(tcl.package_folder, "lib")

        source_root = self._stage_dejagnu_source_root()
        command = [
            runtest,
            "--srcdir={}".format(source_root),
            "--tool=gcc-ada",
        ]
        if str(self.settings.os) == "OHOS":
            command.extend(
                ["--build=aarch64-linux-ohos", "--host=aarch64-linux-ohos"]
            )

        # Run through Conan's generated environments so the gcc-ada driver
        # contributes ADA_INCLUDE_PATH/GNAT runtime settings.  A direct
        # subprocess would inherit only Python's host environment and makes
        # GNAT report "cannot locate file system.ads".
        log_path = os.path.join(self.build_folder, "dejagnu-gnat.log")
        status_path = os.path.join(self.build_folder, "dejagnu-gnat.status")
        path_prefix = os.pathsep.join(
            [os.path.dirname(runtest), os.path.dirname(expect)]
        )
        environment_prefix = (
            "GNATMAKE={} TCL_LIBRARY={} PATH={}:$PATH "
            "LD_LIBRARY_PATH={}:$LD_LIBRARY_PATH"
        ).format(
            shlex.quote(gnatmake),
            shlex.quote(tcl_library),
            path_prefix,
            shlex.quote(tcl_libdir),
        )
        wrapped_command = (
            "({} {}; rc=$?; printf '%s' \"$rc\" > {})"
        ).format(
            environment_prefix,
            shlex.join(command),
            shlex.quote(status_path),
        )
        self.run(
            "{} > {} 2>&1".format(
                wrapped_command, shlex.quote(log_path)
            ),
            cwd=self.build_folder,
            env=["conanrun", "conanbuild"],
        )
        try:
            with open(status_path, encoding="utf-8") as status_file:
                returncode = int(status_file.read().strip())
        except (OSError, ValueError):
            returncode = 1
        try:
            with open(log_path, encoding="utf-8", errors="replace") as log_file:
                transcript = log_file.read()
        except OSError:
            transcript = ""
        if transcript:
            self.output.info(transcript.rstrip())
        pass_lines = len(re.findall(r"(?m)^PASS:", transcript))
        summary_match = re.search(
            r"(?m)^# of expected passes\s+(\d+)\s*$", transcript
        )
        pass_count = (
            int(summary_match.group(1))
            if summary_match
            else pass_lines
        )
        if returncode != 0 or re.search(r"(?m)^FAIL:", transcript):
            raise ConanInvalidConfiguration(
                "DejaGNU GNAT subset failed (exit {}, PASS count {}): {}".format(
                    returncode, pass_count, runtest
                )
            )
        if pass_count < len(self._gnat_dg_tests):
            raise ConanInvalidConfiguration(
                "DejaGNU GNAT subset reported {} PASS results, expected {}".format(
                    pass_count, len(self._gnat_dg_tests)
                )
            )
        self.output.info(
            "DEJAGNU_GNAT_DG_SUBSET={}/{}".format(
                pass_count, len(self._gnat_dg_tests)
            )
        )

    def build(self):
        gnatmake = self._tool("gnatmake")
        self._tool("gnatbind")
        self._tool("gnatlink")
        gnatchop = self._tool("gnatchop")
        self.run(
            "{} --version".format(shlex.quote(gnatmake)),
            env="conanrun",
        )

        source = os.path.join(self.source_folder, "test_gcc_ada.adb")
        executable = os.path.join(self.build_folder, "gcc_ada_test")
        self.run(
            "{} -q -gnata -O2 {} -o {}".format(
                shlex.quote(gnatmake),
                shlex.quote(source),
                shlex.quote(executable),
            ),
            env="conanrun",
        )
        self._sign_program(executable)
        self._build_gnat_dg_subset(gnatmake)
        self._build_acats_subset(gnatmake, gnatchop)
        self._build_adacgi_integration(gnatmake)

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-building: GNAT compile, bind and link completed; "
                "execution skipped"
            )
            return
        executable = os.path.join(self.build_folder, "gcc_ada_test")
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                "The GNAT test executable was not found: {}".format(
                    executable
                )
            )
        verifier = os.path.join(
            self.source_folder, "verify_gcc_ada.py"
        )
        self.run(
            "{} {} {}".format(
                shlex.quote(sys.executable),
                shlex.quote(verifier),
                shlex.quote(executable),
            ),
            env="conanrun",
        )
        adacgi_verifier = os.path.join(
            self.source_folder, "verify_adacgi.py"
        )
        self.run(
            "{} {} {}".format(
                shlex.quote(sys.executable),
                shlex.quote(adacgi_verifier),
                shlex.quote(
                    self._upstream_executable(
                        "adacgi", "test_adacgi"
                    )
                ),
            ),
            env="conanrun",
        )
        self._run_dejagnu_subset(self._tool("gnatmake"))
        upstream_verifier = os.path.join(
            self.source_folder, "verify_upstream_ada.py"
        )
        self.run(
            "{} {} {}".format(
                shlex.quote(sys.executable),
                shlex.quote(upstream_verifier),
                shlex.quote(
                    os.path.join(self.build_folder, "upstream")
                ),
            ),
            env="conanrun",
        )
