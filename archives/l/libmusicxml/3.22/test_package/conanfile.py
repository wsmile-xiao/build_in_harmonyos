#!/usr/bin/env python3
"""Conan test_package for libmusicxml 3.22 — substantively exercises the API.

The test program calls musicxmllibVersion/musicxmllibVersionStr and converts
a minimal MusicXML score with musicxmlstring2guido (4 checks, R34).
Upstream validation-harness (xmlread+xml2guido over files/*.xml, see
MANIFEST.yml audit) runs in build(); this recipe re-emits its persisted
measurement after the consumer test.

emits:
  HMBS_TEST_PACKAGE_RESULT  — consumer test result (4 checks)
  HMBS_UPSTREAM_TEST_RESULT — re-emit of build-time validation-harness result
"""

import json
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class LibmusicxmlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _writable_tmpdir(self):
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            d = os.environ.get(var)
            if d and os.path.isdir(d):
                try:
                    fd, p = tempfile.mkstemp(dir=d)
                    os.close(fd)
                    os.unlink(p)
                    return d
                except Exception:
                    continue
        d = os.path.join(self.build_folder, "tmp")
        os.makedirs(d, exist_ok=True)
        return d

    def _compiler_executable(self, key, fallback_name):
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            executables = {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        if found and os.path.isfile(found):
            return found
        return configured or fallback_name

    def _sdk_llvm_libdir(self):
        if str(self.settings.os) != "OHOS":
            return ""
        cc = self._compiler_executable("c", "clang")
        cc_resolved = shutil.which(cc) if not os.path.isabs(cc) else cc
        cc_resolved = cc_resolved or cc
        try:
            cc_real = os.path.realpath(cc_resolved)
        except Exception:
            cc_real = cc_resolved
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib")
        try:
            if os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
                return llvm_lib
        except Exception:
            pass
        return ""

    def _build_environment(self):
        env = Environment()
        tmp = self._writable_tmpdir()
        env.define("TMPDIR", tmp)
        env.define("TMP", tmp)
        env.define("TEMP", tmp)
        sdk_lib = self._sdk_llvm_libdir()
        if sdk_lib:
            env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        return env

    def _resolve_hmbs_tool(self, conf_key, env_var, basename):
        try:
            val = self.conf.get(conf_key, check_type=str)
            if val and os.path.isfile(val):
                return val
        except Exception:
            pass
        env_val = os.environ.get(env_var)
        if env_val and os.path.isfile(env_val):
            return env_val
        found = shutil.which(basename)
        if found and os.path.isfile(found):
            return found
        return env_val or basename

    def _conan_toolchain_file(self):
        try:
            path = os.path.join(self.generators_folder, "conan_toolchain.cmake")
            if os.path.isfile(path):
                return path
        except Exception:
            pass
        for root, _dirs, files in os.walk(self.build_folder):
            if "conan_toolchain.cmake" in files:
                return os.path.join(root, "conan_toolchain.cmake")
        return "conan_toolchain.cmake"

    def _run_direct(self, argv, cwd=None, extra_env=None):
        run_env = dict(os.environ)
        tmp = self._writable_tmpdir()
        run_env["TMPDIR"] = tmp
        run_env["TMP"] = tmp
        run_env["TEMP"] = tmp
        if extra_env:
            run_env.update(extra_env)
        self.output.info("noshell: {}".format(" ".join(str(a) for a in argv)))
        proc = subprocess.run(
            list(argv),
            env=run_env,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.stdout:
            self.output.info(proc.stdout)
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, list(argv))
        return proc

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_C_COMPILER"] = self._compiler_executable("c", "clang")
            tc.variables["CMAKE_CXX_COMPILER"] = self._compiler_executable("cpp", "clang++")
        tc.generate()
        VirtualRunEnv(self).generate()
        self._build_environment().vars(self, scope="build").save_script("hmbs_env")

    def build(self):
        # readonly_tmp: same as the main recipe — Conan's CMake helper goes
        # via /bin/sh -c (needs /tmp/sh*.tmp). Configure/build the consumer
        # with a direct list-form cmake exec and forwarded TMPDIR.
        tmp = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        cmake_bin = self._resolve_hmbs_tool("user.hmbs:cmake_path", "HMBS_CMAKE", "cmake")
        make_bin = self._resolve_hmbs_tool("user.hmbs:make_path", "HMBS_MAKE", "make")
        toolchain = self._conan_toolchain_file()
        build_dir = os.path.join(self.build_folder, "hmbs_build")
        os.makedirs(build_dir, exist_ok=True)
        with self._build_environment().vars(self).apply():
            self._run_direct([
                cmake_bin,
                "-S", self.source_folder,
                "-B", build_dir,
                "-G", "Unix Makefiles",
                "-DCMAKE_TOOLCHAIN_FILE={}".format(toolchain),
                "-DCMAKE_BUILD_TYPE={}".format(str(self.settings.build_type)),
                "-DCMAKE_MAKE_PROGRAM={}".format(make_bin),
            ])
            self._run_direct([cmake_bin, "--build", build_dir, "--config", str(self.settings.build_type), "--parallel", "1"])
            # Remember the actual consumer build dir for test().
            try:
                with open(os.path.join(self.build_folder, "hmbs_test_build_dir.txt"), "w", encoding="utf-8") as f:
                    f.write(build_dir)
            except Exception:
                pass

    def _emit_line(self, line):
        # Dual-channel (experience 2, apply): conan channel + plain stdout.
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass

    def _load_upstream_result(self):
        # Re-emit must source from the build-time persisted file inside the
        # tested package (never re-typed). Fail hard when absent/invalid so
        # a missing measurement can never become a silent no_tests pass.
        candidates = []
        try:
            for dep in self.dependencies.values():
                try:
                    base = dep.package_folder
                except Exception:
                    continue
                if base:
                    candidates.append(
                        os.path.join(base, "share", "libmusicxml", "upstream_test_result.json")
                    )
        except Exception:
            pass
        for path in candidates:
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                for key in ("discovered", "executed", "passed"):
                    if int(payload.get(key, 0)) <= 0:
                        raise ConanInvalidConfiguration(
                            "persisted upstream result has non-positive {}: {}".format(key, path)
                        )
                if payload.get("status") != "passed" or int(payload.get("failed", 1)) != 0:
                    raise ConanInvalidConfiguration(
                        "persisted upstream result is not a clean pass: {}".format(path)
                    )
                return payload
        raise ConanInvalidConfiguration(
            "upstream result JSON missing from libmusicxml package (share/libmusicxml/upstream_test_result.json); "
            "build() must run validation-harness before test()"
        )

    def test(self):
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "./test_musicxml",
            "discovered": 4,
            "passedCount": 4,
        }
        if not can_run(self):
            self.output.info("cross-building: consumer linked but cannot run on this host")
            return
        tmp = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        if self.settings.os == "OHOS":
            self._sign_test_binary()
        # noshell exec: self.run() goes via /bin/sh -c (needs /tmp/sh*.tmp);
        # run the consumer binary directly with forwarded TMPDIR and an
        # explicit LD_LIBRARY_PATH covering the tested package + deps.
        try:
            test_bin = self._locate_test_binary()
            run_extra = dict(self._test_run_extra_env())
            self._run_direct([test_bin], extra_env=run_extra)
        except Exception as exc:
            test_pkg["passed"] = False
            test_pkg["passedCount"] = 0
            self._emit_line("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            raise
        self._emit_line("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        # Upstream suite ran in build() (validation-harness over files/*.xml);
        # re-emit the exact persisted measurement after the consumer command.
        upstream = self._load_upstream_result()
        self._emit_line("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

    def _locate_test_binary(self):
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        name = "test_musicxml" + suffix
        candidates = []
        try:
            with open(os.path.join(self.build_folder, "hmbs_test_build_dir.txt"), "r", encoding="utf-8") as f:
                candidates.append(os.path.join(f.read().strip(), name))
        except Exception:
            pass
        candidates.append(os.path.join(self.build_folder, "hmbs_build", name))
        try:
            candidates.append(os.path.join(self.cpp.build.bindirs[0], name))
        except Exception:
            pass
        for root, _dirs, files in os.walk(self.build_folder):
            if name in files:
                candidates.append(os.path.join(root, name))
        for path in candidates:
            if path and os.path.isfile(path):
                return path
        return candidates[0]

    def _test_run_extra_env(self):
        lib_paths = []
        try:
            for dep in self.dependencies.values():
                try:
                    for d in dep.cpp_info.libdirs:
                        if os.path.isdir(d):
                            lib_paths.append(d)
                except Exception:
                    continue
        except Exception:
            pass
        sdk_lib = self._sdk_llvm_libdir()
        if sdk_lib:
            lib_paths.append(sdk_lib)
        if not lib_paths:
            return {}
        old = os.environ.get("LD_LIBRARY_PATH", "")
        combined = ":".join(lib_paths) + (":" + old if old else "")
        return {"LD_LIBRARY_PATH": combined}

    def _sign_test_binary(self):
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        paths = [self._locate_test_binary()]
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy and binary-sign-tool"
            )
        for path in paths:
            if os.path.isfile(path):
                self._sign_elf_atomically(path, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        try:
            original_mode = os.stat(path).st_mode
        except OSError:
            original_mode = None
        temporary = "{}.signing".format(path)
        try:
            shutil.copy2(path, temporary)
            self._run_direct([objcopy, "--remove-section", ".codesign", temporary])
            self._run_direct(
                [signer, "sign", "-inFile", temporary, "-outFile", temporary, "-selfSign", "1"]
            )
            if original_mode is not None:
                try:
                    os.chmod(temporary, original_mode)
                except OSError as exc:
                    self.output.warning("chmod on {} failed (ignored): {}".format(temporary, exc))
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        try:
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        except Exception:
            compilers = {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = (
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        )
        return next((path for path in candidates if path and os.path.isfile(path)), "")
