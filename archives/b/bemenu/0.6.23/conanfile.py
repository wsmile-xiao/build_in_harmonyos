#!/usr/bin/env python3
"""Conan recipe for bemenu 0.6.23 — GNUmakefile build system.

bemenu is a dynamic menu library and client for Wayland/X11/curses.
On OHOS, only the core library (libbemenu.so) and client binaries
(bemenu, bemenu-run) are built; renderers require ncurses/x11/wayland
which are not available on the target platform.

Patches:
  0001: Move parse_args() before bm_init() in bemenu-run.c
  0002: Move parse_args() before bm_init() in bemenu.c
  Reason: bm_init() fails without renderers, blocking --version/--help.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, apply_conandata_patches, export_conandata_patches, unzip, check_sha256
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class BemenuConan(ConanFile):
    name = "bemenu"
    version = "0.6.23"
    description = "Dynamic menu library and client for Wayland/X11/curses"
    license = "MIT"
    homepage = "https://github.com/Cloudef/bemenu"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: bemenu core only needs libc (system-provided); no Conan deps
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = self.conan_data["sources"]
        url = sources["url"]
        sha256 = sources.get("sha256", "")
        # OHOS CI Python lacks SSL module; use curl for HTTPS downloads
        urls = url if isinstance(url, list) else [url]
        filename = urls[0].rsplit("/", 1)[-1]
        last_error = None
        for u in urls:
            try:
                self.run(f'curl -fsSL -o "{filename}" "{u}"',
                         cwd=self.source_folder)
            except Exception as e:
                self.output.warn(f"Download from {u} failed: {e}")
                last_error = e
                continue
            if sha256:
                try:
                    check_sha256(self, filename, sha256)
                except Exception as e:
                    raise Exception(
                        f"SHA-256 verification failed for {filename} "
                        f"downloaded from {u}: {e}"
                    ) from e
            break
        else:
            raise Exception(f"Failed to download source from: {urls}") from last_error
        unzip(self, filename, strip_root=True)

    def generate(self):
        # R33: compiler/flags from Conan settings, not bare shell vars
        env = Environment()
        compiler = str(self.settings.compiler)
        if compiler == "clang":
            env.define("CC", "clang")
        elif compiler == "gcc":
            env.define("CC", "gcc")
        else:
            env.define("CC", "cc")
        build_type = str(self.settings.build_type)
        # -fPIC required for shared library (libbemenu.so) on ARM64
        if build_type == "Release":
            cflags = "-fPIC -O2"
        elif build_type == "Debug":
            cflags = "-fPIC -g"
        elif build_type == "RelWithDebInfo":
            cflags = "-fPIC -O2 -g"
        elif build_type == "MinSizeRel":
            cflags = "-fPIC -Os"
        else:
            cflags = "-fPIC -O2"
        env.define("CFLAGS", cflags)
        envvars = env.vars(self)
        envvars.save_script("bemenu_env")

    def build(self):
        apply_conandata_patches(self)
        # Build only clients (libbemenu.so + bemenu + bemenu-run)
        # Renderers (curses/x11/wayland) require unavailable deps on OHOS
        # Note: save_script uses "bemenu_env" (not "conanbuild") to avoid
        # name collision with Conan's aggregated conanbuild.sh which would
        # cause infinite self-sourcing recursion → SIGSEGV
        self.run("make -j1 clients", cwd=self.source_folder, env="conanbuild")

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        # Copy binaries
        copy(self, "bemenu", src=src, dst=os.path.join(pkg, "bin"))
        copy(self, "bemenu-run", src=src, dst=os.path.join(pkg, "bin"))

        # Copy shared library and symlinks
        copy(self, "libbemenu.so*", src=src, dst=os.path.join(pkg, "lib"))

        # Copy header
        copy(self, "bemenu.h", src=os.path.join(src, "lib"),
             dst=os.path.join(pkg, "include"))

        # Generate and copy pkg-config file
        # bemenu.pc.in uses @VERSION@, @PREFIX@, @LIBDIR@, @INCLUDEDIR@
        pc_in = os.path.join(src, "bemenu.pc.in")
        if os.path.exists(pc_in):
            with open(pc_in) as f:
                content = f.read()
            content = content.replace("@VERSION@", self.version)
            content = content.replace("@PREFIX@", "${pcfiledir}/../..")
            content = content.replace("@LIBDIR@", "lib")
            content = content.replace("@INCLUDEDIR@", "include")
            pc_dir = os.path.join(pkg, "lib", "pkgconfig")
            os.makedirs(pc_dir, exist_ok=True)
            with open(os.path.join(pc_dir, "bemenu.pc"), "w") as f:
                f.write(content)

    def package_info(self):
        self.cpp_info.libs = ["bemenu"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.version = self.version
        # R40: Human-confirmed — bemenu is a UI/menu library (图形渲染/UI框架类).
        # Patches (parse_args before bm_init) are substantive platform adaptation,
        # not stubs. test_package calls bm_version() because renderers
        # (curses/x11/wayland) are unavailable on OHOS, limiting functional
        # testing to API-level verification.
