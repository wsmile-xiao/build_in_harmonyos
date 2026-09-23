#!/usr/bin/env python3
"""Conan test_package for alligator 26.04.0 (consumer-side validation).

Verifies the packaged alligator binary starts under the offscreen QPA and
exercises the full QML application surface via the upstream `--self-test`
mode: QQmlApplicationEngine loads Main.qml (Kirigami ApplicationWindow +
kirigami-addons formcard UI + org.kde.alligator models backed by SQLite),
then the 250 ms self-test timer quits the event loop cleanly. This drives
the entire Qt6/KF6/Kirigami QML link closure on the target.

Runtime-linking notes (accessibility 26.04.3 / E537 precedent):
* some published KF6 libraries carry build-tree-relative DT_NEEDED entries
  ("../bin/...", "../../bin/...") and a few absolute conan-cache paths. The
  test runs from a fresh scratch directory whose ../bin and ../../bin both
  reach a link farm of every KF6 shared library (calligra 24.12.3
  precedent), and stale absolute paths are materialized as symlinks.
* the host shell LD_LIBRARY_PATH carries whitespace-padded entries the
  OHOS loader cannot resolve (kirigami-addons 1.13.0 notes, issue 1), and
  the aggregated conanrun QML2_IMPORT_PATH does not include the
  qtdeclarative qml/ tree that QtQuick.Controls needs — so the whole
  environment is rebuilt explicitly here instead of relying on
  env="conanrun".
"""
import os
import re
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.env import Environment


class AlligatorTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

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

    def _collect_libs(self):
        lib_dirs = []
        for p in self.dependencies.values():
            if p and p.package_folder:
                for layout_dir in ("lib", "bin"):
                    lib_dir = os.path.join(p.package_folder, layout_dir)
                    if os.path.isdir(lib_dir):
                        lib_dirs.append(lib_dir)
        return lib_dirs

    def _make_scratch(self):
        # Fresh scratch CWD for the test run: build-tree-relative DT_NEEDED
        # entries ("../../bin/libKF6ConfigCore.so") resolve against the
        # process CWD, so <cwd>/../../bin must reach a link farm of every
        # dependency shared library (E537, accessibility 26.04.3 /
        # calligra 24.12.3 precedent). Layout: <scratch>/a/b is the run CWD
        # and <scratch>/bin is the farm, so ../../bin from the CWD resolves
        # to the farm. Doing this inside a scratch tree (instead of the
        # conan build folder) keeps the recipe sources clean.
        scratch = tempfile.mkdtemp(prefix="alligator-test-")
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
                            except OSError as e:
                                self.output.warning(
                                    f"DT_NEEDED symlink fail {abs_path}: {e}"
                                )
                            break

    def test(self):
        self._materialize_abs_deps()

        dep = self.dependencies.get("alligator")
        assert dep is not None and dep.package_folder is not None, (
            "alligator not found in the dependency graph"
        )
        app_bin = os.path.join(dep.package_folder, "bin", "alligator")
        assert os.path.exists(app_bin), f"missing packaged application: {app_bin}"

        scratch_cwd, farm = self._make_scratch()

        # Rebuild the whole runtime environment explicitly: the inherited
        # host LD_LIBRARY_PATH carries whitespace-padded entries the OHOS
        # loader cannot resolve, and the aggregated conanrun
        # QML2_IMPORT_PATH omits the qtdeclarative qml/ tree.
        ld_paths = list(self._collect_libs())
        ld_paths.append(farm)
        ld_paths.extend(["/system/lib64", "/system/lib64/platformsdk", "/system/lib64/ndk"])
        qml_paths = []
        for p in self.dependencies.values():
            if p and p.package_folder:
                for qml_dir in ("qml", os.path.join("lib", "qml"), os.path.join("bin", "qml")):
                    qml_path = os.path.join(p.package_folder, qml_dir)
                    if os.path.isdir(qml_path):
                        qml_paths.append(qml_path)
        # The packaged org.kde.alligator QML module (installed next to the
        # binary by ecm_add_qml_module) must be on the import path.
        qml_paths.insert(0, os.path.join(dep.package_folder, "bin"))

        env = Environment()
        env.define("LD_LIBRARY_PATH", ":".join(ld_paths))
        env.define("QML2_IMPORT_PATH", ":".join(qml_paths))
        plugin_paths = []
        for p in self.dependencies.values():
            if p and p.package_folder:
                for plugins_dir in ("plugins", os.path.join("lib", "plugins")):
                    plugins_path = os.path.join(p.package_folder, plugins_dir)
                    if os.path.isdir(plugins_path):
                        plugin_paths.append(plugins_path)
        env.define("QT_PLUGIN_PATH", ":".join(plugin_paths))
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("TZ", "Asia/Shanghai")
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
            # R34: real execution of the packaged application. --self-test is
            # the upstream automated-testing entry point (autotests/
            # CMakeLists.txt registers it as alligator-self-test); a nonzero
            # exit means either the engine failed to load Main.qml
            # (rootObjects().isEmpty() -> -1) or a startup crash. The CWD is
            # the scratch tree so build-tree-relative DT_NEEDED entries
            # resolve against the link farm.
            self.run(f'"{app_bin}" --self-test', cwd=scratch_cwd)
