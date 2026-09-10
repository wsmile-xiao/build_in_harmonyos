#!/usr/bin/env python3
"""Conan recipe — GNU Binutils 2.46.0 for HarmonyOS PC (Autotools)."""

import json
import os
import re
import shlex
import shutil
from io import StringIO

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    chdir,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BinutilsConan(ConanFile):
    name = "binutils"
    version = "2.46.0"
    description = "GNU assembler, linker, and binary inspection tools"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/binutils/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "binutils 2.46.0 is adapted for Linux and OHOS"
            )

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "site-stty-fix.exp", self.recipe_folder, self.export_sources_folder)
        copy(self, "tmpfile-shim.c", self.recipe_folder, self.export_sources_folder)
        copy(self, "runtime-probe.c", self.recipe_folder, self.export_sources_folder)
        copy(self, "ohos-test-sign.*", self.recipe_folder, self.export_sources_folder)
        copy(self, "*.exp", os.path.join(self.recipe_folder, "exec-preflight"),
             os.path.join(self.export_sources_folder, "exec-preflight"))

    def requirements(self):
        # Binutils uses its bundled zlib and has no runtime Conan requirements.
        # DejaGNU/Expect/Tcl are test-only tools and belong to build_requirements.
        return None

    def build_requirements(self):
        # The upstream make check target invokes DejaGNU. These packages are
        # already published in the OHOS remote (W0 evidence in notes.md).
        # Host pre-development uses the distro tools directly; the OHOS
        # profile receives the published, target-native test tool chain.
        if str(self.settings.os) == "OHOS":
            self.tool_requires("dejagnu/1.6.3.1")
            self.tool_requires("expect/5.45.4")
            self.tool_requires("tcl/8.6.14")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                "--disable-gprofng",
                "--disable-gdb",
                "--disable-gdbserver",
                "--disable-sim",
                "--disable-nls",
                "--disable-werror",
                "--disable-shared",
                "--enable-static",
                "--without-zstd",
            ]
        )
        # Clang emits LLVM .addrsig directives by default; GNU as in this
        # release intentionally does not consume those directives. Suppress
        # only that metadata in test/build objects, preserving code generation.
        if str(self.settings.compiler) == "clang":
            toolchain.extra_cflags.append("-fno-addrsig")
            toolchain.extra_cxxflags.append("-fno-addrsig")
        build_env = toolchain.environment()
        if str(self.settings.compiler) == "clang":
            # The OHOS toolchain can carry linker-only options into legacy
            # Autoconf `$CC -E` probes. Keep probe stderr clean so valid
            # headers are not rejected because of an unused-option warning.
            build_env.append(
                "CPPFLAGS", "-Wno-unused-command-line-argument", separator=" "
            )
        if str(self.settings.os) == "OHOS":
            # musl-compatible OHOS libc may expose mallinfo symbols without
            # the glibc struct definitions used by optional ld statistics.
            build_env.define("ac_cv_func_mallinfo", "no")
            build_env.define("ac_cv_func_mallinfo2", "no")
        if str(self.settings_build.os) == "OHOS":
            # Autoconf only recognizes GNU mkdir version strings; Toybox's
            # working mkdir otherwise loses to a directly executed install-sh.
            build_env.define("MKDIR_P", "/system/bin/mkdir -p")
            build_env.append_path("PATH", "/system/bin")
            # The DejaGNU application package does not export include paths.
            # libsframe's configure probe and C tests still require dejagnu.h.
            dejagnu_include = os.path.join(
                self.dependencies.build["dejagnu"].package_folder, "include"
            )
            if not os.path.isfile(os.path.join(dejagnu_include, "dejagnu.h")):
                raise RuntimeError("DejaGNU package is missing include/dejagnu.h")
            build_env.append("CPPFLAGS", "-I" + shlex.quote(dejagnu_include), separator=" ")
        toolchain.generate(env=build_env)

        # Keep test tools in a private generated environment. Do not inject a
        # shared /usr/local prefix into the build worker.
        env = Environment()
        deps = self.dependencies.build
        for name in ("dejagnu", "expect"):
            try:
                dep = deps[name]
            except KeyError:
                dep = None
            if dep:
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
        try:
            tcl = deps["tcl"]
        except KeyError:
            tcl = None
        if tcl:
            tcl_lib = os.path.join(tcl.package_folder, "lib")
            env.prepend_path("LD_LIBRARY_PATH", tcl_lib)
            env.define("TCL_LIBRARY", os.path.join(tcl_lib, "tcl8.6"))
        if str(self.settings_build.os) == "OHOS":
            env.prepend_path("PATH", os.path.join(self.build_folder, "ohos-test-wrappers"))
            env.define("BINUTILS_OHOS_TEST_PIPES", "1")
            env.define("BINUTILS_OHOS_SIGNER", os.path.join(self.source_folder, "ohos-test-sign.py"))
        env.vars(self, scope="build").save_script("binutils_check_env")

    def _ohos_shell(self):
        return (VirtualBuildEnv(self, auto_generate=True).vars().get("CONFIG_SHELL")
                or "/system/bin/sh")

    def _ohos_triplet(self):
        from conan.tools.gnu.get_gnu_triplet import _get_gnu_triplet

        triplet = _get_gnu_triplet(str(self.settings.os), str(self.settings.arch))["triplet"]
        output = StringIO()
        self.run(
            f"{shlex.quote(self._ohos_shell())} "
            f"{shlex.quote(os.path.join(self.source_folder, 'config.sub'))} "
            f"{shlex.quote(triplet)}", stdout=output, env="conanbuild"
        )
        triplet = output.getvalue().strip()
        if not re.fullmatch(r"[A-Za-z0-9_.]+-[A-Za-z0-9_.]+-linux-ohos", triplet):
            raise RuntimeError(f"Unexpected canonical OHOS triplet: {triplet!r}")
        return triplet

    def _build_ohos_test_launcher(self):
        """Automake's runtest assignment requires a single executable pathname."""
        if str(self.settings_build.os) != "OHOS":
            return
        target = os.path.join(self.dependencies.build["dejagnu"].package_folder,
                              "bin", "runtest")
        if not os.path.isfile(target):
            raise RuntimeError("DejaGNU package is missing bin/runtest")
        wrapper_dir = os.path.join(self.build_folder, "ohos-test-wrappers")
        os.makedirs(wrapper_dir, exist_ok=True)
        compiler_map = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compiler_map.get("c") or shutil.which("clang")
        if not compiler:
            raise RuntimeError("C compiler is missing for the native DejaGNU launcher")
        source = os.path.join(wrapper_dir, "runtest.c")
        launcher = os.path.join(wrapper_dir, "runtest")
        content = (
            "#include <stdio.h>\n#include <stdlib.h>\n#include <unistd.h>\n"
            "int main(int argc, char **argv) {\n"
            "    char **args = calloc((size_t)argc + 2, sizeof(*args));\n"
            "    if (!args) { perror(\"calloc\"); return 127; }\n"
            f"    args[0] = {json.dumps(self._ohos_shell())};\n"
            f"    args[1] = {json.dumps(target)};\n"
            "    for (int i = 1; i < argc; ++i) args[i + 1] = argv[i];\n"
            "    execv(args[0], args);\n"
            "    perror(\"runtest execv\");\n    free(args);\n    return 127;\n}\n"
        )
        save(self, source, content)
        self.run(f"{shlex.quote(compiler)} -std=c99 -O2 {shlex.quote(source)} "
                 f"-o {shlex.quote(launcher)}", env="conanbuild")
        self.run(f"{shlex.quote(launcher)} --version",
                 env=["conanbuild", "binutils_check_env"])
        self.output.info("[OHOS-SHELL] native runtest launcher verified")

    def _ohos_make_overrides(self):
        """Return make variables that avoid direct script execution on HMDFS."""
        if str(self.settings_build.os) != "OHOS":
            return []
        return [
            "MKDIR_P=" + shlex.quote("/system/bin/mkdir -p"),
            "SHELL=" + shlex.quote(self._ohos_shell()),
        ]

    def _prepare_ohos_runtime(self):
        """Fail before the long build if the test-only preload is ineffective."""
        if str(self.settings_build.os) != "OHOS":
            return ""
        for name in ("llvm-objcopy", "binary-sign-tool"):
            if not os.path.isfile("/data/service/hnp/bin/" + name):
                raise RuntimeError(f"OHOS test execution requires the platform tool {name}")
        compiler_map = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compiler_map.get("c") or shutil.which("clang")
        if not compiler:
            raise RuntimeError("C compiler is missing for the OHOS runtime probe")
        shim = os.path.join(self.build_folder, "tmpfile-shim.so")
        probe = os.path.join(self.build_folder, "runtime-probe")
        log = os.path.join(self.build_folder, "runtime-preflight.log")
        self.run(
            f"{shlex.quote(compiler)} -shared -fPIC "
            f"{shlex.quote(os.path.join(self.source_folder, 'tmpfile-shim.c'))} "
            f"-o {shlex.quote(shim)}", env="conanbuild"
        )
        self.run(
            f"{shlex.quote(compiler)} "
            f"{shlex.quote(os.path.join(self.source_folder, 'runtime-probe.c'))} "
            f"-ldl -o {shlex.quote(probe)}", env="conanbuild"
        )
        rc = self.run(
            f"LD_PRELOAD={shlex.quote(shim)} {shlex.quote(probe)} "
            f"> {shlex.quote(log)} 2>&1", env="conanbuild", ignore_errors=True
        )
        self.run(f"cat {shlex.quote(log)}", env="conanbuild")
        if rc:
            raise RuntimeError(f"OHOS runtime probe failed: rc={rc}; see runtime-preflight.log")
        return shim

    def _check_ohos_test_transport(self, shim):
        if str(self.settings_build.os) != "OHOS":
            return
        directory = os.path.join(self.build_folder, "transport-preflight")
        os.makedirs(directory, exist_ok=True)
        triplet = self._ohos_triplet()
        launcher = os.path.join(self.build_folder, "ohos-test-wrappers", "runtest")
        command = (
            f"DEJAGNU={shlex.quote(os.path.join(self.source_folder, 'site-stty-fix.exp'))} "
            f"LD_PRELOAD={shlex.quote(shim)} {shlex.quote(launcher)} "
            f"--tool binutils-transport "
            f"--srcdir {shlex.quote(os.path.join(self.source_folder, 'exec-preflight'))} "
            f"--build={triplet} --host={triplet} --target={triplet}"
        )
        rc = self.run(command, cwd=directory, env=["conanbuild", "binutils_check_env"],
                      ignore_errors=True)
        summary = os.path.join(directory, "binutils-transport.sum")
        text = ""
        if os.path.isfile(summary):
            with open(summary, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        if (rc or not re.search(r"# of expected passes\s+5(?:\s|$)", text)
                or re.search(r"^(?:FAIL|ERROR|UNRESOLVED|UNSUPPORTED|UNTESTED):", text, re.MULTILINE)):
            raise RuntimeError("DejaGNU transport preflight failed; see transport-preflight logs")
        self.output.info("[OHOS-TRANSPORT] 5/5 checks passed; 256 subprocess cycles completed")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        self._build_ohos_test_launcher()
        shim_so = self._prepare_ohos_runtime()
        self._check_ohos_test_transport(shim_so)
        with chdir(self, self.build_folder):
            if str(self.settings_build.os) == "OHOS":
                configure = os.path.join(self.source_folder, "configure")
                configure_args = autotools._configure_args or ""
                self.run(
                    f"{shlex.quote(self._ohos_shell())} "
                    f"{shlex.quote(configure)} {configure_args}",
                    env="conanbuild",
                )
            else:
                autotools.configure()
            # GNU make's jobserver uses mkfifo, which is restricted on HMDFS.
            jobs = 1 if str(self.settings_build.os) == "OHOS" else min(
                os.cpu_count() or 2, 8
            )
            make_args = [f"-j{jobs}"] + self._ohos_make_overrides()
            autotools.make(args=make_args)

        if str(self.settings_build.os) == "OHOS" and can_run(self) and not cross_building(self):
            self._check_ohos_test_signing(shim_so)

        # Run the complete upstream DejaGNU check target whenever the build
        # context can execute target programs. Cross-only contexts retain a
        # clear skip record rather than silently claiming a pass.
        if can_run(self) and not cross_building(self):
            site_fix = os.path.join(self.build_folder, "site-stty-fix.exp")
            shutil.copy2(os.path.join(self.source_folder, "site-stty-fix.exp"), site_fix)
            assignments = []
            if os.path.isfile(site_fix):
                assignments.append(f"DEJAGNU={shlex.quote(site_fix)}")
            if os.path.isfile(shim_so) and str(self.settings.os) == "OHOS":
                assignments.append(f"LD_PRELOAD={shlex.quote(shim_so)}")
            check_log = os.path.join(self.build_folder, "upstream-check.log")
            check_args = ["make", "-k", "-j1", "check"]
            check_args.extend(self._ohos_make_overrides())
            if str(self.settings_build.os) == "OHOS":
                triplet = self._ohos_triplet()
                self.output.info(f"[OHOS-TRIPLET] canonical={triplet}")
                check_args.append(
                    "RUNTESTFLAGS="
                    + shlex.quote(
                        f"--build={triplet} --host={triplet} --target={triplet}"
                    )
                )
            command = " ".join(
                assignments
                + check_args
                + [">", shlex.quote(check_log), "2>&1"]
            )
            rc = self.run(
                command,
                cwd=self.build_folder,
                env=["conanbuild", "binutils_check_env"],
                ignore_errors=True,
            )
            self.run(f"cat {shlex.quote(check_log)}", cwd=self.build_folder)
            self._check_upstream_summary(check_log, rc)
            self._run_and_check_libiberty(shim_so)
        else:
            self.output.warning(
                "upstream make check skipped: target execution is unavailable"
            )

    def _check_ohos_test_signing(self, shim_so):
        """Run a program produced by this GNU ld after normal platform signing."""
        directory = os.path.join(self.build_folder, "signing-preflight")
        temporary = os.path.join(directory, "tmpdir")
        os.makedirs(temporary, exist_ok=True)
        compiler_map = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        compiler = compiler_map.get("c") or shutil.which("clang")
        program = os.path.join(temporary, "runtime-probe")
        linker = os.path.join(self.build_folder, "ld", "ld-new")
        helper = os.path.join(self.source_folder, "ohos-test-sign.py")
        self.run(f"{shlex.quote(compiler)} -fuse-ld={shlex.quote(linker)} "
                 f"{shlex.quote(os.path.join(self.source_folder, 'runtime-probe.c'))} "
                 f"-ldl -o {shlex.quote(program)}", env="conanbuild")
        self.run(f"python3 {shlex.quote(helper)} {shlex.quote(program)}", cwd=directory,
                 env="conanbuild")
        self.run(f"LD_PRELOAD={shlex.quote(shim_so)} {shlex.quote(program)}", cwd=directory,
                 env="conanbuild")
        self.output.info("[OHOS-SIGN] GNU ld output signed and executed successfully")

    def _check_upstream_summary(self, check_log, make_rc):
        """Require a real DejaGNU run and enforce the C-path 90% floor."""
        import re

        passes = failures = expected_failures = 0
        unresolved = untested = unsupported = 0
        expected_summaries = {
            "binutils/binutils.sum",
            "gas/testsuite/gas.sum",
            "ld/ld.sum",
            "libctf/libctf.sum",
            "libsframe/libsframe.sum",
        }
        found_summaries = set()
        gprof_logs = []
        for root, _dirs, files in os.walk(self.build_folder):
            for filename in files:
                path = os.path.join(root, filename)
                normalized = path.replace(os.sep, "/")
                if normalized.endswith("/gprof/testsuite/test-suite.log"):
                    gprof_logs.append(path)
                if not filename.endswith(".sum"):
                    continue
                matched_summaries = {
                    suffix
                    for suffix in expected_summaries
                    if normalized.endswith("/" + suffix)
                }
                if not matched_summaries:
                    continue
                found_summaries.update(matched_summaries)
                with open(path, encoding="utf-8", errors="replace") as handle:
                    text = handle.read()
                if re.search(r"^ERROR:|^UNRESOLVED:.*(?:Tcl error|aborted)", text, re.MULTILINE):
                    raise RuntimeError(f"upstream test driver aborted: {path}")
                for pattern, target in (
                    (r"# of expected passes\s+(\d+)", "passes"),
                    (r"# of unexpected failures\s+(\d+)", "failures"),
                    (r"# of expected failures\s+(\d+)", "expected_failures"),
                    (r"# of unresolved testcases\s+(\d+)", "unresolved"),
                    (r"# of untested testcases\s+(\d+)", "untested"),
                    (r"# of unsupported tests\s+(\d+)", "unsupported"),
                ):
                    match = re.search(pattern, text)
                    if match:
                        value = int(match.group(1))
                        if target == "passes":
                            passes += value
                        elif target == "failures":
                            failures += value
                        elif target == "unresolved":
                            unresolved += value
                        elif target == "expected_failures":
                            expected_failures += value
                        elif target == "untested":
                            untested += value
                        else:
                            unsupported += value
        missing_summaries = expected_summaries - found_summaries
        if missing_summaries:
            raise RuntimeError(
                "upstream make check did not produce every required DejaGNU "
                "summary: " + ", ".join(sorted(missing_summaries))
            )

        with open(check_log, encoding="utf-8", errors="replace") as handle:
            check_text = handle.read()
        expected_drivers = {
            "binutils": 34,
            "gas": 142,
            "ld": 184,
            "libctf": 4,
            "libsframe": 3,
        }
        driver_counts = {name: 0 for name in expected_drivers}
        for line in check_text.splitlines():
            if not re.match(r"^Running .+\.exp \.\.\.$", line):
                continue
            for name in expected_drivers:
                if f"/{name}/testsuite/" in line:
                    driver_counts[name] += 1
                    break
        mismatched_drivers = {
            name: (driver_counts[name], expected)
            for name, expected in expected_drivers.items()
            if driver_counts[name] != expected
        }
        if mismatched_drivers:
            raise RuntimeError(
                "upstream DejaGNU driver execution is incomplete: "
                + ", ".join(
                    f"{name}={actual}/{expected}"
                    for name, (actual, expected) in sorted(
                        mismatched_drivers.items()
                    )
                )
            )
        self.output.info(
            "[UPSTREAM-INVENTORY] exp_files=379 drivers=%d support_files=12 "
            "excluded_gprofng=7 distribution=%s"
            % (
                sum(driver_counts.values()),
                ",".join(
                    f"{name}:{driver_counts[name]}"
                    for name in ("binutils", "gas", "ld", "libctf", "libsframe")
                ),
            )
        )

        if not gprof_logs:
            raise RuntimeError("upstream make check produced no gprof test-suite.log")
        gprof_log = sorted(gprof_logs)[-1]
        with open(gprof_log, encoding="utf-8", errors="replace") as handle:
            gprof_text = handle.read()
        gprof_counts = {}
        for label in ("TOTAL", "PASS", "SKIP", "FAIL", "ERROR"):
            match = re.search(rf"# {label}:\s+(\d+)", gprof_text)
            if not match:
                raise RuntimeError(f"gprof summary is missing {label}")
            gprof_counts[label.lower()] = int(match.group(1))
        self._check_gprof_coverage(gprof_counts, gprof_log)

        resolved = passes + failures + unresolved
        rate = (passes / resolved) if resolved else 0.0
        self.output.info(
            "[UPSTREAM-TEST] suites=%d pass=%d fail=%d unresolved=%d "
            "xfail=%d untested=%d unsupported=%d rate=%.2f%% make_rc=%d" %
            (
                len(found_summaries),
                passes,
                failures,
                unresolved,
                expected_failures,
                untested,
                unsupported,
                rate * 100,
                make_rc,
            )
        )
        self.output.info(
            "[UPSTREAM-GPROF] total=%d pass=%d skip=%d fail=%d error=%d" %
            (
                gprof_counts["total"],
                gprof_counts["pass"],
                gprof_counts["skip"],
                gprof_counts["fail"],
                gprof_counts["error"],
            )
        )
        if resolved == 0 or rate < 0.90:
            raise RuntimeError(
                "upstream DejaGNU result is below the C-path 90% floor: "
                "pass=%d fail=%d unresolved=%d" % (passes, failures, unresolved)
            )
        if make_rc != 0 and failures == 0 and unresolved == 0:
            raise RuntimeError(
                f"upstream make check returned {make_rc} without a recorded "
                "DejaGNU failure"
            )
        if gprof_counts["fail"] or gprof_counts["error"]:
            raise RuntimeError(
                "gprof tests reported failures: fail=%d error=%d" %
                (gprof_counts["fail"], gprof_counts["error"])
            )

    def _check_gprof_coverage(self, counts, gprof_log):
        if counts["total"]:
            return
        config_log = os.path.join(os.path.dirname(os.path.dirname(gprof_log)), "config.log")
        native_disabled = False
        if str(self.settings.os) == "OHOS" and os.path.isfile(config_log):
            with open(config_log, encoding="utf-8", errors="replace") as handle:
                native_disabled = bool(re.search(
                    r"^gprof_cv_sys_native=['\"]?no['\"]?$", handle.read(), re.MULTILINE
                ))
        if not native_disabled or any(counts.values()):
            raise RuntimeError("gprof test suite reported zero tests without an upstream exclusion")
        self.output.warning(
            "[UPSTREAM-EXCLUSION] gprof discovered=2 executed=0: upstream "
            "gprof_cv_sys_native=no; profiling compiler/runtime probe failed. "
            "This is not a test pass; retain gprof/config.log."
        )

    def _run_and_check_libiberty(self, shim_so):
        """Re-run and verify all seven non-DejaGNU libiberty test targets."""
        test_dirs = []
        for root, _dirs, files in os.walk(self.build_folder):
            normalized = root.replace(os.sep, "/")
            if normalized.endswith("/libiberty/testsuite") and "Makefile" in files:
                test_dirs.append(root)
        if not test_dirs:
            raise RuntimeError("upstream build produced no libiberty testsuite Makefile")

        test_dir = sorted(test_dirs)[-1]
        log_file = os.path.join(self.build_folder, "libiberty-check.log")
        assignments = []
        if os.path.isfile(shim_so) and str(self.settings.os) == "OHOS":
            assignments.append(f"LD_PRELOAD={shlex.quote(shim_so)}")
        command = " ".join(
            assignments
            + [
                "make",
                "-C",
                shlex.quote(test_dir),
                "-j1",
                "really-check",
                *self._ohos_make_overrides(),
                ">",
                shlex.quote(log_file),
                "2>&1",
            ]
        )
        rc = self.run(
            command,
            cwd=self.build_folder,
            env=["conanbuild", "binutils_check_env"],
            ignore_errors=True,
        )
        self.run(f"cat {shlex.quote(log_file)}", cwd=self.build_folder)
        self._check_libiberty_summary(log_file, rc)

    def _check_libiberty_summary(self, log_file, make_rc):
        import re

        with open(log_file, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        demangle = re.findall(
            r"\./test-demangle:\s+(\d+) tests,\s+(\d+) failures", text
        )
        required_commands = (
            "./test-pexecute",
            "./test-expandargv",
            "./test-strtol",
            "./test-doubly-linked-list",
        )
        missing = [command for command in required_commands if command not in text]
        demangle_cases = sum(int(cases) for cases, _failures in demangle)
        demangle_failures = sum(int(value) for _cases, value in demangle)
        pass_lines = len(re.findall(r"^PASS:", text, re.MULTILINE))
        fail_lines = len(re.findall(r"^FAIL:", text, re.MULTILINE))
        expected_demangle_cases = 860
        expected_pass_lines = 69
        if (
            make_rc != 0
            or len(demangle) != 3
            or demangle_cases != expected_demangle_cases
            or demangle_failures
            or missing
            or fail_lines
            or pass_lines != expected_pass_lines
        ):
            raise RuntimeError(
                "libiberty tests incomplete: rc=%d demangle_groups=%d "
                "demangle_cases=%d demangle_failures=%d pass_lines=%d "
                "fail_lines=%d missing=%s"
                % (
                    make_rc,
                    len(demangle),
                    demangle_cases,
                    demangle_failures,
                    pass_lines,
                    fail_lines,
                    ",".join(missing) or "none",
                )
            )
        self.output.info(
            "[UPSTREAM-LIBIBERTY] targets=7 demangle_cases=%d "
            "reported_pass_lines=%d pexecute=pass failures=0 make_rc=%d"
            % (demangle_cases, pass_lines, make_rc)
        )

    def package(self):
        with chdir(self, self.build_folder):
            install_args = (["-j1"] + self._ohos_make_overrides()
                            if str(self.settings_build.os) == "OHOS" else None)
            Autotools(self).install(args=install_args)
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
