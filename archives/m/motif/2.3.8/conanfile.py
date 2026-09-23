#!/usr/bin/env python3
"""Conan recipe for Motif 2.3.8 (the ``libXm.so.4`` X11 user-interface toolkit).

Package version follows the Open Group / SourceForge "Motif 2.3.8" release and
the historical ``libXm.so.4`` ABI (SONAME ``libXm.so.4``, real file
``libXm.so.4.0.4``). Consumers such as ``dinotrace`` link ``-lXm``.

Scope note: only the ``lib/`` subdirectory (the ``Xm`` and ``Mrm`` libraries)
is built. A full-tree ``make`` fails in ``tools/wml`` because the OHOS
``ld.lld`` cannot link the host-only ``wmluiltok`` helper (``undefined symbol:
main``); see notes.md for the raw error. ``make -C lib`` builds cleanly.
"""

import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class MotifConan(ConanFile):
    name = "motif"
    version = "2.3.8"
    description = "Motif (libXm.so.4) X11 user-interface toolkit"
    license = "LGPL-2.1-or-later"
    homepage = "https://sourceforge.net/projects/motif/"
    url = "https://sourceforge.net/projects/motif/"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }
    # Ship the X11 xbitmaps data-file shim (files/X11/bitmaps/gray) with the
    # recipe sources; export_conandata_patches() alone does not copy it.
    exports_sources = ("files/*",)

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: accept both Linux and OHOS, never `== "Linux"` only.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"motif supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # libXm headers include <X11/Xlib.h>, <X11/Intrinsic.h>, <X11/Xresource.h>
        # and <X11/extensions/shape.h>, so libx11, libxt, libxext and xorgproto
        # surface their public headers to consumers.
        # libxt/1.3.1 pins libx11/1.8.13 while libxext pins libx11/6.4.0.
        # Force libx11/1.8.13 (keeps libX11.la, required by libxt's shadow
        # recipe) and use the libxext/6.4.0.1 revision whose published binary
        # already targets that line -- the exact pair libxmu/1.3.1 ships.
        self.requires(
            "libx11/1.8.13",
            force=True,
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("libxt/1.3.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)
        # libXt links libSM/libICE; libXm.so.4 fails to load without them, so
        # keep them pinned as direct runtime requirements.
        self.requires("libsm/1.2.6", transitive_libs=True)
        self.requires("libice/1.1.2", transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        source_data = dict(self.conan_data["sources"][str(self.version)])
        # Metadata keys documented in conandata.yml are not get() arguments.
        source_data.pop("upstream_version", None)
        source_data.pop("tar_format", None)
        get(self, **source_data, strip_root=True)

    def generate(self):
        pkg_config = PkgConfigDeps(self)
        pkg_config.generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            shell = self._ohos_shell()
            environment = tc.environment()
            environment.define_path("SHELL", shell)
            environment.define_path("CONFIG_SHELL", shell)
            environment.define_path("CC", self._compiler_executable("c", "clang"))
            environment.define_path("CXX", self._compiler_executable("cpp", "clang++"))
            environment.define_path("LD", self._tool_executable("ld.lld", "lld", "ld"))
            environment.define_path("AR", self._tool_executable("llvm-ar", "ar"))
            environment.define_path(
                "RANLIB", self._tool_executable("llvm-ranlib", "ranlib")
            )
            environment.define_path(
                "STRIP", self._tool_executable("llvm-strip", "strip")
            )
            environment.define_path("NM", self._tool_executable("llvm-nm", "nm"))
            # Dependency include roots + the X11 xbitmaps data-file shim
            # (<source>/files/X11/bitmaps/gray) + the musl rindex->strrchr shim.
            environment.append("CPPFLAGS", self._motif_cppflags())
            environment.append("LDFLAGS", self._motif_ldflags())
            gnu_triplet = self._gnu_triplet()
            # Motif 2.3.8 ships a 2016 config.guess; pin the canonical triplet so
            # Autotools canonicalization matches the OHOS clang target.
            tc.update_configure_args(
                {
                    "--build": gnu_triplet,
                    "--host": gnu_triplet,
                }
            )
        tc.configure_args.extend(
            [
                "--disable-printing",
                "--disable-xft",
                "--disable-jpeg",
                "--disable-png",
            ]
        )
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
            if self.options.get_safe("fPIC"):
                tc.configure_args.append("--with-pic")
        # Motif's configure probes X11/X.h via --x-includes/--x-libraries.
        libx11 = self.dependencies["libx11"]
        tc.configure_args.append(f"--x-includes={libx11.package_folder}/include")
        tc.configure_args.append(f"--x-libraries={libx11.package_folder}/lib")
        if str(self.settings.os) == "OHOS":
            tc.generate(env=environment)
        else:
            tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._patch_configure_runtime_shell()
        autotools = Autotools(self)
        autotools.configure()
        # Only lib/ builds on OHOS; the full-tree make fails in tools/wml.
        # `-C lib` selects the proven subdirectory target.
        autotools.make(args=["-C", "lib", "-j1"])
        # ── Layer 1: upstream official test (docs/TEST_QUALITY_SPEC.md §3.1) ──
        # lib/ is an automake tree (lib/Makefile.am: SUBDIRS = Xm Mrm), so the
        # standard `check`/`check-recursive` targets exist (lib/Makefile.in has
        # `check: check-recursive`; each subdir has `check-am: all-am`). Motif
        # 2.3.8 registers 0 test cases (0 check_PROGRAMS/TESTS across all 109
        # Makefile.am), so this recurses into Xm/Mrm and reports nothing to run
        # — but it IS invoked from build() so the upstream-check execution is
        # traced in the conan create log (CI L1c). It runs after `make -C lib`
        # so the check targets' `all-am` prerequisite is already satisfied.
        autotools.make(args=["-C", "lib", "check", "-j1"])

    def package(self):
        # Install only the lib/ subtree into the package folder (DESTDIR staging,
        # configure --prefix=/). Avoids the tools/ install that cannot build.
        pkg = shlex.quote(self.package_folder)
        self.run(f"make -C lib install DESTDIR={pkg} -j1")
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._remove_libtool_archives()

    def package_info(self):
        self.cpp_info.libs = ["Xm"]
        self.cpp_info.requires = [
            "libx11::libx11",
            "libxt::libxt",
            "libxext::libxext",
            "libsm::libsm",
            "libice::libice",
            "xorgproto::xorgproto",
        ]
        self.cpp_info.set_property("cmake_file_name", "motif")
        self.cpp_info.set_property("cmake_target_name", "motif::motif")
        self.cpp_info.set_property("cmake_target_aliases", ["motif::Xm"])
        self.cpp_info.set_property("pkg_config_name", "motif")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    # ------------------------------------------------------------------
    # OHOS helpers (mirrors libxext 6.4.0)
    # ------------------------------------------------------------------

    def _gnu_triplet(self):
        arch = str(self.settings.arch)
        machine = {
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "x86_64": "x86_64",
            "armv7": "arm",
        }.get(arch, arch)
        return f"{machine}-unknown-linux-gnu"

    def _ohos_shell(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("sh"),
            "/system/bin/sh",
            "/bin/sh",
            "/usr/bin/sh",
            "/data/service/hnp/bin/bash",
        ):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return "/system/bin/sh"

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _tool_executable(self, *names):
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return names[0]

    def _dependency_dirs(self, subdir):
        result = []
        for dependency in self.dependencies.host.values():
            path = os.path.join(dependency.package_folder, subdir)
            if os.path.isdir(path) and path not in result:
                result.append(path)
        return result

    def _motif_cppflags(self):
        flags = [f"-I{path}" for path in self._dependency_dirs("include")]
        # X11 xbitmaps data-file shim: lib/Xm/I18List.c and lib/Xm/IconButton.c
        # #include <X11/bitmaps/gray>, which is shipped by X.Org 'xbitmaps'
        # (not published on OHOS). files/X11/bitmaps/gray provides it.
        flags.append(f"-I{os.path.join(self.source_folder, 'files')}")
        # musl/OHOS has no rindex(3); XpmI.h only maps it under SYSV/SVR4/etc.
        flags.append("-Drindex=strrchr")
        return flags

    def _motif_ldflags(self):
        flags = []
        for path in self._dependency_dirs("lib"):
            flags.append(f"-L{path}")
            flags.append(f"-Wl,-rpath-link,{path}")
        return flags

    def _patch_configure_runtime_shell(self):
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        shell = self._ohos_shell()
        # E011: HMDFS ignores chmod and uses umask 077, which makes config.status
        # subdirs unwritable. Force umask 022.
        replace_in_file(
            self,
            configure_path,
            "umask 077",
            "umask 022",
            strict=False,
        )
        # /bin/sh and /bin/bash do not exist on OHOS; repoint the shebang.
        for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
            replace_in_file(
                self,
                configure_path,
                pattern,
                f"#!{shell}",
                strict=False,
            )

    def _remove_libtool_archives(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for entry in os.listdir(lib_dir):
            if not entry.endswith(".la"):
                continue
            os.remove(os.path.join(lib_dir, entry))
        for pc_file in self._pkg_config_files(lib_dir):
            self._make_pc_relocatable(pc_file)

    def _pkg_config_files(self, lib_dir):
        pc_dir = os.path.join(lib_dir, "pkgconfig")
        if not os.path.isdir(pc_dir):
            return []
        return [
            os.path.join(pc_dir, entry)
            for entry in os.listdir(pc_dir)
            if entry.endswith(".pc")
        ]

    def _make_pc_relocatable(self, pc_file):
        with open(pc_file, "r", encoding="utf-8") as handle:
            content = handle.read()
        content = re.sub(
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            content,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r"^exec_prefix=.*$",
            "exec_prefix=${prefix}",
            content,
            flags=re.MULTILINE,
        )
        with open(pc_file, "w", encoding="utf-8") as handle:
            handle.write(content)
