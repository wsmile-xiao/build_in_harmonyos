#!/usr/bin/env python3
"""Conan test_package for accessibility 26.04.3 (conan package name is
the platform task name; the upstream product remains
accessibility-inspector).

Verifies the packaged accessibilityinspector binary starts under the
offscreen QPA and exits cleanly via `--version` (QApplication is built
before argument parsing, so the full Qt6/KF6/QAccessibilityClient6 link
closure is exercised on the target).

Runtime-linking note (E537): some published KF6 libraries carry
build-tree-relative DT_NEEDED entries ("../bin/...", "../../bin/...")
and a few absolute conan-cache paths. The parent recipe defines SONAME
flags at link time, so this package's own artifacts already carry
bare-name DT_NEEDED entries and no post-link ELF rewrite is performed
(REV-F3: the earlier "recipe rewrites ... at package()" wording was a
leftover from an abandoned iteration); for the published dependency
libraries this test mirrors the expected build layout next to the
process CWD (link farm, calligra 24.12.3 precedent) and materializes
stale absolute paths as symlinks.
"""
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.env import Environment


class AccessibilityInspectorTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _find_readelf(self):
        import shutil
        for cand in (
            "readelf",
            "/data/service/hnp/bin/readelf",
            "/storage/Users/currentUser/.harmonybrew/bin/readelf",
            "/usr/bin/readelf",
            "/bin/readelf",
        ):
            exe = cand
            try:
                w = shutil.which(cand)
                if w:
                    exe = w
                subprocess.run([exe, "--version"], capture_output=True, timeout=20)
                return exe
            except (OSError, subprocess.SubprocessError):
                continue
        return None

    def _link_farm(self):
        # KF6 libraries record build-tree-relative DT_NEEDED entries (e.g.
        # ../bin/... and ../../bin/...) resolved against the process CWD
        # (tests run with cwd == the cmake build folder). Mirror the expected
        # layout so ../bin and ../../bin both reach a farm of every KF6
        # shared library.
        tp_bin = os.path.join(self.build_folder, "..", "..", "bin")
        os.makedirs(tp_bin, exist_ok=True)
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder, "lib") if dep.package_folder else None
            if libdir and os.path.isdir(libdir):
                for name in os.listdir(libdir):
                    if name.endswith(".so"):
                        link = os.path.join(tp_bin, name)
                        if not os.path.lexists(link):
                            os.symlink(os.path.join(libdir, name), link)
        build_bin = os.path.join(self.build_folder, "..", "bin")
        if not os.path.lexists(build_bin):
            try:
                os.symlink("../bin", build_bin)
            except OSError as e:
                self.output.warning(f"build/bin symlink fail: {e}")

    def _materialize_abs_deps(self):
        # Dependency libs may carry absolute-path DT_NEEDED entries recorded
        # from another builder's conan home; symlink every missing absolute
        # dependency to the real library in the matching package.
        readelf = self._find_readelf()
        if not readelf:
            self.output.warning(
                "readelf not found; absolute DT_NEEDED materialization skipped"
            )
            return
        self.output.info(f"readelf resolved: {readelf}")
        seen_libs = set()
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for name in os.listdir(libdir):
                if not name.endswith(".so") or name in seen_libs:
                    continue
                seen_libs.add(name)
                lib_path = os.path.join(libdir, name)
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
                    for d2 in self.dependencies.values():
                        if not d2.package_folder:
                            continue
                        cand = os.path.join(d2.package_folder, "lib", fname)
                        if os.path.exists(cand):
                            try:
                                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                                if not os.path.lexists(abs_path):
                                    os.symlink(cand, abs_path)
                            except OSError as e:
                                self.output.warning(
                                    f"DT_NEEDED symlink fail {abs_path}: {e}"
                                )
                            break

    def test(self):
        self._link_farm()
        self._materialize_abs_deps()

        dep = self.dependencies.get("accessibility")
        assert dep is not None and dep.package_folder is not None, (
            "accessibility not found in the dependency graph"
        )
        app_bin = os.path.join(dep.package_folder, "bin", "accessibilityinspector")
        assert os.path.exists(app_bin), f"missing packaged application: {app_bin}"

        env = Environment()
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("TZ", "Asia/Shanghai")
        home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(home, ".local", "share"))
        for p in self.dependencies.values():
            if p and p.package_folder:
                lib_dir = os.path.join(p.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    env.prepend_path("LD_LIBRARY_PATH", lib_dir)
                plugins_dir = os.path.join(p.package_folder, "plugins")
                if os.path.isdir(plugins_dir):
                    env.prepend_path("QT_PLUGIN_PATH", plugins_dir)
        tp_bin = os.path.join(self.build_folder, "..", "..", "bin")
        env.append("LD_LIBRARY_PATH", [tp_bin])

        with env.vars(self).apply():
            # R34: real execution of the packaged application.
            self.run(f'"{app_bin}" --version', env="conanrun")
