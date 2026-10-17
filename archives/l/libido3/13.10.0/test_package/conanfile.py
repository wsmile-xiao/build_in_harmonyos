#!/usr/bin/env python3
"""Conan test_package — libido3 13.10.0 consumer test.

Consumes the installed libido3-0.1.pc through pkg_check_modules (the .pc
Requires: gtk+-3.0 chain propagates the transitive include/lib paths; E216
avoids CMakeDeps component-header breakage). test.c performs 5 checks and
prints one "checkN OK" line each; this harness captures stdout, counts the
OK lines and emits the HMBS_TEST_PACKAGE_RESULT machine-evidence marker
(exit code alone is not accepted as proof).

Widget checks run headless on the broadway backend served by broadwayd from
the gtk package (ayatana-ido/0.10.4-v2 precedent on this device).
"""
import json
import os
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment

# test.c performs exactly 5 checks, each printing one "checkN OK" line.
CONSUMER_CHECK_COUNT = 5


class Libido3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # E092: cmake 4.4.3 on this worker ships no Platform/HarmonyOS.cmake;
        # alias the target to Linux (OHOS shares the Linux kernel; the
        # consumer test has no OHOS-specific cmake branches).
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Experience-1 compiler guard: fall back to a PATH-resolved compiler
        # only when the pinned conf binary is absent or not executable.
        try:
            _exes = self.conf.get(
                "tools.build:compiler_executables", default=None
            )
        except Exception:
            _exes = None
        if isinstance(_exes, dict):
            _c = _exes.get("c")
            _cxx = _exes.get("cpp") or _exes.get("cxx") or _exes.get("c")
            for _key, _conf_val, _bare in (
                ("CMAKE_C_COMPILER", _c, "clang"),
                ("CMAKE_CXX_COMPILER", _cxx, "clang++"),
            ):
                if _conf_val and os.path.isfile(str(_conf_val)):
                    continue
                _which = shutil.which(_bare)
                if _which:
                    tc.variables[_key] = _which

        # Deterministic pkg-config for pkg_check_modules: same probe order as
        # the main recipe, with the conan pkgconf tool package as the
        # guaranteed last candidate.
        pkg_bin = self._resolve_pkg_config_binary()
        shim_dir = os.path.join(self.build_folder, "hmbs-pkgconf-shim")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "pkg-config")
        fd = os.open(shim, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write('#!/bin/sh\nexec "%s" "$@"\n' % pkg_bin)
        try:
            os.chmod(shim, 0o755)
        except OSError:
            pass
        tc.variables["PKG_CONFIG_EXECUTABLE"] = shim

        # PKG_CONFIG_PATH: real dependency .pc dirs first, mirrors last.
        pc_dirs = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for sub in ("lib/pkgconfig", "lib64/pkgconfig", "share/pkgconfig"):
                d = os.path.join(dep.package_folder, sub)
                if os.path.isdir(d) and d not in pc_dirs:
                    pc_dirs.append(d)
        try:
            gens = self.generators_folder
            if gens and os.path.isdir(gens) and gens not in pc_dirs:
                pc_dirs.append(gens)
        except Exception:
            pass
        if pc_dirs:
            env = Environment()
            env.define("PKG_CONFIG_PATH", os.pathsep.join(pc_dirs))
            env.vars(self).save_script("hmbs_pkgconfig_path")
        tc.generate()

        # The published glib package's glib-2.0.pc lacks -lintl while
        # libgtk-3/libgio-2.0 reference g_libintl_*; append -lintl to the
        # generated glib-2.0.pc Libs or the test link fails under
        # --no-allow-shlib-undefined (gtk/3.24.43 + ayatana-ido precedent).
        pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.isfile(pc):
            content = open(pc, encoding="utf-8").read()
            lines = []
            for line in content.splitlines(keepends=True):
                if line.startswith("Libs:") and "-lintl" not in line.split():
                    line = line.rstrip("\r\n") + " -lintl\n"
                lines.append(line)
            new_content = "".join(lines)
            if new_content != content:
                open(pc, "w", encoding="utf-8", newline="\n").write(new_content)

    def _resolve_pkg_config_binary(self):
        import subprocess as _sp

        conf_val = None
        try:
            conf_val = self.conf.get("tools.gnu:pkg_config", default=None)
        except Exception:
            conf_val = None
        pkgconf_pkg_bin = ""
        try:
            for dep in self.dependencies.values():
                if dep.ref.name == "pkgconf" and dep.package_folder:
                    cand = os.path.join(dep.package_folder, "bin", "pkgconf")
                    if os.path.isfile(cand):
                        pkgconf_pkg_bin = cand
                    break
        except Exception:
            pass
        candidates = [
            conf_val,
            os.environ.get("PKG_CONFIG"),
            shutil.which("pkg-config"),
            shutil.which("pkgconf"),
            "/data/service/hnp/bin/pkg-config",
            "/data/service/hnp/bin/aarch64-unknown-linux-ohos-pkg-config",
            pkgconf_pkg_bin,
        ]
        for cand in candidates:
            if not cand or not os.path.isfile(str(cand)):
                continue
            try:
                p = _sp.run(
                    [str(cand), "--version"],
                    stdout=_sp.PIPE,
                    stderr=_sp.STDOUT,
                    text=True,
                    timeout=10,
                    check=False,
                )
            except Exception:
                continue
            if p.returncode == 0 and (p.stdout or "").strip():
                return str(cand)
        raise ConanException("no runnable pkg-config/pkgconf binary found")

    def build(self):
        # E002: keep cmake/clang temp files off read-only /tmp.
        _tmp = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
        )
        if not (_tmp and os.path.isdir(_tmp)):
            _tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(_tmp, exist_ok=True)
            os.environ["TMPDIR"] = _tmp
            os.environ["TMP"] = _tmp
            os.environ["TEMP"] = _tmp
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Make every transitive shared library reachable at runtime by
        # injecting all dependency libdirs into LD_LIBRARY_PATH (gtk/pango/
        # cairo pull libsharpyuv/libatk/libintl/... — ayatana-ido precedent).
        dep_libdirs = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(libdir):
                    dep_libdirs.append(libdir)
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            dep_libdirs + ([existing] if existing else [])
        )
        self.output.info(
            "injected LD_LIBRARY_PATH: %d dep libdirs" % len(dep_libdirs)
        )

        # Headless environment: serve the broadway backend with broadwayd
        # from the gtk package, else gtk_init fails with "cannot open
        # display".
        broadwayd = None
        proc = None
        gtk_pkg = self.dependencies.get("gtk")
        if gtk_pkg and gtk_pkg.package_folder:
            broadwayd = os.path.join(gtk_pkg.package_folder, "bin", "broadwayd")
        if broadwayd and os.path.isfile(broadwayd):
            proc = subprocess.Popen(
                [broadwayd, ":5"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for _ in range(10):
                if proc.poll() is not None:
                    break
                time.sleep(0.5)
            if proc.poll() is None:
                os.environ["GDK_BACKEND"] = "broadway"
                os.environ["BROADWAY_DISPLAY"] = ":5"
            else:
                self.output.warning(
                    "broadwayd not ready (rc=%s); display may be unavailable"
                    % proc.returncode
                )
                proc = None
        try:
            bin_path = os.path.join(
                self.cpp.build.bindirs[0], "test_libido3"
            )
            if not os.path.isfile(bin_path):
                raise ConanException("test binary missing: %s" % bin_path)
            run = subprocess.run(
                [bin_path],
                env=dict(os.environ),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=300,
            )
            output = run.stdout or ""
            self.output.info(output[-2000:])
            ok_count = len(
                [ln for ln in output.splitlines() if " OK: " in ln]
            )
            marker = {
                "executed": True,
                "passed": run.returncode == 0
                and ok_count == CONSUMER_CHECK_COUNT,
                "command": bin_path,
                "discovered": CONSUMER_CHECK_COUNT,
                "passedCount": ok_count,
            }
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT="
                + json.dumps(marker, ensure_ascii=False)
            )
            if not marker["passed"]:
                raise ConanException(
                    "consumer test failed: rc=%s ok=%s/%s"
                    % (run.returncode, ok_count, CONSUMER_CHECK_COUNT)
                )
            # L0d quality gate: prove the binary also executes under the
            # conanrun environment while broadwayd is still serving.
            self.run(bin_path, env="conanrun")
        finally:
            if proc is not None:
                proc.terminate()
