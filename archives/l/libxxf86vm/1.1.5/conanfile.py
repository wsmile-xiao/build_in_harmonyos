#!/usr/bin/env python3
"""Conan recipe for X.Org libXxf86vm 1.1.5.

libXxf86vm provides the XF86VidMode extension client library for video
mode switching. The upstream source is a GitLab archive without
pre-generated autotools files; the recipe runs autoreconf in build()
after patching configure.ac to remove the xorg-macros dependency
(unavailable on OHOS).
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


class Libxxf86vmConan(ConanFile):
    name = "libxxf86vm"
    version = "1.1.5"
    description = "X.Org X11 Xxf86vm runtime library — VidMode extension for video mode switching"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxxf86vm"
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
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxxf86vm supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def build_requirements(self):
        self.tool_requires("util-macros/1.20.1")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pkg_config = PkgConfigDeps(self)
        pkg_config.set_property("libx11", "pkg_config_name", "x11")
        pkg_config.generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("lt_cv_deplibs_check_method=pass_all")
        if str(self.settings.os) == "OHOS":
            shell = self._ohos_shell()
            environment = tc.environment()
            environment.define_path("SHELL", shell)
            environment.define_path("CONFIG_SHELL", shell)
            environment.define_path("CC", self._compiler_executable("c", "clang"))
            environment.define_path("CXX", self._compiler_executable("cpp", "clang++"))
            environment.define_path("LD", self._tool_executable("ld.lld", "lld", "ld"))
            environment.define_path("AR", self._tool_executable("llvm-ar", "ar"))
            environment.define_path("RANLIB", self._tool_executable("llvm-ranlib", "ranlib"))
            environment.define_path("STRIP", self._tool_executable("llvm-strip", "strip"))
            environment.define_path("NM", self._tool_executable("llvm-nm", "nm"))
            environment.define("XXF86VM_CFLAGS", self._dep_cflags())
            environment.define("XXF86VM_LIBS", self._dep_libs())
            # Set LD_LIBRARY_PATH so configure test programs can find dep .so files
            for dependency in self.dependencies.host.values():
                for libdir in dependency.cpp_info.libdirs:
                    if not os.path.isabs(libdir):
                        libdir = os.path.join(dependency.package_folder, libdir)
                    if os.path.isdir(libdir):
                        environment.prepend_path("LD_LIBRARY_PATH", libdir)
            gnu_triplet = self._gnu_triplet()
            tc.update_configure_args({
                "--build": gnu_triplet,
                "--host": gnu_triplet,
            })
        tc.configure_args.extend([
            "--disable-docs",
            "--disable-specs",
            "--without-xmlto",
            "--without-fop",
            "--without-xsltproc",
        ])
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
        # Run autoreconf since source is a GitLab archive without pre-generated files
        apply_conandata_patches(self)
        self.run("autoreconf -v --install", cwd=self.source_folder, env="conanbuild")
        if str(self.settings.os) == "OHOS":
            self._patch_configure_runtime_shell()
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
        self._remove_libtool_archives()

    def package_info(self):
        self.cpp_info.libs = ["Xxf86vm"]
        self.cpp_info.requires = [
            "libx11::libx11",
            "libxext::libxext",
            "xorgproto::xorgproto",
        ]
        self.cpp_info.set_property("cmake_file_name", "libxxf86vm")
        self.cpp_info.set_property("cmake_target_name", "libxxf86vm::libxxf86vm")
        self.cpp_info.set_property("cmake_target_aliases", ["libxxf86vm::Xxf86vm"])
        self.cpp_info.set_property("pkg_config_name", "xxf86vm")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    # -- Build helpers -------------------------------------------------------

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

    def _dep_cflags(self):
        include_dirs = self._dependency_dirs("include")
        return " ".join(f"-I{path}" for path in include_dirs if os.path.isdir(path))

    def _dep_libs(self):
        flags = [f"-L{path}" for path in self._dependency_dirs("lib")]
        flags.append("-lX11")
        flags.append("-lXext")
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
        replace_in_file(self, configure_path, "umask 077", "umask 022", strict=False)

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
        with open(pc_file, "w", encoding="utf-8") as handle:
            handle.write(content)
