#!/usr/bin/env python3
"""Conan recipe for libXScrnSaver (libxss) 1.2.4.

The upstream source is a GitLab archive tarball (not a release tarball),
so it ships only configure.ac — no pre-generated configure/Makefile.in.
Build-time autoreconf is required, provided by tool_requires
(util-macros, automake, libtool).

configure.ac uses PKG_CHECK_MODULES for x11, xext, xextproto, and
scrnsaverproto.  xorgproto/2025.1 provides the protocol .pc files;
libx11/6.4.0 and libxext/6.4.0 are normal Conan requirements.
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


class LibxssConan(ConanFile):
    name = "libxss"
    version = "1.2.4"
    description = "X.Org X11 Screen Saver extension client library"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxscrnsaver"
    url = "https://gitlab.freedesktop.org/xorg/lib/libxscrnsaver"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

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
                f"libxss supports Linux and OHOS, not {self.settings.os}"
            )

    def build_requirements(self):
        self.tool_requires("util-macros/1.20.1")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pkg_config = PkgConfigDeps(self)
        pkg_config.set_property("libx11", "pkg_config_name", "x11")
        pkg_config.set_property("libxext", "pkg_config_name", "xext")
        pkg_config.generate()
        self._copy_xorgproto_pc_files()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            shell = self._ohos_shell()
            env = tc.environment()
            env.define_path("SHELL", shell)
            env.define_path("CONFIG_SHELL", shell)
            env.define_path("CC", self._compiler_executable("c", "clang"))
            env.define_path("CXX", self._compiler_executable("cpp", "clang++"))
            env.define_path("AR", self._tool_executable("llvm-ar", "ar"))
            env.define_path("RANLIB", self._tool_executable("llvm-ranlib", "ranlib"))
            env.define_path("STRIP", self._tool_executable("llvm-strip", "strip"))
            env.define_path("NM", self._tool_executable("llvm-nm", "nm"))
            env.define("XSCRNSAVER_CFLAGS", self._dep_cflags())
            env.define("XSCRNSAVER_LIBS", self._dep_libs())
            triplet = self._gnu_triplet()
            tc.update_configure_args(
                {"--build": triplet, "--host": triplet}
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
            tc.generate(env=env)
        else:
            tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._autoreconf()
        if str(self.settings.os) == "OHOS":
            self._patch_configure_shell()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

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
        self._cleanup_libtool_and_pc()

    def package_info(self):
        self.cpp_info.libs = ["Xss"]
        self.cpp_info.requires = [
            "libx11::libx11",
            "libxext::libxext",
            "xorgproto::xorgproto",
        ]
        self.cpp_info.set_property("cmake_file_name", "libxss")
        self.cpp_info.set_property("cmake_target_name", "libxss::libxss")
        self.cpp_info.set_property("pkg_config_name", "xscrnsaver")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    # ── helpers ──────────────────────────────────────────────────

    def _autoreconf(self):
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")

    def _copy_xorgproto_pc_files(self):
        dep = self.dependencies["xorgproto"]
        src_dir = os.path.join(dep.package_folder, "share", "pkgconfig")
        for name in ("xextproto.pc", "scrnsaverproto.pc"):
            src = os.path.join(src_dir, name)
            if not os.path.isfile(src):
                continue
            with open(src, encoding="utf-8") as fh:
                content = fh.read()
            content = content.replace(
                "prefix=${pcfiledir}/../..",
                "prefix={}".format(dep.package_folder.replace("\\", "/")),
            )
            dst = os.path.join(self.generators_folder, name)
            with open(dst, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(content)

    def _patch_configure_shell(self):
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        shell = self._ohos_shell()
        replace_in_file(self, configure_path, "umask 077", "umask 022", strict=False)
        for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
            replace_in_file(self, configure_path, pattern, f"#!{shell}", strict=False)

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
            "tools.build:compiler_executables", default={}, check_type=dict
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

    def _dep_cflags(self):
        dirs = self._dependency_dirs("include")
        return " ".join(f"-I{p}" for p in dirs if os.path.isdir(p))

    def _dep_libs(self):
        flags = [f"-L{p}" for p in self._dependency_dirs("lib")]
        flags.extend(["-lX11", "-lXext"])
        return " ".join(flags)

    def _dependency_dirs(self, subdir):
        result = []
        for dep in self.dependencies.host.values():
            path = os.path.join(dep.package_folder, subdir)
            if os.path.isdir(path) and path not in result:
                result.append(path)
        return result

    def _cleanup_libtool_and_pc(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for entry in os.listdir(lib_dir):
            if entry.endswith(".la"):
                os.remove(os.path.join(lib_dir, entry))
        pc_dir = os.path.join(lib_dir, "pkgconfig")
        if not os.path.isdir(pc_dir):
            return
        for pc_file in os.listdir(pc_dir):
            if pc_file.endswith(".pc"):
                self._make_pc_relocatable(os.path.join(pc_dir, pc_file))

    def _make_pc_relocatable(self, pc_file):
        with open(pc_file, "r", encoding="utf-8") as fh:
            content = fh.read()
        content = re.sub(
            r"^prefix=.*$", "prefix=${pcfiledir}/../..",
            content, flags=re.MULTILINE,
        )
        content = re.sub(
            r"^exec_prefix=.*$", "exec_prefix=${prefix}",
            content, flags=re.MULTILINE,
        )
        with open(pc_file, "w", encoding="utf-8") as fh:
            fh.write(content)
