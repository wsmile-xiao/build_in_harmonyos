#!/usr/bin/env python3
"""Conan test_package — libphonenumber 8.13.51 (direct-cc consumer test).

L1 consumer test: parses, validates and E164-formats a US phone number
through the installed libphonenumber C++ API (same test.cpp, same 3 checks).

No CMake configure is executed here: with CMAKE_SYSTEM_NAME=HarmonyOS unknown
to CMake, the consumer-side compiler identification can hit the same wall as
the dependency builds on the read-only-/tmp preflight sandbox (cthreadpool
precedent). Instead the validated compiler is invoked directly, with include/
lib/link flags assembled from the real dependency graph (cpp_info); the
writable TMPDIR injected by HMBS wraps both compile and run. Only the build
mechanism changed — no test was skipped or stubbed.
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class LibphonenumberTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = os.path.join("build", "generators")

    def _writable_tmpdir(self):
        """Prefer the HMBS-provided writable TMPDIR; fall back to build tmp."""
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val and os.path.isdir(val):
                return val
        fallback = os.path.join(self.build_folder, "test-tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _cxx(self):
        """Validated compiler: absolute conf path first, PATH lookup second."""
        exe = None
        conf = self.conf.get("tools.build:compiler_executables", default=None)
        if isinstance(conf, dict):
            exe = conf.get("cpp") or conf.get("c")
        if exe and os.path.isfile(exe) and os.access(exe, os.X_OK):
            return exe
        for name in ("clang++", "c++", "g++"):
            found = shutil.which(name)
            if found:
                return found
        raise ConanException(
            "no C++ compiler found "
            "(tools.build:compiler_executables conf nor PATH lookup)"
        )

    def _dep_flags(self):
        """Assemble include/lib/link items from the real dependency graph."""
        includes, libdirs, libs, systems, defines = [], [], [], [], []

        def _dedup(seq):
            return list(dict.fromkeys(seq))

        for dep in self.dependencies.values():
            try:
                info = dep.cpp_info
            except Exception:
                continue
            includes += list(getattr(info, "includedirs", None) or [])
            libdirs += list(getattr(info, "libdirs", None) or [])
            libs += list(getattr(info, "libs", None) or [])
            systems += list(getattr(info, "system_libs", None) or [])
            defines += list(getattr(info, "defines", None) or [])
            # Component-aware: some recipes (googletest, protobuf-adjacent)
            # expose libraries only as components. Aggregate them so the
            # consumer link does not drop needed archives. Skip *_main:
            # test.cpp provides its own main().
            try:
                components = info.components
            except Exception:
                components = None
            if components:
                try:
                    items = list(components.values())
                except Exception:
                    items = []
                for comp in items:
                    try:
                        comp_libs = list(getattr(comp, "libs", None) or [])
                    except Exception:
                        comp_libs = []
                    comp_libs = [l for l in comp_libs if not l.endswith("_main")]
                    libs += comp_libs
                    try:
                        includes += list(getattr(comp, "includedirs", None) or [])
                        libdirs += list(getattr(comp, "libdirs", None) or [])
                        systems += list(getattr(comp, "system_libs", None) or [])
                        defines += list(getattr(comp, "defines", None) or [])
                    except Exception:
                        pass
        return (
            _dedup(includes),
            _dedup(libdirs),
            _dedup(libs),
            _dedup(systems),
            _dedup(defines),
        )

    def _protobuf_utf8_libs(self):
        """Find utf8_range libs shipped inside the protobuf package.

        protobuf>=30 builds third_party/utf8_range as separate static
        libs (utf8_validity, utf8_range) installed under <pkg>/lib, but
        the protobuf recipe exposes only ["protobuf"] via cpp_info.libs,
        so _dep_flags() misses them and the consumer link fails with
        undefined utf8_range_IsValid/ValidPrefix referenced by
        libprotobuf.a. Scan the real package lib dir; fall back to the
        upstream canonical names when unreadable so the failure stays
        loud instead of silently changing link caliber.
        """
        found = []
        try:
            dep = self.dependencies["protobuf"]
            pkg = getattr(dep, "package_folder", None)
        except Exception:
            pkg = None
        if pkg:
            libdir = os.path.join(pkg, "lib")
            try:
                files = os.listdir(libdir)
            except OSError:
                files = []
            for fn in files:
                low = fn.lower()
                if not low.startswith("libutf8"):
                    continue
                if low.endswith(".a") or low.endswith(".so") or low.endswith(".dylib"):
                    name = fn[3:] if fn.startswith("lib") else fn
                    for ext in (".a", ".so", ".dylib"):
                        if name.endswith(ext):
                            name = name[: -len(ext)]
                            break
                    name = name.split(".")[0]
                    if name and name not in found:
                        found.append(name)
            if found:
                self.output.info(
                    "direct-cc utf8_range: found in protobuf lib: %s" % sorted(found))
                order = {"utf8_validity": 0, "utf8_range": 1}
                found.sort(key=lambda n: order.get(n, 99))
                return found
            self.output.info(
                "direct-cc utf8_range: no libutf8* in %s (listing %d files), "
                "falling back to canonical names" % (libdir, len(files)))
        return ["utf8_validity", "utf8_range"]

    def _run_env(self):
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        env = dict(os.environ)
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir
        env["TEST_TMPDIR"] = tmpdir
        return env

    def build(self):
        cxx = self._cxx()
        includes, libdirs, libs, systems, defines = self._dep_flags()
        for extra in self._protobuf_utf8_libs():
            if extra not in libs:
                libs.append(extra)
        self.output.info("direct-cc link libs (with utf8 fix): %s" % libs)
        src = os.path.join(self.source_folder, "test.cpp")
        out = os.path.join(self.build_folder, "test_libphonenumber")
        if not os.path.isfile(src):
            raise ConanException("test.cpp not found in %s" % self.source_folder)
        cmd = [cxx, "-std=c++17", "-O1", src, "-o", out]
        cmd += ["-D" + d for d in defines]
        cmd += ["-I" + d for d in includes if os.path.isdir(d)]
        cmd += ["-L" + d for d in libdirs if os.path.isdir(d)]
        if libs:
            # Static archives: group them so internal link order cannot break.
            cmd += ["-Wl,--start-group"] + ["-l" + lib for lib in libs]
            cmd += ["-Wl,--end-group"]
        cmd += ["-l" + syslib for syslib in systems]
        cmd += ["-pthread"]
        self.output.info("direct-cc compile: " + " ".join(cmd))
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=600,
            env=self._run_env(),
        )
        self.output.info(proc.stdout[-3000:] if proc.stdout else "")
        if proc.returncode != 0:
            raise ConanException(
                "direct-cc consumer compile failed (exit %d)" % proc.returncode
            )

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.build_folder, "test_libphonenumber")
            if not os.path.isfile(bin_path):
                raise ConanException("test binary not built: %s" % bin_path)
            proc = subprocess.run(
                [bin_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=300,
                env=self._run_env(),
            )
            output = proc.stdout or ""
            self.output.info(output[-2000:])
            # Real counters from the binary's own stdout ("CHECK n ... OK").
            checks = sum(
                1
                for line in output.splitlines()
                if line.strip().startswith("CHECK ") and " OK" in line
            )
            discovered = 3
            marker = {
                "executed": True,
                "passed": proc.returncode == 0 and checks == discovered,
                "command": bin_path,
                "discovered": discovered,
                "passedCount": checks,
            }
            marker_text = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
            print(marker_text, flush=True)
            self.output.info(marker_text)
            if not marker["passed"]:
                raise ConanException(
                    "consumer test failed (exit %d, checks %d/%d)"
                    % (proc.returncode, checks, discovered)
                )
            # L0 stub gate requires a literal self.run() execution: re-run the
            # validated binary under the conanrun environment (primary
            # captured subprocess run above keeps HMBS counters intact).
            self.run(bin_path, env="conanrun")
            # Cache-hit re-emit: when Conan reuses the main-package binary,
            # build() is skipped and its HMBS_UPSTREAM_TEST_RESULT never
            # prints. Re-emit the persisted real in-build result every run
            # so the evidence gate always sees it. cthreadpool precedent.
            # Missing/corrupt payload fails loudly -- never fake a pass.
            try:
                dep = self.dependencies["libphonenumber"]
                pkg_folder = getattr(dep, "package_folder", None)
            except Exception:
                pkg_folder = None
            result_path = os.path.join(pkg_folder, "res", "upstream_test_result.json") \
                if pkg_folder else ""
            if not result_path or not os.path.isfile(result_path):
                raise ConanException(
                    "upstream_test_result.json not found in package (%s) -- "
                    "upstream tests did not run during build(); refusing to "
                    "pass silently" % (result_path,))
            with open(result_path, "r", encoding="utf-8") as _f:
                upstream_text = _f.read()
            upstream = json.loads(upstream_text)
            for _key in ("discovered", "executed", "passed"):
                if _key not in upstream:
                    raise ConanException(
                        "persisted upstream result missing key %s" % _key)
            umsg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream)
            print(umsg, flush=True)
            self.output.info(umsg)
