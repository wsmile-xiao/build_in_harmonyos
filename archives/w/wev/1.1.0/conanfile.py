#!/usr/bin/env python3
"""Conan recipe for wev 1.1.0 — upstream plain Makefile + pkg-config.

wev is the Wayland event viewer ("xev for Wayland"): it prints every wl_*
event its surface receives, including keyboard/pointer/tablet details.

Upstream build system (Makefile, no configure step):
    WAYLAND_PROTOCOLS = pkg-config --variable=pkgdatadir wayland-protocols
    WAYLAND_SCANNER   = pkg-config --variable=wayland_scanner wayland-scanner
    SCDOC             = pkg-config --variable=scdoc scdoc
    LIBS              = pkg-config --cflags --libs wayland-client xkbcommon
    cc -std=c11 -o wev wev.c shm.c xdg-shell-protocol.c \
       wayland-tablet-protocol.c $(LIBS) -lrt
    install           = wev + wev.1 (man page composed by scdoc)

Adaptation notes (no source patch required):
  - Registry .pc files carry stale prefixes (`prefix=/` or a foreign build
    cache path), so every dependency .pc is copied into a private
    "fixed_pkgconfig" folder with prefix/exec_prefix/libdir/includedir
    rewritten to the real package folder and put first on PKG_CONFIG_PATH
    (hyprpicker/wayland precedent).
  - scdoc installs no .pc upstream, but wev's Makefile resolves the man page
    composer through `pkg-config --variable=scdoc scdoc` -> a minimal
    scdoc.pc is synthesised in the same private folder instead of patching
    the source.
  - pkgconf installs only `bin/pkgconf`, while the Makefile calls
    `pkg-config`; a private bin dir with a `pkg-config` entry is prepended
    to PATH (R49: everything stays inside the build/generators folders, no
    shared /usr/local injection).
  - R32: settings.os validated for Linux/OHOS.
  - R33: compiler taken from Conan conf, never from undefined shell vars.
  - R38: command-line tool -> commands.json declared at software level.
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class WevConan(ConanFile):
    name = "wev"
    version = "1.1.0"
    description = "Wayland event viewer (xev for Wayland)"
    license = "MIT"
    homepage = "https://git.sr.ht/~sircmpwn/wev"
    url = "https://git.sr.ht/~sircmpwn/wev"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: platform check must accept both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wev supports Linux/OHOS only, got {self.settings.os}")

    def requirements(self):
        # Makefile: pkg-config --cflags --libs wayland-client / xkbcommon
        self.requires("wayland/1.24.0")
        self.requires("libxkbcommon/1.13.1")
        # wayland-client.pc declares "Requires.private: libffi" — keep that
        # .pc resolvable (Conan marks pure transitive deps as skipped
        # binaries, which would leave pkg-config unable to resolve it)
        self.requires("libffi/3.4.4")
        # build-time data and tools, all resolved through pkg-config
        self.requires("wayland-protocols/1.47")  # protocol XML descriptions
        self.requires("scdoc/1.11.0")            # wev.1 man page composer
        self.requires("pkgconf/3.0.6")           # pkg-config implementation

    def layout(self):
        basic_layout(self)

    def _rewrite_pc(self, src, dst_dir, base):
        with open(src, encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r"(?m)^prefix=.*$", f"prefix={base}", content)
        content = re.sub(r"(?m)^exec_prefix=.*$", f"exec_prefix={base}", content)
        content = re.sub(r"(?m)^libdir=.*$", f"libdir={base}/lib", content)
        content = re.sub(r"(?m)^includedir=.*$", f"includedir={base}/include", content)
        # stale absolute build-cache paths (.../p/b/<hash>/p)
        content = re.sub(r"/[^\"\s]*/p/b/[^/\s]+/p", base, content)
        os.makedirs(dst_dir, exist_ok=True)
        with open(os.path.join(dst_dir, os.path.basename(src)), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(content)

    @staticmethod
    def _sign_ohos_elf(path):
        """Sign a HarmonyOS ELF copy so the kernel accepts executing it.

        E077: an ELF without a .codesign section is refused with EPERM
        ("Operation not permitted") when executed from HMDFS, no matter what
        the permission bits say.  The platform signer lives in the hnp
        toolchain; hosts that do not ship it simply keep the binary as-is.
        """
        signer = (shutil.which("binary-sign-tool")
                  or "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            return False
        signed = path + ".signed"
        try:
            subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", signed,
                 "-selfSign", "1"],
                check=True, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
        except (OSError, subprocess.CalledProcessError):
            return False
        os.replace(signed, path)
        try:
            os.chmod(path, 0o755)
        except OSError:
            # HMDFS ignores chmod, the copied mode is already 0770
            pass
        return True

    def generate(self):
        env = Environment()
        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        pc_dirs = []
        for dep in self.dependencies.values():
            base = dep.package_folder
            if not base:
                continue
            for sub in ("lib", "share"):
                pc_dir = os.path.join(base, sub, "pkgconfig")
                if not os.path.isdir(pc_dir):
                    continue
                pc_dirs.append(pc_dir)
                for name in sorted(os.listdir(pc_dir)):
                    if name.endswith(".pc"):
                        self._rewrite_pc(os.path.join(pc_dir, name),
                                         fixed_pc_dir, base)
                        self.output.info(f"wev: fixed {name} prefix -> {base}")
            if os.path.isdir(os.path.join(base, "bin")):
                env.prepend_path("PATH", os.path.join(base, "bin"))
            if os.path.isdir(os.path.join(base, "lib")):
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(base, "lib"))

        # scdoc ships no .pc file upstream, but the Makefile asks pkg-config
        # for the `scdoc` variable to compose wev.1
        scdoc_dep = self.dependencies["scdoc"]
        if scdoc_dep.package_folder:
            os.makedirs(fixed_pc_dir, exist_ok=True)
            with open(os.path.join(fixed_pc_dir, "scdoc.pc"), "w",
                      encoding="utf-8", newline="\n") as f:
                f.write(
                    f"prefix={scdoc_dep.package_folder}\n"
                    f"scdoc={scdoc_dep.package_folder}/bin/scdoc\n\n"
                    "Name: scdoc\n"
                    "Description: man page composer\n"
                    f"Version: {scdoc_dep.ref.version}\n")
        # wayland ships the protocol code generator, but the packaged binary
        # is unsigned and therefore cannot be executed on HarmonyOS (E077).
        # Run a signed private copy and publish it through a synthetic
        # wayland-scanner.pc, which shadows the packaged .pc rewritten above.
        wayland_dep = self.dependencies["wayland"]
        scanner_src = os.path.join(wayland_dep.package_folder or "",
                                   "bin", "wayland-scanner")
        if os.path.isfile(scanner_src):
            scanner_dir = os.path.join(self.generators_folder, "scanner")
            os.makedirs(scanner_dir, exist_ok=True)
            scanner_bin = os.path.join(scanner_dir, "wayland-scanner")
            shutil.copy2(scanner_src, scanner_bin)
            if self._sign_ohos_elf(scanner_bin):
                self.output.info(
                    "wev: signed private wayland-scanner copy (E077)")
            os.makedirs(fixed_pc_dir, exist_ok=True)
            with open(os.path.join(fixed_pc_dir, "wayland-scanner.pc"), "w",
                      encoding="utf-8", newline="\n") as f:
                f.write(
                    f"prefix={scanner_dir}\n"
                    f"wayland_scanner=${{prefix}}/wayland-scanner\n\n"
                    "Name: wayland-scanner\n"
                    "Description: Wayland protocol code generator\n"
                    f"Version: {wayland_dep.ref.version}\n")
        # the signed private copy must win over the unsigned packaged
        # binary: fixed_pc_dir is already first on PKG_CONFIG_PATH, so keep
        # the PATH order symmetric as well
        env.prepend_path("PATH", scanner_dir)

        if pc_dirs:
            env.prepend_path("PKG_CONFIG_PATH",
                             os.pathsep.join([fixed_pc_dir] + pc_dirs))

        # the Makefile invokes `pkg-config`; the pkgconf package only ships
        # `pkgconf`, so expose it under that name inside the build folder
        pkgconf_bin = os.path.join(self.dependencies["pkgconf"].package_folder or "",
                                   "bin", "pkgconf")
        shim_dir = os.path.join(self.generators_folder, "pkgconfig_bin")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "pkg-config")
        if os.path.lexists(shim):
            os.remove(shim)
        if os.path.isfile(pkgconf_bin):
            try:
                os.symlink(pkgconf_bin, shim)
            except OSError:
                with open(shim, "w", encoding="utf-8", newline="\n") as f:
                    f.write(f'#!/bin/sh\nexec "{pkgconf_bin}" "$@"\n')
                os.chmod(shim, 0o755)
        env.prepend_path("PATH", shim_dir)
        env.vars(self).save_script("conanbuild_env")

    def source(self):
        get(self, strip_root=True, **self.conan_data["sources"])

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler comes from the Conan profile, not from shell vars
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        # `make` default goal is `all` = wev + wev.1 (man page).
        # basic_layout() separates source and build folders, and the Makefile
        # generates the xdg-shell/tablet protocol sources in-tree, so make has
        # to run inside source_folder (same idiom as scdoc).
        self.run(f"make CC={cc} -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        copy(self, "wev", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "wev.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
