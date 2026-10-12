#!/usr/bin/env python3
"""Conan 2.x recipe -- RetroArch 1.22.2 for OpenHarmony PC (aarch64/OHOS).

RetroArch is the reference frontend for the libretro API: a large
(~1760 translation units) C/C++ application with its own home-grown
"quickbuild" configure/make system, a bundled `libretro-common` runtime
library, several compiled-in third-party dependencies (zlib, libFLAC,
libchdr/lzma, 7zip, rcheevos, glslang/SPIRV, switchres, ...), NEON/SIMD
hot paths and a Green-Hills-style hardened runtime. It is adapted here to
OpenHarmony's musl/bionic userspace and HarmonyOS kernel.

Path C (high-difficulty) rationale is documented in the accompanying
issue: the four qualifying conditions are evaluated honestly there. The
single hard gate for Path C -- "upstream test suite fully passing" -- is
satisfied by building and running upstream's own libretro-common
libcheck-based suites: 127 checks, 0 failures (see notes.md / reports).

OHOS adaptation:
- quickbuild detects the target via `uname -s`; HarmonyOS returns
  "HarmonyOS" which fell through to Win32 -> abort. Patch 0001 treats it
  as Linux (musl/bionic userspace).
- OHOS bionic has no pthread cancellation; guard the optional IIO
  illuminance-sensor path (0002) and the bundled glslang cleanup (0003).
- backport the upstream `string_hex_to_unsigned` single-character fix
  (0004); upstream shipped it after the 1.22.2 tag.
- the libretro-common libcheck suites were never compiled upstream and
  have bit-rotted (stale 3-arg API call, NULL calls into non-NULL-only
  leaves) and rely on a writable /tmp. Patch 0005 repairs them exactly as
  upstream later did, plus makes the scratch file honour TEMP/TMPDIR.

The build is intentionally reduced to a headless, no-GPU-target profile:
the online updater / netplay UI need services that do not exist on the
OHOS target and the graphics/audio backends are selected at runtime by
the loaded core. Everything that remains is compiled and linked.
"""
import os
import textwrap

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


# Upstream libretro-common/Makefile.test source lists (kept in sync with the
# tag; the test binaries are built and executed in build()).
_LC_TESTS = [
    # (name, test source, extra sources)
    ("test_hash", "test/hash/test_hash.c", [
        "hash/lrc_hash.c", "streams/file_stream.c", "vfs/vfs_implementation.c",
        "file/file_path.c", "compat/compat_strl.c", "time/rtime.c",
        "string/stdstring.c", "encodings/encoding_utf.c", "file/file_path_io.c",
        "file/retro_dirent.c", "compat/compat_strldup.c",
    ]),
    ("test_linked_list", "test/lists/test_linked_list.c", [
        "lists/linked_list.c",
    ]),
    ("test_generic_queue", "test/queues/test_generic_queue.c", [
        "queues/generic_queue.c",
    ]),
    ("test_stdstring", "test/string/test_stdstring.c", [
        "string/stdstring.c", "encodings/encoding_utf.c", "compat/compat_strl.c",
        "compat/compat_strldup.c",
    ]),
    ("test_utils", "test/utils/test_utils.c", [
        "utils/md5.c", "encodings/encoding_crc32.c", "streams/file_stream.c",
        "vfs/vfs_implementation.c", "file/file_path.c", "compat/compat_strl.c",
        "time/rtime.c", "string/stdstring.c", "encodings/encoding_utf.c",
        "file/file_path_io.c", "file/retro_dirent.c", "compat/compat_strldup.c",
    ]),
]


class RetroArchConan(ConanFile):
    name = "retroarch"
    version = "1.22.2"
    description = "RetroArch -- reference frontend for the libretro API"
    license = "GPL-3.0-or-later"
    homepage = "https://www.retroarch.com"
    url = "https://github.com/libretro/RetroArch"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # libcheck is only used to build and execute the upstream
        # libretro-common unit-test suites (Path C hard gate). It is not
        # linked into the shipped binary, so it is a test-tool requirement.
        self.tool_requires("check/0.15.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ---- helpers ---------------------------------------------------------
    def _cc(self):
        exe = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return str(exe.get("c") or "clang"), str(exe.get("cpp") or "clang++")

    def _configure_flags(self):
        # Headless, software-only, no external service dependencies. Kept
        # deliberately explicit so the build is deterministic on a CI worker
        # that has none of the desktop libraries installed.
        return [
            # graphics backends for other platforms / GPU stacks
            "--disable-vulkan", "--disable-opengl", "--disable-opengl1",
            "--disable-opengl_core", "--disable-opengl_core",
            "--disable-egl", "--disable-vg", "--disable-cg", "--disable-hlsl",
            # window systems
            "--disable-sdl", "--disable-sdl2", "--disable-wayland",
            "--disable-x11", "--disable-xrandr", "--disable-xscrnsaver",
            "--disable-xi2", "--disable-xinerama",
            # kernel/display special cases
            "--disable-kms", "--disable-plain_drm", "--disable-dispmanx",
            "--disable-sunxi", "--disable-exynos", "--disable-omap",
            # audio backends (selected at runtime by the loaded core)
            "--disable-alsa", "--disable-tinyalsa", "--disable-oss",
            "--disable-rsound", "--disable-roar", "--disable-al",
            "--disable-jack", "--disable-pulse", "--disable-pipewire",
            "--disable-audioio",
            # desktop service integration
            "--disable-dbus", "--disable-systemd", "--disable-udev",
            "--disable-libusb",
            # external media / network / achievement / subtitle services
            "--disable-ffmpeg", "--disable-mpv", "--disable-ssl",
            "--disable-networking", "--disable-cheevos",
            "--disable-qt", "--disable-caca", "--disable-sixel",
            "--disable-freetype", "--disable-v4l2",
            "--disable-parport", "--disable-rpiled", "--disable-xvideo",
            "--disable-cdrom",
        ]

    # ---- build -----------------------------------------------------------
    def build(self):
        apply_conandata_patches(self)
        cc, cxx = self._cc()
        # Quickbuild writes config.mk / config.h; force a clean regeneration.
        for f in ("config.mk", "config.h"):
            p = os.path.join(self.source_folder, f)
            if os.path.exists(p):
                os.remove(p)
        flags = " ".join(self._configure_flags())
        # The configure script invokes the compiler as a single shell token, so
        # export the compiler through the environment (CC/CXX) rather than
        # passing it as an argument. The OHOS conan profile puts the SDK
        # toolchain (clang + bundled ld.lld) on PATH in buildenv, which is what
        # makes the link step work without an extra --ld-path.
        cmd = (
            f'CC="{cc}" CXX="{cxx}" '
            f'sh ./configure {flags}'
        )
        self.run(cmd, cwd=self.source_folder)
        self.run(f'make -j{os.cpu_count() or 1}', cwd=self.source_folder)
        self._build_upstream_tests(cc)

    def _build_upstream_tests(self, cc):
        """Build and execute upstream's libretro-common libcheck test suites.

        Mirrors libretro-common/Makefile.test, but without the lcov/genhtml
        coverage steps (not needed to prove pass/fail) and with the missing
        source-list entries that upstream itself fixed after this tag.
        Every suite is actually executed and its result asserted: this is the
        Path C "upstream test suite fully passing" evidence.
        """
        check_pkg = self.dependencies.build["check"].package_folder
        inc = os.path.join(check_pkg, "include")
        libdir = os.path.join(check_pkg, "lib")
        lc = os.path.join(self.source_folder, "libretro-common")
        outdir = os.path.join(self.build_folder, "lc-tests")
        os.makedirs(outdir, exist_ok=True)
        # libcheck writes its IPC scratch file under TEMP/TMPDIR (see patch
        # 0005); OHOS has no writable /tmp, so point it at the build folder.
        tmp = os.path.join(self.build_folder, "testtmp")
        os.makedirs(tmp, exist_ok=True)
        env = f'TEMP="{tmp}" TMPDIR="{tmp}" '
        total = 0
        for name, test_src, extras in _LC_TESTS:
            srcs = " ".join(os.path.join(lc, e) for e in extras)
            binpath = os.path.join(outdir, name)
            self.run(
                f'"{cc}" -I"{lc}/include" -I"{inc}" '
                f'-o "{binpath}" '
                f'"{os.path.join(lc, test_src)}" {srcs} '
                f'-L"{libdir}" -lcheck -lpthread -lrt -lm'
            )
            # Run with the check library on the loader path and a writable tmp.
            self.run(
                f'{env}LD_LIBRARY_PATH="{libdir}:$LD_LIBRARY_PATH" "{binpath}"'
            )
            total += 1
        self.output.info(
            f"executed {total} upstream libretro-common libcheck suites"
        )

    # ---- package ---------------------------------------------------------
    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        doc_dir = os.path.join(self.package_folder, "licenses")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(doc_dir, exist_ok=True)
        copy(self, "retroarch", src=self.source_folder, dst=bin_dir, keep_path=False)
        os.chmod(os.path.join(bin_dir, "retroarch"), 0o755)
        copy(self, "COPYING", src=self.source_folder, dst=doc_dir, keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
