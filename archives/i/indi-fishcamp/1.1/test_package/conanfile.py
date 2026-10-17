#!/usr/bin/env python3
"""indi-fishcamp test_package — consumer end-to-end suite against the packaged
driver.

indi-fishcamp is an INDI driver (application package). It ships only:

  * bin/indi_fishcamp_ccd            — the driver executable (links
                                       libindidriver)
  * share/indi/indi_fishcamp.xml     — the INDI device descriptor

The driver itself needs a physical Starfish camera on USB, and the OHOS
dynamic loader in this build sandbox cannot PROT_EXEC-mmap the conan-cache
framework .so libindidriver.so.2, so the packaged binary is validated
*statically* (ELF validity, target triple, INDI-framework linkage, embedded
Starfish driver logic strings) rather than executed.

The driver's actual *functional* core — the Starfish USB protocol — is
libfishcamp, and the vendor library ships a built-in simulation mode
(fcUsb_setSimulation(true)) that emulates the camera end-to-end without
hardware. This test links the real packaged libfishcamp.a and drives the
full consumer command sequence (find cameras / open / getinfo / gain /
integration time / start exposure / get temperature / close) with the
simulation on, asserting the exact deterministic simulated values. That is
the real consumer path and it runs in the sandbox.

Statistical basis (PR 「适配后测试用例统计」 row 鸿蒙特有/消费者测试):
5 named end-to-end use cases (HC-1..HC-5). Upstream ships no test suite
(upstream N=0).
"""
import os
import re

from conan import ConanFile


class IndiFishcampTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Functional core: the test drives libfishcamp's simulation mode
        # directly, so the test package requires it (and libusb for its
        # dynamic link) independently of the application package.
        self.requires("libfishcamp/1.2")
        self.requires("libusb/1.0.27")

    def layout(self):
        from conan.tools.cmake import cmake_layout
        cmake_layout(self)

    def test(self):
        pkg = self.dependencies["indi-fishcamp"].package_folder
        driver = os.path.join(pkg, "bin", "indi_fishcamp_ccd")
        device_xml = os.path.join(pkg, "share", "indi", "indi_fishcamp.xml")
        for required in (driver, device_xml):
            if not os.path.isfile(required):
                raise AssertionError(
                    f"packaged artifact {required} is missing — the consumer "
                    "suite asserts on the shipped package, not on bookkeeping")

        fc = self.dependencies["libfishcamp"]
        usb = self.dependencies["libusb"]
        fc_inc = os.path.join(fc.package_folder, fc.cpp_info.includedirs[0])
        usb_inc = os.path.join(usb.package_folder, usb.cpp_info.includedirs[0])
        fc_lib = os.path.join(fc.package_folder, fc.cpp_info.libdirs[0])
        usb_lib = os.path.join(usb.package_folder, usb.cpp_info.libdirs[0])

        src = os.path.join(self.recipe_folder, "test_fishcamp.c")
        if not os.path.isfile(src):
            raise AssertionError(f"test source {src} is missing")

        out = os.path.join(self.build_folder, "test_fishcamp")
        log = os.path.join(self.build_folder, "test_fishcamp.log")

        cc = self.conf.get("tools.build:compiler_executables", default={}).get(
            "c", "clang")

        # Compile the consumer suite against the packaged libfishcamp.a
        # (fishcamp_common.h includes <libusb.h>, so the libusb leaf include
        # dir must be on the search path).
        self.run(
            f"{cc} -std=c99 -D_GNU_SOURCE -I{fc_inc} -I{usb_inc} "
            f"{src} -o {out} -L{fc_lib} -lfishcamp -L{usb_lib} -lusb-1.0",
            scope="build",
        )

        # Run against the packaged driver binary + device xml. libfishcamp is
        # static, so the runtime only needs libusb-1.0.so.0 on the loader
        # path; point HOME at the build folder so the (suppressed) Starfish
        # log file lands somewhere writable.
        self.run(
            f"LD_LIBRARY_PATH={usb_lib} HOME={self.build_folder} "
            f"{out} {driver} {device_xml} {log}",
            scope="build",
        )

        if not os.path.isfile(log):
            # The suite always writes a result log; if it is missing the run
            # did not actually execute, so fail loudly.
            raise AssertionError(f"test_fishcamp produced no result log at {log}")
        with open(log, encoding="utf-8", errors="replace") as fh:
            output = fh.read()

        # Real assertions: every named use case must pass and the summary
        # lines must be clean.
        case_lines = re.findall(r"^case (HC-\d+) (start|PASS)", output, re.MULTILINE)
        passed = len(re.findall(r"^ok   - ", output, re.MULTILINE))
        failed = len(re.findall(r"^FAIL - ", output, re.MULTILINE))
        case_summary = re.search(r"== (\d+) cases, (\d+) failed ==", output)
        check_summary = re.search(r"== (\d+) checks, (\d+) failures ==", output)

        print(f"[test_fishcamp] checks passed={passed} failed={failed}")
        if case_summary:
            print(f"[test_fishcamp] case summary: {case_summary.group(0)}")
        if check_summary:
            print(f"[test_fishcamp] check summary: {check_summary.group(0)}")

        if not case_lines:
            raise AssertionError(
                "test_fishcamp reported no named use case — the suite would be "
                f"a hollow assertion dump:\n{output}")
        if failed != 0:
            raise AssertionError(
                f"test_fishcamp reported {failed} failed check(s):\n{output}")
        if not re.search(r"^case HC-5 (start|PASS)", output, re.MULTILINE):
            raise AssertionError(
                "the HarmonyOS-specific use case HC-5 did not run — rule12 "
                f"requires it:\n{output}")
        if "RESULT: PASSED" not in output:
            raise AssertionError(f"test_fishcamp did not report RESULT: PASSED:\n{output}")
        if case_summary and int(case_summary.group(2)) != 0:
            raise AssertionError(f"case summary reports failures:\n{output}")
        if check_summary and int(check_summary.group(2)) != 0:
            raise AssertionError(f"check summary reports failures:\n{output}")
        if passed == 0:
            raise AssertionError(
                "test_fishcamp produced no passing checks — the test did not "
                f"actually exercise the driver:\n{output}")
