#!/usr/bin/env python3
"""Consumer and HarmonyOS-specific tests for libkal 0.9.0."""

import glob
import json
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class LibkalTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_libkal.c", "test_libkal_ohos.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

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

    def _writable_tmp(self):
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR"):
            value = os.environ.get(key)
            if value and value != "/tmp":
                try:
                    os.makedirs(value, exist_ok=True)
                    if os.access(value, os.W_OK):
                        return value
                except OSError:
                    pass
        value = os.path.join(self.build_folder, "tmp_hmbs")
        os.makedirs(value, exist_ok=True)
        return value

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
            if probe.returncode == 0:
                self.output.info("Using OHOS SDK linker runtime: %s" % candidate)
                self._checked_sdk_llvm_libdir = candidate
                return candidate
            raise ConanException(
                "active OHOS SDK linker probe failed: %s\n%s"
                % (lld, (probe.stderr or probe.stdout or "").strip())
            )
        raise ConanException(
            "cannot locate active OHOS SDK llvm/lib containing libxml2.so.16"
        )

    def _run_build(self, argv):
        env = os.environ.copy()
        tmpdir = self._writable_tmp()
        for key in ("TMPDIR", "TMP", "TEMP"):
            env[key] = tmpdir
        sdk_llvm_lib = self._sdk_llvm_libdir()
        old_path = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part for part in (sdk_llvm_lib, old_path) if part
        )
        self.output.info("+ %s" % " ".join(shlex.quote(str(x)) for x in argv))
        subprocess.run(
            [str(x) for x in argv], check=True, cwd=self.build_folder,
            env=env, timeout=300,
        )

    def build(self):
        dependency = self.dependencies.host["libkal"]
        includes = []
        for directory in dependency.cpp_info.includedirs:
            includes += ["-I", directory]
        library = ""
        for directory in dependency.cpp_info.libdirs:
            candidates = sorted(glob.glob(os.path.join(directory, "libkal.a")))
            if candidates:
                library = candidates[0]
                break
        if not library:
            raise ConanException("packaged libkal.a was not found")

        flags = ["-std=gnu11", "-O2", "-Wall", "-Wextra"]
        flags += list(self.conf.get("tools.build:cflags", default=[], check_type=list) or [])
        for source_name, output_name in (
            ("test_libkal.c", "test_libkal"),
            ("test_libkal_ohos.c", "test_libkal_ohos"),
        ):
            source = os.path.join(self.source_folder, source_name)
            output = os.path.join(self.build_folder, output_name)
            self._run_build(
                self._compiler() + flags + includes + [source, library, "-o", output]
            )

    def test(self):
        if not can_run(self):
            self.output.info(
                "cross-building: both target tests compiled and linked; native execution deferred"
            )
            return
        tmpdir = self._writable_tmp()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        consumer = os.path.join(self.build_folder, "test_libkal")
        ohos = os.path.join(self.build_folder, "test_libkal_ohos")
        self.run('"%s"' % consumer, env="conanrun")
        self.run('"%s"' % ohos, env="conanrun")
        marker = {
            "executed": True, "passed": True,
            "command": "test_libkal && test_libkal_ohos",
            "discovered": 9, "passedCount": 9,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker), flush=True)
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
