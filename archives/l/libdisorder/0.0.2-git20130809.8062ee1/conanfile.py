#!/usr/bin/env python3
"""Conan recipe for libdisorder 0.0.2-git20130809.8062ee1."""

import json
import os
import platform
import re
import selectors
import shlex
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LibdisorderConan(ConanFile):
    name = "libdisorder"
    version = "0.0.2-git20130809.8062ee1"
    description = "Library and command-line tool for measuring byte-stream entropy"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/locasto/libdisorder"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                "libdisorder is packaged here for HarmonyOS/OHOS only"
            )
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "libdisorder currently supports the HarmonyOS PC armv8 target"
            )
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "libdisorder is intentionally packaged as the upstream static library"
            )

    def _tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c")
        if not cc:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables must provide the C compiler"
            )
        tool_dir = os.path.dirname(cc)
        ar = executables.get("ar") or os.path.join(tool_dir, "llvm-ar")
        ranlib = executables.get("ranlib") or os.path.join(tool_dir, "llvm-ranlib")
        for label, executable in (("C compiler", cc), ("archiver", ar), ("ranlib", ranlib)):
            if not (os.path.isfile(executable) or shutil.which(executable)):
                raise ConanInvalidConfiguration(f"{label} is unavailable: {executable}")
        return cc, ar, ranlib

    def build(self):
        apply_conandata_patches(self)
        cc, ar, ranlib = self._tools()
        source = os.path.join(self.source_folder, "code")
        include = os.path.join(source, "include")
        os.makedirs(self.build_folder, exist_ok=True)
        opt = "-O2" if str(self.settings.build_type) == "Release" else "-O0 -g"
        common = (
            f"{opt} -fPIC -Wall -Wextra -Wno-unused-parameter "
            "-D_POSIX_C_SOURCE=200809L -std=c99"
        )
        obj = os.path.join(self.build_folder, "disorder.o")
        library = os.path.join(self.build_folder, "libdisorder.a")
        ropy = os.path.join(self.build_folder, "ropy")
        upstream_test = os.path.join(self.build_folder, "libdisorder_upstream_test")

        self.run(
            f'{shlex.quote(cc)} {common} -I{shlex.quote(include)} -c '
            f'{shlex.quote(os.path.join(source, "src", "disorder.c"))} '
            f'-o {shlex.quote(obj)}'
        )
        self.run(f'{shlex.quote(ar)} rcs {shlex.quote(library)} {shlex.quote(obj)}')
        self.run(f'{shlex.quote(ranlib)} {shlex.quote(library)}')
        for source_file, output in (
            (os.path.join(source, "tool", "ropy.c"), ropy),
            (os.path.join(source, "test", "test.c"), upstream_test),
        ):
            self.run(
                f'{shlex.quote(cc)} {common} -I{shlex.quote(include)} '
                f'{shlex.quote(source_file)} {shlex.quote(library)} -lm '
                f'-o {shlex.quote(output)}'
            )

        result = self._run_upstream_test(upstream_test)
        with open(
            os.path.join(self.build_folder, "upstream_test_result.json"),
            "w",
            encoding="utf-8",
        ) as result_file:
            json.dump(result, result_file, ensure_ascii=False, indent=2)
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        self.output.info(marker)
        print(marker, flush=True)

    def _runner_prefix(self):
        machine = platform.machine().lower()
        if machine in ("aarch64", "arm64"):
            return []
        qemu = shutil.which("qemu-aarch64")
        root = os.environ.get("QEMU_LD_PREFIX")
        if not qemu:
            raise ConanInvalidConfiguration(
                "qemu-aarch64 is required to run OHOS tests on a non-AArch64 host"
            )
        if not root or not os.path.isfile(
            os.path.join(root, "lib", "ld-musl-aarch64.so.1")
        ):
            raise ConanInvalidConfiguration(
                "QEMU_LD_PREFIX must contain lib/ld-musl-aarch64.so.1"
            )
        return [qemu, "-L", root]

    def _run_upstream_test(self, executable):
        command = self._runner_prefix() + [executable]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        pattern = re.compile(
            r"^\[\s*(\d+)\]\s+entropy:\s+([0-9.]+)\s+"
            r"maxent:\s+([0-9.]+)\s+ratio:\s+([0-9.]+)$"
        )
        samples = []
        deadline = time.monotonic() + 30
        try:
            while len(samples) < 3 and time.monotonic() < deadline:
                events = selector.select(timeout=1)
                if process.poll() is not None and not events:
                    break
                for key, _ in events:
                    line = key.fileobj.readline().strip()
                    if not line:
                        continue
                    match = pattern.match(line)
                    if not match:
                        raise ConanException(
                            "unexpected upstream entropy-test output: " + line
                        )
                    run = int(match.group(1))
                    entropy, maximum, ratio = map(float, match.groups()[1:])
                    if run != len(samples):
                        raise ConanException("upstream test run counter is not contiguous")
                    if not (0.0 <= entropy <= 8.0 and 0.0 <= maximum <= 8.0):
                        raise ConanException("upstream entropy result is out of range")
                    if not (0.0 <= ratio <= 1.000001):
                        raise ConanException("upstream entropy ratio is out of range")
                    samples.append(line)
            if len(samples) != 3:
                stderr = process.stderr.read() if process.poll() is not None else ""
                raise ConanException(
                    f"upstream continuous test produced {len(samples)}/3 valid samples: {stderr}"
                )
        finally:
            selector.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        return {
            "status": "passed",
            "framework": "standalone-continuous-smoke",
            "command": "code/test/test.c (3 validated /dev/urandom iterations, then terminate)",
            "discovered": 1,
            "executed": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
            "iterations_validated": len(samples),
        }

    def package(self):
        source = os.path.join(self.source_folder, "code")
        copy(
            self,
            "disorder.h",
            src=os.path.join(source, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libdisorder.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "ropy",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "COPYING",
            src=source,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "upstream_test_result.json",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "res"),
        )

    def package_info(self):
        self.cpp_info.libs = ["disorder"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "libdisorder")
        self.cpp_info.set_property("cmake_target_name", "libdisorder::libdisorder")
        self.cpp_info.set_property("pkg_config_name", "libdisorder")
