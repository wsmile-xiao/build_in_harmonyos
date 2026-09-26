#!/usr/bin/env python3
"""Conan recipe — libinput 1.26.2 (libinput shared library + tools, Meson).

libinput is the input device handling library used by Wayland compositors and
X.Org: it reads kernel evdev events and turns them into high-level events
(pointer motion/buttons, keyboard, touch, gestures, tablet, switch).  It is the
input stack behind weston / wlroots / XWayland, and consumes libevdev, mtdev
and libudev.

Adapted to HarmonyOS PC (aarch64).  See notes.md for the platform notes.

Upstream build system is Meson (>= 0.56.0).  The upstream test suite (litest)
is *not* built here — see `_configure_tests` and notes.md for the measured
reason (litest hard-depends on /dev/uinput, which this environment does not
expose).
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibinputConan(ConanFile):
    name = "libinput"
    version = "1.26.2"
    description = "Input device handling library for Wayland compositors and X.Org"
    license = "MIT"
    homepage = "https://wayland.freedesktop.org/libinput.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # libinput is a Linux input-stack component (evdev + udev + epoll).
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libinput requires a Linux-kernel input stack, not {self.settings.os}")

    def requirements(self):
        # libevdev: the evdev wrapper libinput builds its device model on.
        self.requires("libevdev/1.13.7", transitive_headers=False, transitive_libs=True)
        # mtdev: multi-touch protocol translation (meson.build:147, >= 1.1.0).
        self.requires("mtdev/1.1.7", transitive_headers=False, transitive_libs=True)
        # libudev: meson.build:146 `dependency('libudev')` — hard requirement,
        # no fallback branch upstream.  ohpcd has no standalone libudev recipe,
        # but eudev declares `pkg_config_name = "libudev"`, so PkgConfigDeps
        # emits a libudev.pc that satisfies that lookup.
        #
        # headers/libs are declared EXPLICITLY on purpose.  eudev is packaged as
        # `package_type = "application"` (it ships the udevd daemon), and Conan
        # then defaults this requirement's traits to headers=False/libs=False
        # (conan/internal/model/requires.py:217-221, `process_package_type`),
        # which drops eudev's cpp_info — consumers would get no libudev.h and
        # the build fails with "fatal error: 'libudev.h' file not found".
        # Those defaults only apply when the trait is unset (`set_if_none`), so
        # declaring them here overrides that and honours eudev's real cpp_info
        # (it does install include/libudev.h and lib/libudev.so).
        # transitive_headers=True is likewise required: the public header
        # src/libinput.h:35 does `#include <libudev.h>`, so every consumer of
        # libinput compiles against libudev's headers.
        self.requires("eudev/3.2.14", headers=True, libs=True,
                      transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        get(self, url=source_data["url"],
            sha256=source_data.get("sha256", ""), strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        self._ensure_tmpdir()
        # libinput resolves libudev/mtdev/libevdev through pkg-config.
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # libwacom: tablet identification database — not in ohpcd, and libinput
        # builds fine without it (meson.build:161-166 falls back to a no-op dep).
        tc.project_options["libwacom"] = "false"
        # debug-gui: the GTK4 "libinput debug-gui" tool; needs GTK, not needed here.
        tc.project_options["debug-gui"] = "false"
        # tests: litest creates virtual devices through /dev/uinput.  Measured:
        # /dev/uinput is not accessible in this environment (EACCES), so the
        # suite cannot run; building it would only produce binaries that cannot
        # execute.  See notes.md — the upstream suite is reported as NOT RUN.
        tc.project_options["tests"] = "false"
        tc.project_options["install-tests"] = "false"
        tc.project_options["documentation"] = "false"
        # Conan 的 MesonToolchain 把 libexecdir 硬编码成 bindir
        # （conan/tools/meson/toolchain.py:358 `'libexecdir': bindir`），
        # 于是上游的两个安装目标撞在同一路径：
        #   主命令  libinput        → $prefix/bin/libinput      （文件）
        #   子工具  libinput-*      → $prefix/libexec/libinput/ （上游本意是目录）
        # 撞车后 install 报 "Destination .../bin/libinput already exists and
        # is not a file"。把 libexecdir 恢复成 meson 的默认值 libexec，
        # 即还原上游意图（主命令在 bin/、子工具在 libexec/libinput/）。
        tc.project_options["libexecdir"] = "libexec"
        tc.generate()
        self._inject_ar_ranlib()

    def build(self):
        self._ensure_tmpdir()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._resign_installed_elfs()
            if self.options.shared:
                self._create_shared_lib_aliases()

    def package_info(self):
        self.cpp_info.libs = ["input"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("pkg_config_name", "libinput")
        self.cpp_info.set_property("cmake_file_name", "libinput")
        self.cpp_info.set_property("cmake_target_name", "libinput::libinput")

    # ── Helper methods ────────────────────────────────────────────────

    def _ensure_tmpdir(self):
        """HarmonyOS /tmp is a read-only erofs (E002) — point TMPDIR somewhere writable."""
        tmpdir = os.environ.get("TMPDIR") or os.path.join(
            os.path.expanduser("~"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

    def _inject_ar_ranlib(self):
        """Set AR/RANLIB from the Conan profile's compiler_executables.

        Meson otherwise falls back to host `ar`, which is not the OHOS LLVM one.
        """
        compiler_executables = (
            self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
            or {}
        )
        ar = compiler_executables.get("ar")
        ranlib = compiler_executables.get("ranlib")
        cc = compiler_executables.get("c") or ""
        if not ar and cc:
            ar = os.path.join(os.path.dirname(cc), "llvm-ar")
        if not ranlib and cc:
            ranlib = os.path.join(os.path.dirname(cc), "llvm-ranlib")
        if ar:
            os.environ["AR"] = ar
        if ranlib:
            os.environ["RANLIB"] = ranlib

    def _create_shared_lib_aliases(self):
        """Ensure the libinput.so -> .so.N symlinks exist inside the package.

        Meson installs the real library plus its SONAME symlink; on HMDFS the
        symlink step can be lost, which breaks `-linput` for consumers.
        """
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        real = None
        for name in sorted(os.listdir(libdir)):
            if name.startswith("libinput.so.") and name != "libinput.so":
                real = name
                break
        if not real:
            return
        soname = "libinput.so." + real.split("libinput.so.")[1].split(".")[0]
        for src, dst in ((real, soname), (soname, "libinput.so")):
            src_path = os.path.join(libdir, src)
            dst_path = os.path.join(libdir, dst)
            if os.path.exists(src_path) and not os.path.exists(dst_path):
                os.symlink(src, dst_path)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _resign_installed_elfs(self):
        """Re-sign every installed ELF artifact for OHOS.

        The OHOS toolchain embeds a `.codesign` section at link time, and the
        loader refuses to map an ELF whose signature no longer matches its
        bytes.  `meson install` rewrites each ELF it installs — it blanks the
        build tree's RUNPATH in place with an equal-length "XXX..." string, so
        the installed file keeps its size but changes content, invalidating the
        signature.  Symptom (CI-shaped): the package builds and links, the
        consumer compiles and links, and then the run fails with

            Error loading shared library libinput.so.10: (needed by ./test_libinput)

        — note the empty reason.  Verified by comparing the two copies: the
        build tree's own libinput.so.10.13.0 loads fine and the test passes,
        while the installed one differs in 246 bytes and is refused.  So strip
        the stale section and re-sign what install produced.

        The scan is recursive because libinput installs its tools into
        `bin/libinput/` and the udev callouts into `lib/udev/`, not flat.
        """
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        for root, _dirs, files in os.walk(self.package_folder):
            for name in sorted(files):
                path = os.path.join(root, name)
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                if not self._is_elf(path):
                    continue
                self.run(f'"{objcopy}" --remove-section .codesign "{path}"')
                self.run(f'"{signer}" sign -inFile "{path}" -outFile "{path}" '
                         f'-selfSign 1')
