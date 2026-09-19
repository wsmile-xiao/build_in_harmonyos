#!/usr/bin/env python3
"""Conan recipe for libkal 0.9.0 on HarmonyOS aarch64."""

import json
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibkalConan(ConanFile):
    name = "libkal"
    version = "0.9.0"
    description = "Calendar conversion library for Julian, Gregorian, Arabic, and Jewish dates"
    license = "LGPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/libkal"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    _library_sources = (
        "kal_main.c", "kal_getdate.c", "kal_names.c", "kal_check.c", "kal_procs.c",
    )
    _public_headers = (
        "kal.h", "kal_main.h", "kal_getdate.h", "kal_names.h", "kal_check.h", "kal_procs.h",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                "libkal/0.9.0 adaptation targets OHOS only, got os=%s" % self.settings.os
            )
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "libkal/0.9.0 adaptation targets HarmonyOS PC aarch64, got arch=%s"
                % self.settings.arch
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        self._ensure_writable_tmp()

    def _ensure_writable_tmp(self):
        candidates = [
            os.environ.get("TMPDIR"), os.environ.get("TMP"),
            os.environ.get("TEMP"), os.environ.get("HMBS_TMPDIR"),
        ]
        tmpdir = ""
        for candidate in candidates:
            if candidate and candidate != "/tmp":
                try:
                    os.makedirs(candidate, exist_ok=True)
                    if os.access(candidate, os.W_OK):
                        tmpdir = candidate
                        break
                except OSError:
                    pass
        if not tmpdir:
            base = getattr(self, "build_folder", None) or os.getcwd()
            tmpdir = os.path.join(base, "tmp_hmbs")
            os.makedirs(tmpdir, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        return tmpdir

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        candidate = str(compilers.get("c") or "").strip()
        if candidate:
            parts = shlex.split(candidate)
            first = parts[0]
            if os.path.isfile(first) and os.access(first, os.X_OK):
                return parts
            resolved = shutil.which(os.path.basename(first))
            if resolved:
                return [resolved] + parts[1:]
            raise ConanException("configured C compiler is not executable: %s" % candidate)
        fallback = shutil.which("clang") or shutil.which("cc")
        if not fallback:
            raise ConanException("no C compiler found in profile or PATH")
        return [fallback]

    def _llvm_tool(self, name):
        cc_path = self._compiler()[0]
        sibling = os.path.join(os.path.dirname(cc_path), name)
        if os.path.isfile(sibling) and os.access(sibling, os.X_OK):
            return sibling
        resolved = shutil.which(name)
        if resolved:
            return resolved
        raise ConanException("required build tool not found: %s" % name)

    def _sdk_llvm_libdir(self):
        cached = getattr(self, "_checked_sdk_llvm_libdir", None)
        if cached is not None:
            return cached

        compiler = self._compiler()
        candidates = []
        try:
            probe = subprocess.run(
                compiler + ["-print-resource-dir"], check=False,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30,
            )
            resource_dir = (probe.stdout or "").strip().splitlines()
            if probe.returncode == 0 and resource_dir:
                candidates.append(
                    os.path.normpath(os.path.join(resource_dir[-1], os.pardir, os.pardir))
                )
        except (OSError, subprocess.SubprocessError):
            pass
        compiler_real = os.path.realpath(compiler[0])
        candidates.append(
            os.path.join(os.path.dirname(os.path.dirname(compiler_real)), "lib")
        )

        for candidate in dict.fromkeys(candidates):
            candidate = os.path.realpath(candidate)
            if not os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                continue
            lld = os.path.join(os.path.dirname(candidate), "bin", "lld")
            env = os.environ.copy()
            old_path = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                part for part in (candidate, old_path) if part
            )
            try:
                probe = subprocess.run(
                    [lld, "-flavor", "gnu", "--version"], check=False, env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30,
                )
            except (OSError, subprocess.SubprocessError) as error:
                raise ConanException(
                    "cannot execute the active OHOS SDK linker %s: %s" % (lld, error)
                ) from error
            if probe.returncode != 0:
                raise ConanException(
                    "active OHOS SDK linker probe failed: %s\n%s"
                    % (lld, (probe.stderr or probe.stdout or "").strip())
                )
            self.output.info("Using OHOS SDK linker runtime: %s" % candidate)
            self._checked_sdk_llvm_libdir = candidate
            return candidate

        raise ConanException(
            "cannot locate active OHOS SDK llvm/lib containing libxml2.so.16"
        )

    def _run(self, argv, cwd, input_text=None, timeout=1200, linker_runtime=False):
        env = os.environ.copy()
        tmpdir = self._ensure_writable_tmp()
        for key in ("TMPDIR", "TMP", "TEMP"):
            env[key] = tmpdir
        if linker_runtime:
            sdk_llvm_lib = self._sdk_llvm_libdir()
            old_path = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                part for part in (sdk_llvm_lib, old_path) if part
            )
        self.output.info("+ %s" % " ".join(shlex.quote(str(x)) for x in argv))
        proc = subprocess.run(
            [str(x) for x in argv], cwd=cwd, env=env, input=input_text,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
        )
        output = proc.stdout or ""
        if output:
            self.output.info(output[-8000:])
        return proc.returncode, output

    def _run_checked(
        self, argv, cwd, input_text=None, timeout=1200, linker_runtime=False
    ):
        rc, output = self._run(
            argv, cwd, input_text=input_text, timeout=timeout,
            linker_runtime=linker_runtime,
        )
        if rc != 0:
            raise ConanException(
                "command failed with rc=%s: %s\n%s"
                % (rc, " ".join(str(x) for x in argv), output[-4000:])
            )
        return output

    def build(self):
        cc = self._compiler()
        ar = self._llvm_tool("llvm-ar")
        ranlib = self._llvm_tool("llvm-ranlib")
        objdir = os.path.join(self.build_folder, "obj")
        os.makedirs(objdir, exist_ok=True)
        flags = ["-std=gnu11", "-Wall", "-Wextra"]
        flags += (["-O2", "-DNDEBUG"] if str(self.settings.build_type) == "Release"
                  else ["-O0", "-g"])
        if self.options.get_safe("fPIC"):
            flags.append("-fPIC")
        flags += list(self.conf.get("tools.build:cflags", default=[], check_type=list) or [])

        objects = []
        for source_name in self._library_sources:
            source = os.path.join(self.source_folder, source_name)
            obj = os.path.join(objdir, source_name[:-2] + ".o")
            self._run_checked(cc + flags + ["-c", source, "-o", obj], objdir)
            objects.append(obj)
        library = os.path.join(objdir, "libkal.a")
        self._run_checked([ar, "rcs", library] + objects, objdir)
        self._run_checked([ranlib, library], objdir)
        self._run_upstream_tests(cc, flags, library)

    def _build_test_binary(self, cc, flags, library, source_name, output_name, testdir):
        source = os.path.join(self.source_folder, source_name)
        output = os.path.join(testdir, output_name)
        self._run_checked(
            cc + flags + ["-I", self.source_folder, source, library, "-o", output],
            testdir, linker_runtime=True,
        )
        return output

    def _run_upstream_tests(self, cc, flags, library):
        discovered = 7
        if not can_run(self):
            marker = {
                "status": "skipped", "framework": "upstream-makefile/direct-exec",
                "command": "check jul/gre/ar/jew; test; test1; test-dw",
                "discovered": discovered, "executed": 0, "passed": 0,
                "failed": 0, "skipped": discovered,
                "reason": "cross-building: target binaries cannot run on build host",
            }
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker), flush=True)
            return

        testdir = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(testdir, exist_ok=True)
        binaries = {
            name: self._build_test_binary(cc, flags, library, source, name, testdir)
            for name, source in (
                ("check", "check.c"), ("test", "test.c"),
                ("test1", "test1.c"), ("test-dw", "test-dw.c"),
            )
        }
        passed = 0
        details = []
        for calendar in ("jul", "gre", "ar", "jew"):
            rc, output = self._run([binaries["check"], calendar], testdir)
            ok = rc == 0 and "0 errors found." in output
            details.append("check-%s:%s" % (calendar, "pass" if ok else "fail"))
            passed += int(ok)

        rc, output = self._run(
            [binaries["test"]], testdir, input_text="gre\n1\n1\n2000\n"
        )
        ok = rc == 0 and "Date in Gregorianic system: 1.1.2000" in output
        details.append("test:%s" % ("pass" if ok else "fail"))
        passed += int(ok)

        rc, output = self._run(
            [binaries["test1"]], testdir, input_text="gre\n29\n2\n2000\n"
        )
        ok = rc == 0 and "Date in Gregorianic system: 29.2.2000" in output
        details.append("test1:%s" % ("pass" if ok else "fail"))
        passed += int(ok)

        rc, output = self._run([binaries["test-dw"]], testdir)
        ok = rc == 0 and all(
            "--->%s<--" % day in output
            for day in ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")
        )
        details.append("test-dw:%s" % ("pass" if ok else "fail"))
        passed += int(ok)

        failed = discovered - passed
        marker = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "upstream-makefile/direct-exec",
            "command": "; ".join(details), "discovered": discovered,
            "executed": discovered, "passed": passed, "failed": failed, "skipped": 0,
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker), flush=True)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if failed:
            raise ConanException("libkal upstream tests failed: %s" % marker)

    def package(self):
        objdir = os.path.join(self.build_folder, "obj")
        copy(self, "libkal.a", src=objdir, dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        for header in self._public_headers:
            copy(self, header, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["kal"]
        self.cpp_info.set_property("cmake_file_name", "libkal")
        self.cpp_info.set_property("cmake_target_name", "libkal::libkal")
        self.cpp_info.set_property("pkg_config_name", "libkal")
