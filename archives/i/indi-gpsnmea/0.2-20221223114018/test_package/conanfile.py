#!/usr/bin/env python3
"""indi-gpsnmea test_package — consumer end-to-end suite against the packaged
driver.

indi-gpsnmea is an INDI driver (application package). It ships only:

  * bin/indi_gpsnmea            — the driver executable (links libindidriver)
  * share/indi/indi_gpsnmea.xml — the INDI device descriptor

The driver itself needs a live TCP NMEA receiver at 192.168.1.1:50000, and the
OHOS dynamic loader in this build sandbox cannot PROT_EXEC-mmap a conan-cache
framework .so, so the packaged binary is validated *statically* (ELF validity,
target triple, INDI-framework linkage, embedded GPS NMEA logic strings) rather
than executed.

The driver's actual *functional* core — the NMEA 0183 parser — is the in-tree
minmea (minmea.c/h, compiled straight into the driver by upstream CMakeLists).
This test recompiles a frozen copy of that source and drives it with known
NMEA sentences (RMC/GGA/GSA/GLL/ZDA plus bad-checksum and unknown sentences),
asserting the exact parsed values. That is the real consumer path and it runs
in the sandbox.

Statistical basis (PR 「适配后测试用例统计」 row 鸿蒙特有/消费者测试):
5 named end-to-end use cases (HC-1..HC-5), 54 checks. Upstream ships no test
suite (upstream N=0).
"""
import os
import re

from conan import ConanFile


class IndiGpsnmeaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        from conan.tools.cmake import cmake_layout
        cmake_layout(self)

    def test(self):
        pkg = self.dependencies["indi-gpsnmea"].package_folder
        driver = os.path.join(pkg, "bin", "indi_gpsnmea")
        device_xml = os.path.join(pkg, "share", "indi", "indi_gpsnmea.xml")
        for required in (driver, device_xml):
            if not os.path.isfile(required):
                raise AssertionError(
                    f"packaged artifact {required} is missing — the consumer "
                    "suite asserts on the shipped package, not on bookkeeping")

        src = os.path.join(self.recipe_folder, "test_gpsnmea.c")
        minmea_c = os.path.join(self.recipe_folder, "minmea.c")
        minmea_h = os.path.join(self.recipe_folder, "minmea.h")
        for required in (src, minmea_c, minmea_h):
            if not os.path.isfile(required):
                raise AssertionError(f"test source {required} is missing")

        out = os.path.join(self.build_folder, "test_gpsnmea")
        log = os.path.join(self.build_folder, "test_gpsnmea.log")

        cc = self.conf.get("tools.build:compiler_executables", default={}).get(
            "c", "clang")

        # Recompile the vendored NMEA parser and the consumer suite together.
        # -D_GNU_SOURCE exposes timegm (POSIX) so minmea.c compiles without an
        # implicit-declaration warning under -std=c99.
        self.run(
            f"{cc} -std=c99 -D_GNU_SOURCE -I{self.recipe_folder} "
            f"{src} {minmea_c} -o {out} -lm",
            scope="build",
        )

        # Run against the packaged driver binary + device xml.
        self.run(f"{out} {driver} {device_xml} {log}", scope="build")

        if not os.path.isfile(log):
            # The suite always writes a result log; if it is missing the run
            # did not actually execute, so fail loudly.
            raise AssertionError(f"test_gpsnmea produced no result log at {log}")
        with open(log, encoding="utf-8", errors="replace") as fh:
            output = fh.read()

        # Real assertions: every named use case must pass and the summary
        # lines must be clean.
        case_lines = re.findall(r"^case (HC-\d+) (start|PASS)", output, re.MULTILINE)
        passed = len(re.findall(r"^ok   - ", output, re.MULTILINE))
        failed = len(re.findall(r"^FAIL - ", output, re.MULTILINE))
        case_summary = re.search(r"== (\d+) cases, (\d+) failed ==", output)
        check_summary = re.search(r"== (\d+) checks, (\d+) failures ==", output)

        print(f"[test_gpsnmea] checks passed={passed} failed={failed}")
        if case_summary:
            print(f"[test_gpsnmea] case summary: {case_summary.group(0)}")
        if check_summary:
            print(f"[test_gpsnmea] check summary: {check_summary.group(0)}")

        if not case_lines:
            raise AssertionError(
                "test_gpsnmea reported no named use case — the suite would be "
                f"a hollow assertion dump:\n{output}")
        if failed != 0:
            raise AssertionError(
                f"test_gpsnmea reported {failed} failed check(s):\n{output}")
        if not re.search(r"^case HC-5 (start|PASS)", output, re.MULTILINE):
            raise AssertionError(
                "the HarmonyOS-specific use case HC-5 did not run — rule12 "
                f"requires it:\n{output}")
        if "RESULT: PASSED" not in output:
            raise AssertionError(f"test_gpsnmea did not report RESULT: PASSED:\n{output}")
        if case_summary and int(case_summary.group(2)) != 0:
            raise AssertionError(f"case summary reports failures:\n{output}")
        if check_summary and int(check_summary.group(2)) != 0:
            raise AssertionError(f"check summary reports failures:\n{output}")
        if passed == 0:
            raise AssertionError(
                "test_gpsnmea produced no passing checks — the test did not "
                f"actually exercise the driver:\n{output}")
