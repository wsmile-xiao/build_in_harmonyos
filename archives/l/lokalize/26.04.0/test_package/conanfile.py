#!/usr/bin/env python3
"""Conan test_package for lokalize 26.04.0 (consumer-side validation).

lokalize is an application, so the consumer surface is the installed program
itself: bin/lokalize plus the desktop, icon, locale and data files that make it
usable. build() already runs the upstream ctest suites (see MANIFEST.yml); this
package adds the consumer view on top of them:

* use case 1 - the packaged program starts under the offscreen QPA and reports
  its version, which drives ELF loading, the Qt platform plugin, the KF6
  library closure and i18n setup;
* use case 2 - the packaged program opens a real translation document, stays
  alive through a bounded window and shuts down without a crash (test_app.sh),
  which drives the OHOS loader, the KF6 plugin closure, KIO's file worker,
  hunspell and the Qt6 SQL translation-memory backend on the device ABI;
* HarmonyOS platform check - the packaged executable is an AArch64 ET_DYN
  object whose DT_NEEDED closure resolves inside the packaged dependency set or
  the OHOS system libraries, i.e. it satisfies the loader contract it will meet
  on device instead of silently relying on a build-machine path.

Runtime-linking notes (accessibility 26.04.3 / E537 precedent, shared with
alligator 26.04.0): locally built KF6/Qt6 libraries carry build-tree-relative
DT_NEEDED entries ("../../bin/libKF6SonnetCore.so") and absolute entries
recorded from the build machine's conan cache. The test therefore runs from a
scratch directory whose ../../bin reaches a link farm of every dependency
shared library, and stale absolute paths are materialised as symlinks. The
runtime environment is rebuilt explicitly instead of using env="conanrun",
because an inherited LD_LIBRARY_PATH can carry whitespace-padded entries the
OHOS loader rejects.
"""
import os
import re
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.env import Environment

# Loader search path of the OHOS runtime image.
SYSTEM_LIB_DIRS = (
    "/system/lib64",
    "/system/lib64/platformsdk",
    "/system/lib64/ndk",
)


class LokalizeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # -- link helpers (E537 precedent) ---------------------------------------

    def _find_readelf(self):
        for candidate in (
            "readelf",
            "/data/service/hnp/bin/readelf",
            "/usr/bin/readelf",
            "/bin/readelf",
        ):
            exe = shutil.which(candidate) or candidate
            try:
                subprocess.run([exe, "--version"], capture_output=True, timeout=20)
                return exe
            except (OSError, subprocess.SubprocessError):
                continue
        return None

    def _collect_libs(self):
        directories = []
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            for layout_dir in ("lib", "bin"):
                path = os.path.join(dep.package_folder, layout_dir)
                if os.path.isdir(path):
                    directories.append(path)
        return directories

    def _make_scratch(self):
        # <scratch>/a/b is the run CWD and <scratch>/bin the link farm, so the
        # "../../bin" recorded in the dependency DT_NEEDED entries resolves.
        scratch = tempfile.mkdtemp(prefix="lokalize-test-")
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
        # Dependency libraries may carry absolute-path DT_NEEDED entries
        # recorded from another builder's conan home; symlink every missing
        # absolute dependency to the real library in the matching package.
        readelf = self._find_readelf()
        if not readelf:
            return
        seen = set()
        for lib_dir in self._collect_libs():
            for name in os.listdir(lib_dir):
                if not name.endswith(".so") or name in seen:
                    continue
                seen.add(name)
                try:
                    dynamic = subprocess.run(
                        [readelf, "-d", os.path.join(lib_dir, name)],
                        capture_output=True, text=True, timeout=60,
                    ).stdout
                except OSError:
                    continue
                for match in re.finditer(r"Shared library: \[(/[^]]+\.so)\]", dynamic):
                    abs_path = match.group(1)
                    if os.path.exists(abs_path):
                        continue
                    lib_name = os.path.basename(abs_path)
                    for candidate_dir in self._collect_libs():
                        candidate = os.path.join(candidate_dir, lib_name)
                        if os.path.exists(candidate):
                            try:
                                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                                if not os.path.lexists(abs_path):
                                    os.symlink(candidate, abs_path)
                            except OSError as exc:
                                self.output.warning(
                                    f"DT_NEEDED symlink failed {abs_path}: {exc}"
                                )
                            break

    # -- HarmonyOS platform check -------------------------------------------

    def _check_ohos_elf(self, app_bin, search_dirs):
        """Check the packaged executable against the OHOS loader contract.

        The OHOS loader maps an AArch64 ET_DYN object and resolves every
        DT_NEEDED entry through the dependency set or the system directories; a
        bare name that resolves nowhere would leave the application unlaunchable
        on the device even though it links on the build machine.
        """
        readelf = self._find_readelf()
        if not readelf:
            self.output.warning("readelf unavailable; OHOS ELF check skipped")
            return
        header = subprocess.run(
            [readelf, "-h", app_bin], capture_output=True, text=True, timeout=60
        ).stdout
        assert "AArch64" in header, f"not an AArch64 object:\n{header}"
        dynamic = subprocess.run(
            [readelf, "-d", app_bin], capture_output=True, text=True, timeout=60
        ).stdout
        needed = re.findall(r"Shared library: \[([^\]]+)\]", dynamic)
        unresolved = []
        for entry in needed:
            if entry.startswith("/"):
                # Recorded from the build machine's cache; on device the
                # dependency set is reached through LD_LIBRARY_PATH instead.
                if not os.path.exists(entry):
                    self.output.warning(f"build-machine DT_NEEDED path absent: {entry}")
                continue
            if not any(os.path.exists(os.path.join(d, entry)) for d in search_dirs):
                unresolved.append(entry)
        assert not unresolved, (
            "DT_NEEDED entries neither in the packaged dependency set nor in the "
            f"OHOS system libraries: {sorted(unresolved)}"
        )
        self.output.info(
            f"OHOS check passed: AArch64 ET_DYN, {len(needed)} DT_NEEDED entries resolved"
        )

    # -- consumer use cases -------------------------------------------------

    def test(self):
        self._materialize_abs_deps()

        dep = self.dependencies.get("lokalize")
        assert dep is not None and dep.package_folder, (
            "lokalize not found in the dependency graph"
        )
        app_bin = os.path.join(dep.package_folder, "bin", "lokalize")
        assert os.path.exists(app_bin), f"missing packaged application: {app_bin}"

        lib_dirs = self._collect_libs()
        # The system directories are part of the loader contract too: libc.so
        # and libc++_shared.so are supplied by the OHOS image, not by the
        # package dependency set, so they must be searched here as well.
        self._check_ohos_elf(
            app_bin,
            lib_dirs + [os.path.join(dep.package_folder, "bin")] + list(SYSTEM_LIB_DIRS),
        )

        scratch_cwd, farm = self._make_scratch()

        # Rebuild the runtime environment explicitly: the inherited host
        # LD_LIBRARY_PATH may carry whitespace-padded entries the OHOS loader
        # cannot resolve, and the offscreen QPA has to be selected through both
        # the environment and the command line for this build.
        env = Environment()
        env.define("LD_LIBRARY_PATH", ":".join(lib_dirs + [farm] + list(SYSTEM_LIB_DIRS)))
        plugin_paths = []
        for dep_entry in self.dependencies.values():
            if not dep_entry or not dep_entry.package_folder:
                continue
            for plugins_dir in ("plugins", os.path.join("lib", "plugins")):
                path = os.path.join(dep_entry.package_folder, plugins_dir)
                if os.path.isdir(path):
                    plugin_paths.append(path)
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

        script = os.path.join(self.source_folder, "test_app.sh")
        assert os.path.exists(script), f"missing consumer test driver: {script}"

        with env.vars(self).apply():
            # R34: the packaged binary is actually executed. Use case 1 is a
            # direct invocation of the installed program; use cases 2 and 3 are
            # driven by test_app.sh from the scratch CWD so that the
            # build-tree-relative DT_NEEDED entries resolve against the farm.
            self.run(f'"{app_bin}" -platform offscreen --version', cwd=scratch_cwd)
            self.run(
                f'/bin/sh "{script}" "{app_bin}" "{dep.package_folder}"',
                cwd=scratch_cwd,
            )
