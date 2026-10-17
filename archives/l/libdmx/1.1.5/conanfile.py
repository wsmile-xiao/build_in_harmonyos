#!/usr/bin/env python3
"""Conan recipe for X.Org libdmx 1.1.5.

libdmx is the X11 Distributed Multihead X (DMX) extension client
library.  The upstream configure runs `PKG_CHECK_MODULES(DMX,
[x11 >= 1.6] xext xextproto [dmxproto >= 2.2.99.1])`; the single
translation unit src/dmx.c links Xlib and libXext only
(`libdmx_la_LIBADD` = @DMX_LIBS@).  xextproto and dmxproto are
headers-only and come from xorgproto (dmxproto.pc Version 2.3.1
satisfies >= 2.2.99.1).  All dependencies live on the cmd-pkgs track
(libx11/6.4.0 + libxext/6.4.0.1 + xorgproto/2025.1) with no vendoring.

The build reuses the CI-verified OHOS autotools pattern from
libxext/6.4.0.1 and libxres/1.2.1: clang as CC/CXX, an explicit
CONFIG_SHELL, TMPDIR inside the build folder, -j1 make, relocatable
pkg-config metadata, and no shipped .la archives.
"""

import os
import re
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


class LibdmxConan(ConanFile):
    name = "libdmx"
    version = "1.1.5"
    description = "X.Org Distributed Multihead X (DMX) extension client library"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libdmx"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
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
    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libdmx supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires(
            "libx11/6.4.0",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libxext/6.4.0.1",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def generate(self):
        pkg_config = PkgConfigDeps(self)
        pkg_config.set_property("libx11", "pkg_config_name", "x11")
        pkg_config.set_property("libxext", "pkg_config_name", "xext")
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
            environment.define("DMX_CFLAGS", self._module_cflags())
            environment.define("DMX_LIBS", self._module_libs("-lX11", "-lXext"))
            gnu_triplet = self._gnu_triplet()
            # libdmx 1.1.5 ships an older config.guess/config.sub pair that
            # does not know ohos.  The compiler target still comes from the
            # Conan profile; this pair is only for Autotools canonicalization.
            tc.update_configure_args(
                {
                    "--build": gnu_triplet,
                    "--host": gnu_triplet,
                }
            )
        tc.configure_args.extend(
            [
                "--disable-docs",
                "--disable-specs",
                "--without-xmlto",
                "--without-fop",
                "--without-xsltproc",
            ]
        )
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
            if self.options.get_safe("fPIC"):
                tc.configure_args.append("--with-pic")
        if str(self.settings.os) == "OHOS":
            tc.generate(env=environment)
        else:
            tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._patch_configure_runtime_shell()
        # E331/E237: rewrite dependency_libs in dependency .la files to
        # remove references to non-existent build-folder .la paths
        # (e.g. libXext.la under /.conan2/p/b/...). Conan packages do not
        # ship .la files, so libtool fails with "is not a valid libtool
        # archive" when recursively reading these stale paths. Mirrors
        # libxext/6.4.0.1 _fix_dep_la_files().
        self._fix_dep_la_files()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream libdmx 1.1.5 registers no TESTS/check_PROGRAMS; `make
        # check` exists but always reports zero tests.  Run it anyway so a
        # future upstream release that adds tests is not silently skipped.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._remove_libtool_archives()

    def package_info(self):
        self.cpp_info.libs = ["dmx"]
        self.cpp_info.requires = [
            "libx11::libx11",
            "libxext::libxext",
            "xorgproto::xorgproto",
        ]
        self.cpp_info.set_property("cmake_file_name", "libdmx")
        self.cpp_info.set_property("cmake_target_name", "libdmx::libdmx")
        self.cpp_info.set_property("pkg_config_name", "dmx")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

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

    def _module_cflags(self):
        include_dirs = self._dependency_dirs("include")
        return " ".join(f"-I{path}" for path in include_dirs if os.path.isdir(path))

    def _module_libs(self, *link_libs):
        flags = [f"-L{path}" for path in self._dependency_dirs("lib")]
        flags.extend(link_libs)
        return " ".join(flags)

    def _dependency_dirs(self, subdir):
        result = []
        for dependency in self.dependencies.host.values():
            path = os.path.join(dependency.package_folder, subdir)
            if os.path.isdir(path) and path not in result:
                result.append(path)
        return result

    def _patch_configure_runtime_shell(self):
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        shell = self._ohos_shell()
        replace_in_file(
            self,
            configure_path,
            "umask 077",
            "umask 022",
            strict=False,
        )
        for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
            replace_in_file(
                self,
                configure_path,
                pattern,
                f"#!{shell}",
                strict=False,
            )

    def _fix_dep_la_files(self):
        """Rewrite dependency_libs in dependency .la files to remove
        references to non-existent build-folder .la paths."""
        for dep in self.dependencies.values():
            package_folder = getattr(dep, "package_folder", None)
            if not package_folder:
                continue
            dep_lib = os.path.join(package_folder, "lib")
            if not os.path.isdir(dep_lib):
                continue
            for entry in os.listdir(dep_lib):
                if not entry.endswith(".la"):
                    continue
                la_path = os.path.join(dep_lib, entry)
                with open(la_path, "r", encoding="utf-8") as handle:
                    content = handle.read()
                new_content = content
                for match in re.finditer(r"(\S+\.la)", new_content):
                    la_ref = match.group(1)
                    if not os.path.isfile(la_ref):
                        new_content = new_content.replace(la_ref, "")
                # Clean up any double spaces left behind.
                new_content = re.sub(r"  +", " ", new_content)
                if new_content != content:
                    with open(la_path, "w", encoding="utf-8") as handle:
                        handle.write(new_content)

    def _remove_libtool_archives(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for entry in os.listdir(lib_dir):
            if entry.endswith(".la"):
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
        content = re.sub(
            r"^libdir=.*$",
            "libdir=${prefix}/lib",
            content,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r"^includedir=.*$",
            "includedir=${prefix}/include",
            content,
            flags=re.MULTILINE,
        )
        with open(pc_file, "w", encoding="utf-8") as handle:
            handle.write(content)
