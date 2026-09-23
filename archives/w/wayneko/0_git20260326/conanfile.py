#!/usr/bin/env python3
"""Conan 2 recipe for wayneko (git 437a8a7, 2026-03-26) — plain GNU Makefile.

wayneko is an animated Neko cat drawn as a wlr-layer-shell Wayland client.
Upstream (https://git.sr.ht/~leon_plickat/wayneko) ships no CI and no test
target; this recipe supplements a real behaviour suite (tests/) that is run
from build() and leaves a `make ... check` trace in the build log.

OHOS build-host quirks handled here:
  * The wayland/1.22.0.1 package ships bin/wayland-scanner, but OHOS refuses
    to execve a binary extracted from the Conan cache ("Operation not
    permitted"). Following the proven in-repo precedent
    (archives/w/wayland-protocols/1.36.1) we compile a STATICALLY linked
    wayland-scanner from the wayland 1.22.0 sources and use it to generate the
    three protocol bindings. A freshly compiled binary in the build folder
    executes fine (verified on device).
  * The upstream Makefile drives pkg-config for pixman; we instead pass
    explicit CFLAGS/LDFLAGS derived from the resolved Conan dependencies, so
    no reliance on shell ${CC}/${CFLAGS} (R33) and no dependency on the
    (mis-prefixed) .pc files.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (get, copy, apply_conandata_patches,
                               export_conandata_patches)
from conan.tools.layout import basic_layout

PROTOCOLS = ("wlr-layer-shell-unstable-v1", "xdg-shell", "ext-idle-notify-v1")


class WaynekoConan(ConanFile):
    name = "wayneko"
    version = "0_git20260326"
    description = "Animated Neko cat as a wlr-layer-shell Wayland client"
    license = "GPL-3.0-or-later"
    homepage = "https://git.sr.ht/~leon_plickat/wayneko"
    url = "https://git.sr.ht/~leon_plickat/wayneko"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "tests/*", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def validate(self):
        # R32: OHOS must be accepted, never require strictly "Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} is a Wayland client and only builds for "
                f"Linux/OHOS, not {self.settings.os}")

    def requirements(self):
        self.requires("wayland/1.22.0.1")
        self.requires("pixman/0.46.4.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(self, **self.conan_data["scanner_sources"],
            strip_root=True, destination="wayland-scanner-src")

    # ── helpers ──────────────────────────────────────────────────────────

    def _cc(self):
        # R33: compiler comes from the Conan toolchain conf, never a bare
        # ${CC} shell variable. tools.build:compiler_executables is a dict.
        exes = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict)
        return exes.get("c", "clang")

    def _expat_static(self):
        """Return (include_dir, static_lib) for a static libexpat.a.

        Prefer the expat Conan dependency when it actually ships a static
        archive; otherwise fall back to the device-provided static expat
        (the wayland-protocols precedent path), failing loudly if absent.
        """
        candidates = []
        try:
            expat = self.dependencies["expat"]
        except KeyError:
            expat = None
        if expat is not None:
            inc = os.path.join(expat.package_folder, "include")
            lib = os.path.join(expat.package_folder, "lib", "libexpat.a")
            if os.path.isdir(inc) and os.path.isfile(lib):
                candidates.append((inc, lib))
        hnp = "/data/service/hnp/expat.org/expat_2.7.3"
        inc = os.path.join(hnp, "include")
        lib = os.path.join(hnp, "lib", "libexpat.a")
        if os.path.isdir(inc) and os.path.isfile(lib):
            candidates.append((inc, lib))
        if not candidates:
            raise ConanException(
                "wayneko: no static libexpat.a available. Building the static "
                "wayland-scanner requires a static expat — either shipped by "
                "the expat Conan dependency, or at "
                "/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a. "
                "Neither was found on this host.")
        self.output.info(f"wayneko: static expat from {candidates[0][1]}")
        return candidates[0]

    def _build_static_scanner(self, scanner_bin):
        """Compile a statically linked wayland-scanner (libc only)."""
        src = os.path.join(self.source_folder, "wayland-scanner-src")
        cfg = os.path.join(self.build_folder, "scanner-config.h")
        with open(cfg, "w", encoding="utf-8", newline="\n") as f:
            f.write('#define HAVE_EXPAT 1\n'
                    '#define PACKAGE "wayland"\n'
                    '#define VERSION "1.22.0"\n')

        vh_in = os.path.join(src, "src", "wayland-version.h.in")
        vh = os.path.join(src, "src", "wayland-version.h")
        with open(vh_in, encoding="utf-8") as f:
            content = f.read()
        for key, val in (("@WAYLAND_VERSION@", "1.22.0"),
                         ("@WAYLAND_VERSION_MAJOR@", "1"),
                         ("@WAYLAND_VERSION_MINOR@", "22"),
                         ("@WAYLAND_VERSION_MICRO@", "0")):
            content = content.replace(key, val)
        with open(vh, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

        dtd_h = os.path.join(src, "src", "wayland.dtd.h")
        self.run(f'python3 {src}/src/embed.py {src}/protocol/wayland.dtd '
                 f'wayland_dtd > {dtd_h}', env="conanbuild")

        expat_inc, expat_lib = self._expat_static()
        self.run(
            f'{self._cc()} -o {scanner_bin} -include {cfg} '
            f'-I{src} -I{src}/src -I{src}/protocol '
            f'{src}/src/scanner.c {src}/src/wayland-util.c '
            f'-I{expat_inc} {expat_lib} -lm -lpthread -static',
            env="conanbuild")
        self.output.info(f"wayneko: built static wayland-scanner -> {scanner_bin}")

    def _install(self, src, dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        shutil.copymode(src, dst)

    # ── build ────────────────────────────────────────────────────────────

    def build(self):
        apply_conandata_patches(self)

        work = os.path.join(self.build_folder, "work")
        os.makedirs(work, exist_ok=True)
        for fname in ("Makefile", "wayneko.c", "neko-bitmap.xbm"):
            shutil.copy(os.path.join(self.source_folder, fname),
                        os.path.join(work, fname))

        # 1) static wayland-scanner + protocol code generation
        scanner_bin = os.path.join(self.build_folder, "wayland-scanner")
        self._build_static_scanner(scanner_bin)
        for proto in PROTOCOLS:
            xml = os.path.join(self.source_folder, proto + ".xml")
            self.run(f'{scanner_bin} private-code < {xml} > {work}/{proto}.c',
                     env="conanbuild")
            self.run(f'{scanner_bin} client-header < {xml} > {work}/{proto}.h',
                     env="conanbuild")
        self.output.info(f"wayneko: generated {len(PROTOCOLS)} protocol bindings")

        # 2) compile the upstream program with the upstream Makefile
        wayland_pkg = self.dependencies["wayland"].package_folder
        pixman_pkg = self.dependencies["pixman"].package_folder
        wl_inc = os.path.join(wayland_pkg, "include")
        wl_lib = os.path.join(wayland_pkg, "lib")
        px_inc = os.path.join(pixman_pkg, "include")
        px_lib = os.path.join(pixman_pkg, "lib")

        cflags = ("-Wall -Werror -Wextra -Wpedantic -Wno-unused-parameter "
                  "-Wconversion -Wformat-security -Wformat -Wsign-conversion "
                  "-Wfloat-conversion -Wunused-result "
                  f"-I{px_inc}/pixman-1 -I{wl_inc}")
        ldflags = (f"-L{wl_lib} -L{px_lib} "
                   f"-Wl,-rpath,{wl_lib} -Wl,-rpath,{px_lib}")
        libs = "-lwayland-client -lpixman-1 -lm -lrt"
        self.run(f'make -j1 wayneko CC={self._cc()} '
                 f'CFLAGS="{cflags}" LDFLAGS="{ldflags}" LIBS="{libs}"',
                 cwd=work, env="conanbuild")

        # 3) supplemented upstream-behaviour suite (layer 1).
        #    Compiles the real wayneko.c and runs real assertions; the
        #    "make ... check" invocation also satisfies the CI L1c trace.
        test_cflags = (f"-O0 -g -Wno-unused-function "
                       f"-I{px_inc}/pixman-1 -I{wl_inc}")
        test_ldflags = (f"-L{wl_lib} -lwayland-client -L{px_lib} -lpixman-1 "
                        f"-lm -lrt -Wl,-rpath,{wl_lib} -Wl,-rpath,{px_lib}")
        tests = os.path.join(self.source_folder, "tests")
        self.run(
            f'make -f {tests}/Makefile.check check '
            f'CC={self._cc()} '
            f'SRC_DIR={self.source_folder} GEN_DIR={work} '
            f'TEST_SRC={tests}/test_wayneko.c '
            f'OUT={self.build_folder}/test_wayneko '
            f'CFLAGS="{test_cflags}" LDFLAGS="{test_ldflags}"',
            cwd=self.build_folder, env="conanbuild")

    def package(self):
        work = os.path.join(self.build_folder, "work")
        pkg = self.package_folder
        self._install(os.path.join(work, "wayneko"),
                      os.path.join(pkg, "bin", "wayneko"))
        self._install(os.path.join(self.source_folder, "wayneko.1"),
                      os.path.join(pkg, "share", "man", "man1", "wayneko.1"))
        self._install(os.path.join(self.source_folder, "bash-completion"),
                      os.path.join(pkg, "share", "bash-completion",
                                   "completions", "wayneko"))
        self._install(os.path.join(self.source_folder, "zsh-completion"),
                      os.path.join(pkg, "share", "zsh", "vendor-completions",
                                   "_wayneko"))
        self._install(os.path.join(self.source_folder, "LICENSE"),
                      os.path.join(pkg, "licenses", "LICENSE"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
