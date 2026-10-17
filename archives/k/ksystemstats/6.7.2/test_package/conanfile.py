#!/usr/bin/env python3
"""Conan test_package for ksystemstats 6.7.2.

The package is an application — the ``org.kde.ksystemstats`` D-Bus daemon, its
eight sensor plugins (the lmsensors plugin is gated off on this platform) and
the ``kstatsviewer`` CLI — so there is no library to link against. The
consumer-side test therefore executes the packaged binaries
end to end: ``consumer_check.sh`` starts the packaged daemon against a private
session bus and asserts, through the packaged CLI, that the plugins published
sensors and that a concrete sensor reports a live value (R34).

Removing the package's ``bin/`` or ``plugins/`` directory makes this fail, so
the check cannot pass against a stub (the CI L1e destructive reverse
verification walks the same path).
"""
import glob
import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class KsystemstatsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # Provides dbus-daemon for the session bus the packaged daemon needs
        # (OHOS ships none).
        self.tool_requires("dbus/1.14.10.1")

    def _runtime_env(self):
        """Runtime library path for the SDK libc++ and every dependency, using
        the same ordering as the package recipe (kconfig/kdeclarative
        precedent)."""
        env = Environment()
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        deps = list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        )
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "bin")
                )
        return env

    def _dbus_daemon(self):
        dep = self.dependencies.build.get("dbus")
        if dep and dep.package_folder:
            candidate = os.path.join(dep.package_folder, "bin", "dbus-daemon")
            if os.path.isfile(candidate):
                return candidate
        raise ConanException(
            "dbus-daemon was not found in the dbus/1.14.10.1 tool package; the "
            "packaged daemon cannot be driven over D-Bus without a session bus"
        )

    def _libksysguard_libdir(self):
        try:
            dependency = self.dependencies["libksysguard"]
        except KeyError:
            return None
        if dependency.cpp_info.libdirs:
            return dependency.cpp_info.libdirs[0]
        return None

    def _bridge_legacy_needed_paths(self, bridge_root):
        """Materialize the published libksysguard/6.7.2 DT_NEEDED quirks.

        libKSysGuardSystemStats.so records libKSysGuardFormatter.so as the
        relative path "../bin/libKSysGuardFormatter.so", which the loader
        resolves against the process CWD, and libKSysGuardFormatter.so records
        its KF6 dependencies as absolute paths under a previous Conan cache
        prefix (<home>/.cache/conan2). The consumer check runs with
        "<bridge_root>/work" as CWD, so "../bin" is bridged under
        <bridge_root>, and the stale cache prefix is bridged to the live one
        (E537; akonadi/baloo precedent).
        """
        if str(self.settings.os) != "OHOS":
            return
        libdir = self._libksysguard_libdir()
        if libdir:
            formatter = os.path.join(libdir, "libKSysGuardFormatter.so")
            if os.path.isfile(formatter):
                target = os.path.join(
                    bridge_root, "bin", "libKSysGuardFormatter.so"
                )
                if not os.path.lexists(target):
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    os.symlink(formatter, target)
        stale_root = os.path.join(os.path.expanduser("~"), ".cache", "conan2")
        live_root = os.path.join(os.path.expanduser("~"), ".conan2")
        if not os.path.exists(stale_root) and os.path.isdir(live_root):
            try:
                os.symlink(live_root, stale_root)
            except OSError as exc:
                self.output.warning(
                    "could not bridge %s -> %s: %s" % (stale_root, live_root, exc)
                )

    def test(self):
        package_folder = self.dependencies["ksystemstats"].package_folder
        # Never write build artefacts into the recipe tree (R10: TMPDIR, the
        # OHOS root is read-only); the run tree is disposable.
        tmp_root = os.environ.get("TMPDIR") or os.path.join(
            os.path.expanduser("~"), "tmp"
        )
        os.makedirs(tmp_root, exist_ok=True)
        bridge_root = tempfile.mkdtemp(prefix="ksystemstats-consumer-", dir=tmp_root)
        work_dir = os.path.join(bridge_root, "work")
        os.makedirs(work_dir, exist_ok=True)
        self._bridge_legacy_needed_paths(bridge_root)

        script = os.path.join(self.recipe_folder, "consumer_check.sh")
        env = self._runtime_env()
        env.define("TMPDIR", tmp_root)
        try:
            with env.vars(self).apply():
                self.run(
                    'sh "{}" "{}" "{}" "{}"'.format(
                        script, package_folder, self._dbus_daemon(), work_dir
                    ),
                    env="conanrun",
                    # "../bin/libKSysGuardFormatter.so" is resolved against the
                    # CWD; the bridge created above lives in <bridge_root>/bin.
                    cwd=work_dir,
                )
        finally:
            shutil.rmtree(bridge_root, ignore_errors=True)
