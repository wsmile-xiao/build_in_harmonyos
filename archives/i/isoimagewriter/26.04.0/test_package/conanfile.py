#!/usr/bin/env python3
"""Conan test_package for isoimagewriter 26.04.0 (consumer-side validation).

R34: the test actually executes the packaged application.  Upstream ships no
test suite (no autotests/ directory, no enable_testing()/add_test()), so the
consumer test is the only automated coverage and it drives the real binary:

  * `isoimagewriter --version` — QApplication is constructed (which loads the
    offscreen QPA plugin and therefore the whole Qt6/KF6 link closure), then
    KAboutData/QCommandLineParser print the application name and exit 0.  The
    version number itself is baked into the binary by ecm_setup_version /
    -DPROJECT_VERSION and is asserted on the artifact bytes, because upstream
    handles --version before KAboutData::setApplicationData() so Qt reports an
    empty applicationVersion.
  * `isoimagewriter --help`     — same startup path, plus the upstream
    command-line surface (--version, --lang, --dir) must be advertised.
  * the packaged .desktop and icon files must exist, which proves the patched
    install branch (HarmonyOS handled like Linux) took effect.

Runtime-linking repair (E537 family, accessibility 26.04.3 / alligator 26.04.0
precedent): several published KF6 libraries carry DT_NEEDED entries that are
not plain sonames —

  * build-tree-relative entries such as "../../bin/libKF6ConfigCore.so", which
    the loader resolves against the process CWD, and
  * absolute paths recorded from the builder's conan home, e.g.
    /home/.../.cache/conan2/p/<id>/p/lib/libKF6I18n.so, which do not exist on
    another machine.

Both are repaired here by materializing the missing entries from the dependency
packages.  Symlinks are used when the platform allows them, otherwise the file
is copied in place: the OHOS sandbox maps the conan process to a foreign uid, so
symlink creation there fails with EACCES while ordinary file creation succeeds.

The inherited host LD_LIBRARY_PATH also carries whitespace-padded entries the
OHOS loader cannot resolve, so the runtime environment is rebuilt explicitly
instead of relying on env="conanrun".
"""
import os
import re
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.env import Environment


class IsoimagewriterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ── dependency library helpers ──────────────────────────────────────
    def _lib_dirs(self):
        lib_dirs = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                for layout_dir in ("lib", "bin"):
                    lib_dir = os.path.join(dep.package_folder, layout_dir)
                    if os.path.isdir(lib_dir):
                        lib_dirs.append(lib_dir)
        return lib_dirs

    def _find_readelf(self):
        for cand in (
            "readelf",
            "/data/service/hnp/bin/readelf",
            "/usr/bin/readelf",
            "/bin/readelf",
        ):
            exe = cand
            try:
                found = shutil.which(cand)
                if found:
                    exe = found
                subprocess.run([exe, "--version"], capture_output=True, timeout=20)
                return exe
            except (OSError, subprocess.SubprocessError):
                continue
        return None

    def _needed_entries(self, readelf, path):
        try:
            out = subprocess.run(
                [readelf, "-d", path], capture_output=True, text=True, timeout=60
            ).stdout
        except (OSError, subprocess.SubprocessError):
            return []
        return re.findall(r"Shared library: \[([^\]]+)\]", out)

    def _find_lib(self, basename, lib_dirs):
        for lib_dir in lib_dirs:
            cand = os.path.join(lib_dir, basename)
            if os.path.exists(cand):
                return cand
        return None

    def _link_or_copy(self, src, dst):
        """Place a library at an exact path; symlink, else copy.

        The OHOS sandbox maps the conan process tree to a foreign uid, so
        symlink creation fails there with EACCES while file creation (the
        directories are group-writable and setgid) succeeds.
        """
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.lexists(dst):
            return
        try:
            os.symlink(src, dst)
        except OSError:
            shutil.copy2(src, dst)

    def _repair_dt_needed(self, readelf, lib_dirs, run_cwd):
        """Materialize relative and stale-absolute DT_NEEDED entries."""
        repaired = []
        for lib_dir in lib_dirs:
            for name in sorted(os.listdir(lib_dir)):
                if not name.endswith(".so"):
                    continue
                for entry in self._needed_entries(readelf, os.path.join(lib_dir, name)):
                    if entry.startswith("/"):
                        dest = entry
                    elif "/" in entry:
                        # Relative entries are resolved against the process CWD.
                        dest = os.path.normpath(os.path.join(run_cwd, entry))
                    else:
                        continue
                    if os.path.exists(dest):
                        continue
                    src = self._find_lib(os.path.basename(entry), lib_dirs)
                    if not src:
                        continue
                    try:
                        self._link_or_copy(src, dest)
                        repaired.append(f"{os.path.basename(entry)} -> {dest}")
                    except OSError as exc:
                        self.output.warning(f"cannot materialize {dest}: {exc}")
        return repaired

    def _run_app(self, app_bin, env, cwd, args):
        """Run the packaged binary with a bound log and return its output."""
        log = os.path.join(cwd, "run.log")
        with env.vars(self).apply():
            self.run(f'"{app_bin}" {args} > "{log}" 2>&1', cwd=cwd)
        with open(log, "r", errors="replace") as handle:
            return handle.read()

    # ── test ────────────────────────────────────────────────────────────
    def test(self):
        dep = self.dependencies.get("isoimagewriter")
        if dep is None or not dep.package_folder:
            raise AssertionError("isoimagewriter not found in the dependency graph")
        app_bin = os.path.join(dep.package_folder, "bin", "isoimagewriter")
        if not os.path.exists(app_bin):
            raise AssertionError(f"missing packaged application: {app_bin}")

        # The patched install branch must ship the desktop integration files.
        for rel in (
            os.path.join("share", "applications", "org.kde.isoimagewriter.desktop"),
            os.path.join("share", "icons", "hicolor", "scalable", "apps",
                         "org.kde.isoimagewriter.svg"),
        ):
            installed = os.path.join(dep.package_folder, rel)
            if not os.path.exists(installed):
                raise AssertionError(f"missing installed file: {installed}")

        # Run from <scratch>/a/b so relative DT_NEEDED entries ("../../bin/X")
        # resolve inside the scratch tree (alligator 26.04.0 precedent).
        scratch = tempfile.mkdtemp(prefix="isoimagewriter-test-")
        run_cwd = os.path.join(scratch, "a", "b")
        os.makedirs(run_cwd, exist_ok=True)

        lib_dirs = self._lib_dirs()
        readelf = self._find_readelf()
        if readelf:
            repaired = self._repair_dt_needed(readelf, lib_dirs, run_cwd)
            self.output.info(
                f"DT_NEEDED entries materialized: {len(repaired)}"
            )
            for item in repaired:
                self.output.info(f"  {item}")
        else:
            self.output.warning("readelf not found; DT_NEEDED repair skipped")

        ld_paths = list(lib_dirs)
        ld_paths.extend([
            "/system/lib64", "/system/lib64/platformsdk", "/system/lib64/ndk",
        ])
        plugin_paths = []
        for dep_it in self.dependencies.values():
            if dep_it and dep_it.package_folder:
                for plugins_dir in ("plugins", os.path.join("lib", "plugins")):
                    plugins_path = os.path.join(dep_it.package_folder, plugins_dir)
                    if os.path.isdir(plugins_path):
                        plugin_paths.append(plugins_path)

        env = Environment()
        env.define("LD_LIBRARY_PATH", ":".join(ld_paths))
        env.define("QT_PLUGIN_PATH", ":".join(plugin_paths))
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("TZ", "Asia/Shanghai")
        home = os.path.join(run_cwd, "test-home")
        xdg_runtime = os.path.join(run_cwd, "xdg-runtime")
        os.makedirs(home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(home, ".local", "share"))

        version_out = self._run_app(app_bin, env, run_cwd, "--version")
        self.output.info("--version output:\n" + version_out)
        if "isoimagewriter" not in version_out:
            raise AssertionError(
                f"--version did not identify the application: {version_out!r}"
            )

        pkg_version = str(dep.ref.version)
        # ecm_setup_version / -DPROJECT_VERSION bake the release version into
        # the executable, so the artifact itself proves which upstream release
        # was packaged (upstream's --version prints an empty applicationVersion
        # because KAboutData::setApplicationData() runs after option parsing).
        # KAboutData takes the version through QStringLiteral, i.e. UTF-16, so
        # both encodings are accepted.
        with open(app_bin, "rb") as handle:
            binary = handle.read()
        if (pkg_version.encode() not in binary
                and pkg_version.encode("utf-16-le") not in binary):
            raise AssertionError(
                f"packaged binary does not embed the version string "
                f"{pkg_version}"
            )

        help_out = self._run_app(app_bin, env, run_cwd, "--help")
        self.output.info("--help output:\n" + help_out)
        for option in ("--version", "--lang", "--dir"):
            if option not in help_out:
                raise AssertionError(
                    f"--help did not advertise the upstream option "
                    f"{option}: {help_out!r}"
                )
