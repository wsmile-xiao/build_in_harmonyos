#!/usr/bin/env python3
"""Conan recipe for safe-iop 0.3.1 on HarmonyOS.

safe-iop is a small C library whose Makefile only builds a test executable or
an uninstalled shared object.  The recipe therefore uses the compiler selected
by the Conan profile directly, packages the public header plus safe_iopf
implementation, and invokes the unmodified upstream ``make test`` target.
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class SafeIopConan(ConanFile):
    name = "safe-iop"
    version = "0.3.1"
    description = "Safe integer arithmetic operations for C"
    license = "Public-Domain"
    homepage = "https://code.google.com/archive/p/safe-iop/"
    url = "https://code.google.com/archive/p/safe-iop/"
    topics = ("integer-overflow", "safe-arithmetic", "c")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "safe-iop supports Linux and OHOS, not %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        self._set_writable_tmp()
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tmpdir = self._set_writable_tmp()
        for name in ("TMPDIR", "TMP", "TEMP"):
            self.buildenv_info.define(name, tmpdir)

    def _set_writable_tmp(self):
        for name in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR"):
            value = os.environ.get(name)
            if value and value != "/tmp":
                try:
                    os.makedirs(value, exist_ok=True)
                    if os.access(value, os.W_OK):
                        break
                except OSError:
                    pass
        else:
            root = getattr(self, "build_folder", None) or os.getcwd()
            value = os.path.join(root, "tmp_hmbs")
            os.makedirs(value, exist_ok=True)
        for name in ("TMPDIR", "TMP", "TEMP"):
            os.environ[name] = value
        return value

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = (executables.get("c") or "").strip()
        if configured and os.path.isfile(configured) and os.access(configured, os.X_OK):
            return configured
        if configured:
            fallback = shutil.which(os.path.basename(configured))
            if fallback:
                return fallback
        return shutil.which("clang") or shutil.which("cc") or "clang"

    @staticmethod
    def _tool(*names):
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return names[0]

    def _run(self, command, cwd):
        self.output.info("+ %s" % " ".join(command))
        process = subprocess.run(
            command,
            cwd=cwd,
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1200,
        )
        output = process.stdout or ""
        if output:
            self.output.info(output.rstrip())
        if process.returncode != 0:
            raise ConanException(
                "command failed (rc=%s): %s\n%s"
                % (process.returncode, " ".join(command), output[-6000:])
            )
        return output

    def build(self):
        apply_conandata_patches(self)
        self._set_writable_tmp()
        os.makedirs(self.build_folder, exist_ok=True)

        cc = self._compiler()
        optimisation = "-O2" if str(self.settings.build_type) == "Release" else "-O0"
        obj = os.path.join(self.build_folder, "safe_iop.o")
        compile_command = [
            cc,
            optimisation,
            "-Wall",
            "-Wextra",
            "-I" + os.path.join(self.source_folder, "include"),
        ]
        if self.options.shared or self.options.get_safe("fPIC"):
            compile_command.append("-fPIC")
        compile_command += [
            "-c",
            os.path.join(self.source_folder, "src", "safe_iop.c"),
            "-o",
            obj,
        ]
        self._run(compile_command, self.build_folder)

        if self.options.shared:
            library = os.path.join(self.build_folder, "libsafe_iop.so")
            self._run(
                [cc, "-shared", "-Wl,-soname,libsafe_iop.so", obj, "-o", library],
                self.build_folder,
            )
        else:
            library = os.path.join(self.build_folder, "libsafe_iop.a")
            self._run([self._tool("llvm-ar", "ar"), "rcs", library, obj], self.build_folder)

        self._run_upstream_tests(cc)

    def _run_upstream_tests(self, cc):
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "safe-iop requires native execution of its upstream test suite"
            )
        make = self._tool("make", "gmake")
        output = self._run(
            [
                make,
                "test",
                "CC=" + cc,
                "CFLAGS=-Wall -O2 -Iinclude",
            ],
            self.source_folder,
        )
        expects = re.search(
            r"(\d+)/(\d+) expects succeeded \((\d+) failures\)", output
        )
        tests = re.search(
            r"(\d+)/(\d+) tests succeeded \((\d+) failures\)", output
        )
        if not expects or not tests:
            raise ConanException("upstream test summary was not found")
        expect_passed, expect_total, expect_failed = map(int, expects.groups())
        passed, total, failed = map(int, tests.groups())
        if (expect_passed, expect_total, expect_failed) != (459, 459, 0):
            raise ConanException("unexpected upstream assertion result: %s" % (expects.group(0),))
        if (passed, total, failed) != (73, 73, 0):
            raise ConanException("unexpected upstream test result: %s" % (tests.group(0),))
        marker = {
            "status": "passed",
            "framework": "make",
            "command": "make test",
            "discovered": total,
            "executed": total,
            "passed": passed,
            "failed": failed,
            "assertions": expect_total,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))

    def package(self):
        copy(
            self,
            "safe_iop.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        pattern = "libsafe_iop.so" if self.options.shared else "libsafe_iop.a"
        copy(
            self,
            pattern,
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "README",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["safe_iop"]
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "safe-iop")
        self.cpp_info.set_property("cmake_target_name", "safe-iop::safe-iop")
