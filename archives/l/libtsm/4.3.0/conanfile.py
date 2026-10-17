#!/usr/bin/env python3
"""Conan recipe — libtsm 4.3.0 (TSM, terminal-emulator state machine).

Upstream (official): kmscon/libtsm — the terminal-emulator state machine that
grew out of David Herrmann's kmscon project. The Aetf/libtsm repository is a
personal fork that self-describes as "This is a personal modified version.
Upstream development has restarted from this fork at [official repository]
(https://github.com/kmscon/libtsm)"; both carry the same v4.3.0 tag
(commit 9d2817b7) and byte-identical tag archives, so this recipe takes the
official source per R39. Build system: meson (>= 1.1). The project is plain C
(``project('libtsm', 'c', ...)``), c_std=gnu99.

Shape of the upstream build (4.3.0):
  * ``src/tsm/meson.build`` declares ``shared_library('tsm', ...)`` with
    ``version: 4.3.0`` / ``soversion: 4`` and a linker version script
    (``src/tsm/libtsm.sym`` -> ABI symbol versions LIBTSM_3 / LIBTSM_4);
    the produced artifact is ``libtsm.so.4.3.0`` (SONAME ``libtsm.so.4``).
    There is no static variant upstream, so this recipe truthfully declares
    ``shared=True`` only and rejects a static request instead of silently
    emitting a shared library (see ``validate()``/``generate()``).
  * installed files: ``lib/libtsm.so*``, ``include/libtsm.h`` and the meson
    generated pkg-config file ``lib/pkgconfig/libtsm.pc``.
  * ``xkbcommon`` is an *optional* dependency used only for keysym
    translation; upstream falls back to the vendored
    ``external/xkbcommon/xkbcommon-keysyms.h`` when it is not found. That
    fallback is what happens here (no xkbcommon package on the ohpcd remote),
    so the recipe needs no dependency and no patch.
  * ``dependency('check')`` in ``test/meson.build`` is unconditional, so the
    ``tests`` project option must be turned off here: ``check`` is a test-only
    framework that must not enter the package dependency chain. The 7 upstream
    ``check`` suites (37 registered test cases) are executed on the device
    during native exploration; evidence in ``reports/`` and ``notes.md``.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.meson import Meson, MesonToolchain


class LibtsmConan(ConanFile):
    name = "libtsm"
    version = "4.3.0"
    description = ("Terminal-emulator state machine (DEC VT100-VT520 "
                   "compatible) used by terminal emulators such as kmscon")
    license = "MIT"
    homepage = "https://github.com/kmscon/libtsm"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("terminal", "terminal-emulator", "vt100", "state-machine",
              "kmscon")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # meson_layout was removed in conan 2.29.x; replicate its folders.
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def validate(self):
        self._check_shared()

    def _check_shared(self):
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "libtsm/4.3.0 only provides a shared library: upstream "
                "src/tsm/meson.build declares shared_library('tsm') "
                "unconditionally (no default_library switch, no static "
                "target). Build with -o libtsm/*:shared=True or adapt the "
                "upstream meson.build in a patch.")

    def generate(self):
        self._check_shared()
        tc = MesonToolchain(self)
        # Upstream defaults: tests=true, gtktsm=false, extra_debug=false.
        # tests must be off here (check is not a package dependency);
        # gtktsm/extra_debug are pinned so the packaged build cannot drift
        # with upstream option defaults.
        tc.project_options["tests"] = False
        tc.project_options["gtktsm"] = False
        tc.project_options["extra_debug"] = False
        # meson probes the static archiver through the compiler-derived bare
        # name ("llvm-ar" for clang toolchains) via PATH lookup; CI workers
        # ship a shorter PATH where that bare name is not resolvable and
        # configure fails with "Unknown linker(s): [['llvm-ar']]". Pin the
        # archiver with an absolute path (same doctrine as the profile's
        # compiler_executables conf).
        tc.binaries["ar"] = self._resolve_archiver()
        tc.generate()

    @staticmethod
    def _resolve_archiver():
        """Absolute path of the static archiver for the meson native file.

        Resolution order (never relies on a bare name resolved by PATH at
        build time, R33): PATH lookup -> the hnp toolchain location used by
        the OHOS profile -> common LLVM/GNU locations. Raises if nothing is
        found instead of silently emitting a bare name that would fail later
        with a confusing meson error.
        """
        candidates = [
            shutil.which("llvm-ar"),
            "/data/service/hnp/bin/llvm-ar",
            shutil.which("ar"),
            "/usr/bin/ar",
            "/bin/ar",
        ]
        for path in candidates:
            if path and os.path.isabs(path) and os.path.exists(path):
                return path
        raise ConanInvalidConfiguration(
            "no static archiver found: looked for llvm-ar and ar in PATH, "
            "/data/service/hnp/bin, /usr/bin and /bin. Set "
            "tools.build:compiler_executables={\"ar\": ...} in the profile.")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # meson target 'tsm' -> libtsm.so.4.3.0 (SONAME libtsm.so.4), so the
        # link name is -ltsm. DT_NEEDED of the artifact is libc.so only.
        self.cpp_info.libs = ["tsm"]
