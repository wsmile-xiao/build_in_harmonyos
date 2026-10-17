#!/usr/bin/env python3
"""libfli test_package — runs the real consumer end-to-end suite against the
packaged library.

R34 / rule12: the suite in test_libfli.c is a set of NAMED, COMPLETE consumer
use cases (HC-1..HC-6), each a whole flow rather than a pile of assertions. HC-6
is the HarmonyOS-specific one and it consumes the *installed package*:

  * the packaged lib/libfli.a is parsed as a real ar archive and every member is
    verified to be a relocatable AArch64 ELF64 object;
  * that same packaged archive is absorbed into a downstream shared object
    (clang -shared -Wl,--whole-archive) and loaded with dlopen() by the platform
    dynamic loader, its FLI* entry points are resolved with dlsym() and called
    across the .so boundary;
  * the packaged lib/udev/rules.d/99-fli.rules is read and validated.

The downstream .so step is also the regression test for the packaging defect
that is fixed in build(): with the archive built without
CMAKE_POSITION_INDEPENDENT_CODE the --whole-archive link aborts with
"relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'devices'".
So a non-PIC libfli.a cannot pass this suite.

libfli is pure C; the test is C and links the static libfli.a. libfli's USB
backend calls into libusb-1.0, which the registry ships as a shared library
only, so the test (and the probe .so) link that .so explicitly and record an
RPATH — the OHOS loader cannot always mmap an OHOS .so PROT_EXEC on the build
host, so the test avoids pulling libfli's own .so in.
"""
import os
import re

from conan import ConanFile


class LibfliTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Keep the test build in the standard build/<cfg> layout so the
        # CMakeToolchain/CMakeDeps generators line up with the main recipe.
        from conan.tools.cmake import cmake_layout
        cmake_layout(self)

    def test(self):
        src = os.path.join(self.recipe_folder, "test_libfli.c")
        out = os.path.join(self.build_folder, "test_libfli")
        probe = os.path.join(self.build_folder, "libfli_downstream_probe.so")
        log = os.path.join(self.build_folder, "test_libfli.log")
        pkg = self.dependencies["libfli"].package_folder
        inc = os.path.join(pkg, "include")
        lib = os.path.join(pkg, "lib")
        archive = os.path.join(lib, "libfli.a")
        rules = os.path.join(lib, "udev", "rules.d", "99-fli.rules")

        for required in (archive, rules):
            if not os.path.isfile(required):
                raise AssertionError(
                    f"the packaged artifact {required} is missing — the consumer "
                    "suite asserts on the shipped package, not on the test's own "
                    "bookkeeping")

        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "clang")
        usb_lib_dir = os.path.join(self.dependencies["libusb"].package_folder, "lib")

        self.run(
            f"{cc} {src} -o {out} -Wl,--gc-sections,--as-needed "
            f"-Wl,-rpath,{usb_lib_dir} "
            f"-I{inc} {archive} "
            f"-L{usb_lib_dir} -lusb-1.0 -lm -lpthread -ldl",
            scope="build",
        )

        # A downstream shared object that absorbs the packaged static archive.
        # --whole-archive is required: nothing in the probe references a FLI*
        # symbol, so without it the linker would pull in no member at all and
        # dlsym() would have nothing to resolve.
        self.run(
            f"{cc} -shared -o {probe} "
            f"-Wl,--whole-archive {archive} -Wl,--no-whole-archive "
            f"-Wl,-rpath,{usb_lib_dir} "
            f"-L{usb_lib_dir} -lusb-1.0 -lm -lpthread",
            scope="build",
        )

        # The test writes its transcript to `log` as well as stdout, because
        # Conan's self.run() streams the output but does not return it.
        self.run(f"{out} {log} {lib} {probe} {rules}", scope="build")

        if not os.path.isfile(log):
            raise AssertionError(
                f"test_libfli produced no result log at {log}")
        with open(log, encoding="utf-8", errors="replace") as fh:
            output = fh.read()

        # Real assertions, not a smoke-test "did it link" check: every named
        # use case must report PASS, every check line must report ok, and both
        # summary lines must be clean.
        case_lines = re.findall(r"^case (HC-\d+) (PASS|FAIL)", output, re.MULTILINE)
        passed_cases = [c for c, verdict in case_lines if verdict == "PASS"]
        failed_cases = [c for c, verdict in case_lines if verdict == "FAIL"]
        passed = len(re.findall(r"^ok   - ", output, re.MULTILINE))
        failed = len(re.findall(r"^FAIL - ", output, re.MULTILINE))
        case_summary = re.search(r"== (\d+) cases, (\d+) failed ==", output)
        check_summary = re.search(r"== (\d+) checks, (\d+) failures ==", output)

        print(f"[test_libfli] use cases passed={len(passed_cases)} "
              f"failed={len(failed_cases)} -> {', '.join(passed_cases)}")
        print(f"[test_libfli] checks passed={passed} failed={failed}")
        if case_summary:
            print(f"[test_libfli] case summary: {case_summary.group(0)}")
        if check_summary:
            print(f"[test_libfli] check summary: {check_summary.group(0)}")

        if failed != 0:
            raise AssertionError(
                f"test_libfli reported {failed} failed check(s):\n{output}")
        if failed_cases:
            raise AssertionError(
                f"test_libfli use cases failed: {', '.join(failed_cases)}\n{output}")
        if not case_lines:
            raise AssertionError(
                "test_libfli reported no named use case — the suite would be a "
                f"hollow assertion dump:\n{output}")
        if "HC-6" not in passed_cases:
            raise AssertionError(
                "the HarmonyOS-specific consumer use case HC-6 did not pass — "
                f"rule12 requires it:\n{output}")
        if passed == 0:
            raise AssertionError(
                "test_libfli produced no passing checks — the test did not "
                f"actually exercise the library:\n{output}")
        if "RESULT: PASSED" not in output:
            raise AssertionError(f"test_libfli did not report RESULT: PASSED:\n{output}")
        if case_summary and int(case_summary.group(2)) != 0:
            raise AssertionError(f"test_libfli case summary reports failures:\n{output}")
        if check_summary and int(check_summary.group(2)) != 0:
            raise AssertionError(f"test_libfli check summary reports failures:\n{output}")
