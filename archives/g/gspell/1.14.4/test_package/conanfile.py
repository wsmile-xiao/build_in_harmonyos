#!/usr/bin/env python3
"""Conan test_package for gspell 1.14.4.

The consumer program is built with pkg-config (`pkg_check_modules(gspell-1)`)
so that the whole Requires: gio-2.0 gtk+-3.0 enchant-2 chain coming out of the
installed gspell-1.pc is exercised — that is exactly what a downstream project
on OHOS would do.

test() runs the binary for real.  It is a GTK program (gtk_init), so it runs on
the headless **broadway** GDK backend served by broadwayd from the gtk package
(same technique as ayatana-ido/0.10.4-v2).  The TAP lines printed by the test
binary are parsed, so "the test passed" means "N assertions executed and all of
them held", not "the process exited 0 without doing anything".
"""
import glob
import os
import re
import subprocess
import time

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment

BROADWAY_DISPLAY = ":5"


class GspellTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _sdk_llvm_libdir(self):
        """Locate the active OHOS SDK llvm/lib that ships libc++_shared.so.

        The test_package's cmake is a C++ program (DT_NEEDED libc++_shared.so)
        and lives in <sdk>/llvm/lib/aarch64-linux-ohos/.  The CI shell prepends
        ~/usr/local/lib, which shadows the ABI-matching copy, so the directory
        is probed and put on LD_LIBRARY_PATH (same as gtkspell3).
        """
        if str(self.settings.os) != "OHOS":
            return ""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp") or compilers.get("c")
        candidates = []
        if cxx:
            try:
                resource_dir = subprocess.check_output(
                    [cxx, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL, text=True).strip()
                candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
            except (OSError, subprocess.CalledProcessError):
                pass
            compiler = os.path.realpath(cxx)
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib"))
        expanded = []
        for cand in dict.fromkeys(candidates):
            expanded.append(cand)
            sub = os.path.join(cand, "aarch64-linux-ohos")
            if os.path.isdir(sub):
                expanded.append(sub)
        for cand in dict.fromkeys(expanded):
            if os.path.isfile(os.path.join(cand, "libc++_shared.so")):
                return cand
        return ""

    def _resolved_lib_dirs(self):
        dirs = []
        for dependency in self.dependencies.values():
            if not getattr(dependency, "package_folder", None):
                continue
            for libdir in dependency.cpp_info.libdirs or []:
                if not libdir:
                    continue
                full = libdir if os.path.isabs(libdir) else os.path.join(
                    dependency.package_folder, libdir)
                if full not in dirs:
                    dirs.append(full)
        # OHOS HNP layout helper: transitive runtime libs (pcre2/ffi/expat/
        # intl/epoxy) live under /data/service/hnp/*/*/lib.
        for pattern in ("libpcre2-8.so*", "libffi.so*", "libexpat.so*",
                        "libintl.so*", "libepoxy.so*"):
            for match in glob.glob("/data/service/hnp/*/*/lib/{}".format(pattern)):
                libdir = os.path.dirname(match)
                if libdir not in dirs:
                    dirs.append(libdir)
        return dirs

    def _env(self):
        env = Environment()
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            self.output.info("Prepending OHOS SDK runtime path: {}".format(sdk_llvm_lib))
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        for dependency in self.dependencies.values():
            if not getattr(dependency, "package_folder", None):
                continue
            for libdir in dependency.cpp_info.libdirs or []:
                if not libdir:
                    continue
                full = libdir if os.path.isabs(libdir) else os.path.join(
                    dependency.package_folder, libdir)
                env.prepend_path("LD_LIBRARY_PATH", full)
                env.prepend_path("PKG_CONFIG_PATH", os.path.join(full, "pkgconfig"))
        for libdir in self._resolved_lib_dirs():
            env.prepend_path("LD_LIBRARY_PATH", libdir)
        return env

    def _broadway_env(self):
        """Start broadwayd; return (env, process)."""
        env = self._env()
        proc = None
        gtk_pkg = self.dependencies.get("gtk")
        if gtk_pkg is not None and gtk_pkg.package_folder:
            broadwayd = os.path.join(gtk_pkg.package_folder, "bin", "broadwayd")
            if os.path.isfile(broadwayd):
                libdirs = self._resolved_lib_dirs()
                run_env = dict(os.environ)
                sdk_llvm_lib = self._sdk_llvm_libdir()
                parts = ([sdk_llvm_lib] if sdk_llvm_lib else []) + libdirs
                if parts:
                    run_env["LD_LIBRARY_PATH"] = ":".join(
                        parts + [run_env.get("LD_LIBRARY_PATH", "")]
                    ).strip(":")
                proc = subprocess.Popen([broadwayd, BROADWAY_DISPLAY],
                                        env=run_env,
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL)
                for _ in range(20):
                    if proc.poll() is not None:
                        break
                    time.sleep(0.5)
                if proc.poll() is None:
                    env.define("GDK_BACKEND", "broadway")
                    env.define("BROADWAY_DISPLAY", BROADWAY_DISPLAY)
                else:
                    self.output.warning(
                        "broadwayd exited early (rc=%s); running the consumer "
                        "test without a display backend" % proc.returncode)
                    proc = None
        return env, proc

    def build(self):
        envvars = self._env().vars(self)
        with envvars.apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise RuntimeError("test_gspell executable directory was not produced")
        exe = os.path.join(bindirs[0], "test_gspell")
        if not os.path.isfile(exe):
            raise RuntimeError("test_gspell binary missing: {}".format(exe))

        required = (
            "libgspell-1.so.3",
            "libgtk-3.so.0",
            "libgdk-3.so.0",
            "libenchant-2.so.2",
            "libglib-2.0.so.0",
        )
        lib_dirs = self._resolved_lib_dirs()
        missing = [lib for lib in required
                   if not any(os.path.isfile(os.path.join(d, lib))
                              for d in lib_dirs if d)]
        if missing:
            raise RuntimeError(
                "gspell runtime libs missing from the dependency graph; the "
                "consumer assertions would not execute: {}".format(missing))

        env, broadwayd_proc = self._broadway_env()
        log = os.path.join(self.build_folder, "test_gspell.tap")
        run_error = None
        try:
            envvars = env.vars(self)
            with envvars.apply():
                self.run('"{}" > "{}" 2>&1'.format(exe, log), env="conanrun")
        except Exception as exc:      # re-raised below, after the TAP log is shown
            run_error = exc
        finally:
            if broadwayd_proc is not None and broadwayd_proc.poll() is None:
                broadwayd_proc.terminate()

        try:
            with open(log, encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        self.output.info("----- test_gspell TAP -----\n{}".format(out))

        ok = len(re.findall(r"^ok\b", out, re.M))
        not_ok = len(re.findall(r"^not ok\b", out, re.M))
        plan = re.search(r"^1\.\.(\d+)\s*$", out, re.M)
        expected = int(plan.group(1)) if plan else 0
        if run_error is not None or expected < 1 or ok != expected or not_ok != 0:
            raise RuntimeError(
                "consumer assertions did not all pass ({}): plan={} ok={} not_ok={}\n{}"
                .format(run_error, expected, ok, not_ok, out))
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT={{\"status\": \"passed\", \"assertions\": {}}}"
            .format(ok))
