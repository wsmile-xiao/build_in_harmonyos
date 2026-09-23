#!/usr/bin/env python3
"""Conan test_package for knavalbattle 26.04.0 (consumer-side validation).

R34: genuinely exercises the packaged application. knavalbattle is a Qt6
Widgets GUI game (no public library/headers to link against), so the
consumer test runs the packaged bin/knavalbattle with `--version`
(KAboutData::setupCommandLine + QCommandLineParser::process print the
version string and exit 0 before any display/DBus/network service is
touched). A non-zero exit or an empty output means the binary could not
start at all (missing loader deps / broken ELF).

Runtime-linking notes (alligator 26.04.0 / E537 precedent):
  * several published KF6/KDEGames6 libraries carry build-tree-relative
    DT_NEEDED entries ("../../bin/libKF6*.so") which the OHOS loader
    resolves against the process CWD, and absolute conan-cache paths
    ("/storage/.../.cache/conan2/p/<hash>/p/lib/libKF6*.so" and even
    ".../p/b/<hash>/p/lib/..." build-folder paths) baked in on the build
    machine. The test therefore runs from a fresh scratch CWD whose
    ../../bin reaches a link farm of every dependency shared library, and
    every missing absolute DT_NEEDED target is materialized as a symlink
    to the real library in the matching package (accessibility 26.04.3 /
    calligra 24.12.3 precedent).
  * the host shell LD_LIBRARY_PATH carries whitespace-padded entries the
    OHOS loader cannot resolve, so the whole environment is rebuilt
    explicitly instead of relying on env="conanrun".
"""
import os
import re
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.env import Environment


class KnavalbattleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # openal-soft is a *transitive* runtime dependency of libkdegames
        # (libKDEGames6.so carries DT_NEEDED libopenal.so.1). The published
        # openal-soft recipe defaults shared=False, so Conan treats it as a
        # static lib and drops it from the test graph ("Skipped binaries",
        # package_folder=None) — without a direct requirement its lib dir is
        # never added to LD_LIBRARY_PATH and the packaged game cannot start.
        self.requires("openal-soft/1.25.2")

    def _find_readelf(self):
        for cand in (
            "readelf",
            "/data/service/hnp/bin/readelf",
            "/data/service/hnp/bin/llvm-readelf",
        ):
            try:
                w = shutil.which(cand)
                exe = w or cand
                subprocess.run([exe, "--version"], capture_output=True, timeout=20)
                return exe
            except (OSError, subprocess.SubprocessError):
                continue
        return None

    def _collect_libs(self):
        lib_dirs = []
        for p in self.dependencies.values():
            if p and p.package_folder:
                for layout_dir in ("lib", "bin"):
                    lib_dir = os.path.join(p.package_folder, layout_dir)
                    if os.path.isdir(lib_dir):
                        lib_dirs.append(lib_dir)
        return lib_dirs

    def _materialize_abs_deps(self):
        # Dependency libs carry absolute DT_NEEDED entries recorded from the
        # builder's conan home ("/storage/.../.cache/conan2/p/<hash>/p/lib/"
        # and ".../p/b/<hash>/p/lib/" build-folder paths). Symlink every
        # missing absolute dependency to the real library of the same
        # basename found in the dependency packages.
        readelf = self._find_readelf()
        if not readelf:
            self.output.warning("readelf not found; absolute DT_NEEDED materialization skipped")
            return
        self.output.info(f"readelf resolved: {readelf}")
        seen_libs = set()
        for lib_dir in self._collect_libs():
            for name in os.listdir(lib_dir):
                if not name.endswith(".so") or name in seen_libs:
                    continue
                seen_libs.add(name)
                lib_path = os.path.join(lib_dir, name)
                try:
                    rd = subprocess.run(
                        [readelf, "-d", lib_path],
                        capture_output=True, text=True, timeout=60,
                    ).stdout
                except OSError:
                    continue
                for m in re.finditer(r"Shared library: \[(/[^]]+\.so)\]", rd):
                    abs_path = m.group(1)
                    if os.path.exists(abs_path):
                        continue
                    fname = os.path.basename(abs_path)
                    for cand_dir in self._collect_libs():
                        cand = os.path.join(cand_dir, fname)
                        if os.path.exists(cand):
                            try:
                                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                                if not os.path.lexists(abs_path):
                                    os.symlink(cand, abs_path)
                            except OSError as exc:
                                self.output.warning(
                                    f"DT_NEEDED symlink fail {abs_path}: {exc}"
                                )
                            break

    def _make_scratch(self):
        # Fresh scratch CWD: <scratch>/a/b is the run CWD and <scratch>/bin
        # is the link farm, so ../../bin from the CWD reaches every
        # dependency shared library (relative DT_NEEDED resolution base).
        scratch = tempfile.mkdtemp(prefix="knavalbattle-test-")
        farm = os.path.join(scratch, "bin")
        cwd = os.path.join(scratch, "a", "b")
        os.makedirs(farm, exist_ok=True)
        os.makedirs(cwd, exist_ok=True)
        for lib_dir in self._collect_libs():
            for name in os.listdir(lib_dir):
                if not name.endswith(".so"):
                    continue
                link = os.path.join(farm, name)
                if not os.path.lexists(link):
                    try:
                        os.symlink(os.path.join(lib_dir, name), link)
                    except OSError as exc:
                        self.output.warning(f"link farm entry {name} failed: {exc}")
        return cwd, farm

    def test(self):
        self._materialize_abs_deps()

        dep = self.dependencies.get("knavalbattle")
        assert dep is not None and dep.package_folder is not None, (
            "knavalbattle not found in the dependency graph"
        )
        app_bin = os.path.join(dep.package_folder, "bin", "knavalbattle")
        assert os.path.exists(app_bin), f"missing packaged application: {app_bin}"

        scratch_cwd, farm = self._make_scratch()

        # Rebuild the whole runtime environment explicitly (the inherited
        # host LD_LIBRARY_PATH carries whitespace-padded entries the OHOS
        # loader cannot resolve).
        ld_paths = list(self._collect_libs())
        ld_paths.append(farm)
        ld_paths.extend(["/system/lib64", "/system/lib64/platformsdk", "/system/lib64/ndk"])
        plugin_paths = []
        for p in self.dependencies.values():
            if p and p.package_folder:
                for plugins_dir in ("plugins", os.path.join("lib", "plugins")):
                    plugins_path = os.path.join(p.package_folder, plugins_dir)
                    if os.path.isdir(plugins_path):
                        plugin_paths.append(plugins_path)

        env = Environment()
        env.define("LD_LIBRARY_PATH", ":".join(ld_paths))
        env.define("QT_PLUGIN_PATH", ":".join(plugin_paths))
        env.define("QT_QPA_PLATFORM", "offscreen")
        home = os.path.join(scratch_cwd, "test-home")
        xdg_runtime = os.path.join(scratch_cwd, "xdg-runtime")
        os.makedirs(home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(home, ".local", "share"))

        with env.vars(self).apply():
            # R34: real execution of the packaged binary. --version is
            # handled by KAboutData/QCommandLineParser before any display,
            # DBus or network service starts; a non-zero exit means the
            # binary could not start (missing loader deps / broken ELF).
            # Output validation lives in run_test.py — the standalone test
            # source file required by the CI L0c gate (povray/normalize
            # precedent: local .sh residue makes L0c pass spuriously, a
            # clean CI checkout needs a real .py test source).
            self.output.info(f"running packaged binary: {app_bin} --version")
            import sys as _sys
            _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import run_test
            # self.run() executes in the Conan-managed environment (the
            # env-vars block above); its retcode/output are then validated
            # by run_test.check_run_output().
            self.run(f'"{app_bin}" --version', cwd=scratch_cwd)
            proc = subprocess.run(
                f'"{app_bin}" --version', shell=True, cwd=scratch_cwd,
                capture_output=True, text=True, timeout=120,
            )
            run_test.check_run_output(proc.returncode,
                                      (proc.stdout or "") + (proc.stderr or ""))
