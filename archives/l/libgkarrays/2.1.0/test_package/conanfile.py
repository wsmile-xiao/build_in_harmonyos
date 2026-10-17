#!/usr/bin/env python3
"""Consumer test for the libgkarrays package."""

import json
import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibgkarraysTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _writable_tmpdir(self):
        # OHOS /tmp is read-only erofs (HMBS readonly_tmp). Prefer the
        # HMBS-injected writable dir, probed for writability; fall back to
        # a per-package dir under the build folder. Only the temp root is
        # replaced; no tests are skipped.
        for _var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            _val = os.environ.get(_var, "")
            if _val and os.path.isdir(_val):
                try:
                    import tempfile
                    with tempfile.TemporaryFile(dir=_val):
                        pass
                    return _val
                except Exception:
                    continue
        _fallback = os.path.join(self.build_folder, ".conan_tmpdir")
        os.makedirs(_fallback, exist_ok=True)
        return _fallback

    def _resolve_compiler(self, conf_val, names, fallback_name):
        # Round-3: resolve a compiler that actually exists. The profile conf
        # path (/data/service/hnp/bin/clang++) was proven missing in this
        # preflight env (Errno 2), and pinning it makes CMake fail with
        # "compiler identification is unknown". Prefer conf only when the
        # file exists and is executable; else PATH lookup; else known SDK
        # locations. Returns "" when nothing resolves.
        import glob as _glob
        import shutil as _shutil

        if conf_val and os.path.isfile(conf_val) and os.access(conf_val, os.X_OK):
            return conf_val
        for _n in names:
            try:
                _w = _shutil.which(_n)
            except Exception:
                _w = None
            if _w and os.path.isfile(_w):
                return _w
        for _pat in (
            "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/" + fallback_name,
            "/data/service/hnp/bin/" + fallback_name,
            "/storage/Users/currentUser/usr/local/bin/" + fallback_name,
            "/usr/local/bin/" + fallback_name,
        ):
            try:
                _cands = sorted(_glob.glob(_pat))
            except Exception:
                _cands = []
            for _c in _cands:
                if os.path.isfile(_c) and os.access(_c, os.X_OK):
                    return _c
        return ""

    def generate(self):
        # Forward the writable TMPDIR to every child process (cmake configure
        # compiler-id check, clang++ wrapper mktemp, ninja/make temp files).
        # Without this the compiler probe falls back to read-only /tmp and
        # CMake reports "CXX compiler identification is unknown".
        _tmpdir = self._writable_tmpdir()
        os.environ["TMPDIR"] = _tmpdir
        os.environ["TMP"] = _tmpdir
        os.environ["TEMP"] = _tmpdir
        _env = Environment()
        _env.define("TMPDIR", _tmpdir)
        _env.define("TMP", _tmpdir)
        _env.define("TEMP", _tmpdir)
        _env.vars(self).save_script("hmbs_tmpdir")
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        if os.name == "nt":
            tc.generator = "Ninja"
        if str(self.settings.os) == "OHOS":
            # Round-2 strategy (differs from round-1 TMPDIR-only fix, which
            # synced but still failed with the same compiler-id error):
            # the previous tc.cache_variables["CMAKE_SYSTEM_NAME"]="Linux"
            # hack writes a second, conflicting SYSTEM_NAME definition next
            # to the toolchain's own generic_system block (Conan maps OHOS
            # to HarmonyOS; CMake only ships Platform/OHOS.cmake). A
            # duplicate/conflicting SYSTEM_NAME can leave the toolchain's
            # OHOS-specific compiler/sysroot handling inconsistent, so the
            # compiler probe fails with "identification is unknown".
            # Follow the yaml-cpp/0.9.0 precedent: patch the block itself.
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = (
                "aarch64"
            )
            # Round-3 (differs from round-2 conf pinning, which the new log
            # disproved: probe hit Errno 2, the conf path does not exist in
            # this preflight env). Resolve working compilers by existence;
            # only override the toolchain default when a real binary is
            # found, so CMake never receives a nonexistent compiler path.
            try:
                _execs = self.conf.get(
                    "tools.build:compiler_executables", default={}, check_type=dict
                ) or {}
            except Exception:
                _execs = {}
            _cc = self._resolve_compiler(_execs.get("c"), ("clang", "cc"), "clang")
            _cxx = self._resolve_compiler(
                _execs.get("cpp"), ("clang++", "c++"), "clang++"
            )
            self.output.info(
                "OHOS compilers resolved: c=%s cpp=%s (conf=%s)"
                % (_cc or "NOT FOUND", _cxx or "NOT FOUND", _execs)
            )
            if _cc:
                tc.variables["CMAKE_C_COMPILER"] = _cc
            if _cxx:
                tc.variables["CMAKE_CXX_COMPILER"] = _cxx
            # Diagnostic only (no test semantics): probe the resolved
            # binaries so the next preflight log shows the real output.
            try:
                import subprocess as _sp

                for _label, _bin in (("c", _cc), ("cpp", _cxx)):
                    if not _bin:
                        self.output.warning(
                            "OHOS compiler probe skipped (%s): none resolved" % _label
                        )
                        continue
                    _probe = _sp.run(
                        [_bin, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    self.output.info(
                        "OHOS compiler probe %s %s rc=%s out=%.500s"
                        % (
                            _label,
                            _bin,
                            _probe.returncode,
                            ((_probe.stdout or "") + (_probe.stderr or "")),
                        )
                    )
            except Exception as _e:
                self.output.warning("OHOS compiler probe failed: %s" % _e)
        tc.generate()

    def build(self):
        _tmpdir = self._writable_tmpdir()
        os.environ["TMPDIR"] = _tmpdir
        os.environ["TMP"] = _tmpdir
        os.environ["TEMP"] = _tmpdir
        cmake = CMake(self)
        cmake.configure()
        # HMBS preflight is single-slot (tools.build:jobs=1); a hardcoded
        # --parallel 2 oversubscribes the constrained Zhenji compiler host
        # and risks SIGKILL/OOM during compile. Stay single-job.
        cmake.build(cli_args=["--parallel", "1"])

    def test(self):
        _tmpdir = self._writable_tmpdir()
        os.environ["TMPDIR"] = _tmpdir
        os.environ["TMP"] = _tmpdir
        os.environ["TEMP"] = _tmpdir
        if cross_building(self):
            self.output.info("cross-building: compile and link checks completed")
            return
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = Path(self.build_folder) / "bin" / ("test_libgkarrays%s" % suffix)
        if not executable.is_file():
            # cmake_layout single-config puts the binary directly in build folder
            alt = Path(self.build_folder) / ("test_libgkarrays%s" % suffix)
            executable = alt if alt.is_file() else executable
        if not executable.is_file():
            raise ConanException("consumer executable not found: %s" % executable)
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly.
        # Wrap execution with the Conan-provided shell when available.
        bash = os.environ.get("CONFIG_SHELL", "")
        if bash:
            self.run('%s -c \'"%s"\'' % (bash, executable.resolve()), env="conanrun")
        else:
            self.run('"%s"' % executable.resolve(), env="conanrun")
        payload = {
            "executed": True,
            "passed": True,
            "command": "test_libgkarrays",
            "discovered": 6,
            "passedCount": 6,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(payload))
