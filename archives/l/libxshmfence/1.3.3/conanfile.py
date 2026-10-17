#!/usr/bin/env python3
"""Conan recipe for libxshmfence 1.3.3.

libxshmfence provides an X shared-memory fence primitive (futex- or
pthread-backed) used by the X server and DRI3 clients.  The upstream
configure only runs ``PKG_CHECK_MODULES(XPROTO, xproto)`` — xproto is a
headers-only module shipped by xorgproto — so the only dependency is
``xorgproto/2025.1`` and the library links nothing but pthreads when futexes
are unavailable.

Shared-memory-dir trap: ``AC_ARG_WITH(shared-memory-dir)`` auto-detects
``/run/shm /dev/shm /var/tmp /tmp`` at configure time and hard-fails with
"No directory found for shared memory temp files" if none exist.  The OHOS
CI worker has no ``/tmp``, so we point ``--with-shared-memory-dir`` at a
writable dir inside the build folder.  At runtime the primary allocation
path is ``memfd_create(2)`` (present on the OHOS Linux kernel); the
SHMDIR-backed ``mkostemp`` fallback is only hit when memfd is unavailable,
so the baked path never matters for real consumers.

The build reuses the CI-verified OHOS autotools pattern from libxcursor/
libxkbfile: clang as CC/CXX, an explicit CONFIG_SHELL, TMPDIR/TMP/TEMP
inside the build folder, -j1 make, and relocatable .pc metadata.
"""

import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibxshmfenceConan(ConanFile):
    name = "libxshmfence"
    version = "1.3.3"
    description = "X shared memory fence library"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxshmfence"
    url = "https://gitlab.freedesktop.org/xorg/lib/libxshmfence"
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
                f"libxshmfence supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # xproto is a headers-only module from xorgproto; configure uses it
        # only for XPROTO_CFLAGS, and xshmfence.h includes X11/Xfuncproto.h.
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
            gnu_triplet = self._gnu_triplet()
            tc.update_configure_args(
                {
                    "--build": gnu_triplet,
                    "--host": gnu_triplet,
                }
            )
            tc.extra_cflags.append("-Qunused-arguments")
            tc.extra_cflags.append("-Wno-error=unused-command-line-argument")
            self._add_dependency_flags(tc)
            # OHOS worker has no /tmp, so point the shm dir at a writable
            # build-folder path to satisfy configure's auto-detect check.
            shm_dir = os.path.join(self.build_folder, "tmp")
            tc.configure_args.append(f"--with-shared-memory-dir={shm_dir}")
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
        # Mirror the CI-verified toolchain pattern from libxcb/1.16: the OHOS
        # worker has no /tmp and the build uid is absent from /etc/passwd, so
        # clang's temp-file creation fails unless TMPDIR/TMP/TEMP point into the
        # build folder, and the tool helpers need a PATH prepend + env patch.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        build_env = Environment()
        build_env.define("TMPDIR", tmpdir)
        build_env.define("TMP", tmpdir)
        build_env.define("TEMP", tmpdir)
        build_env.define("TMPPREFIX", os.path.join(tmpdir, "zsh"))
        if str(self.settings.os) == "OHOS":
            self._prepend_ohos_tool_paths()
            build_env.define("CK_FORK", "no")
            shell = self._resolve_shell()
            self._patch_conan_env_scripts(shell)
            build_env.define("CONFIG_SHELL", shell)
            build_env.define("SHELL", shell)
            for variable, tool in {
                "LD": "ld.lld",
                "AR": "llvm-ar",
                "RANLIB": "llvm-ranlib",
                "NM": "llvm-nm",
                "STRIP": "llvm-strip",
            }.items():
                build_env.define(variable, self._resolve_ohos_tool(tool))
            self._add_runtime_library_paths(build_env)

        autotools = Autotools(self)
        with VirtualBuildEnv(self).vars().apply(), build_env.vars(self).apply():
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
        # Upstream builds libxshmfence.so.1 (version-number 1:0:0); the conan
        # libs entry must match the file so CMakeDeps find_library works.
        self.cpp_info.libs = ["xshmfence"]
        self.cpp_info.requires = ["xorgproto::xorgproto"]
        self.cpp_info.set_property("cmake_file_name", "libxshmfence")
        self.cpp_info.set_property("cmake_target_name", "libxshmfence::libxshmfence")
        self.cpp_info.set_property("pkg_config_name", "xshmfence")
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

    def _dependency_dirs(self, subdir):
        result = []
        for dependency in self.dependencies.host.values():
            path = os.path.join(dependency.package_folder, subdir)
            if os.path.isdir(path) and path not in result:
                result.append(path)
        return result

    def _resolve_ohos_tool(self, tool):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for compiler in ("c", "cpp"):
            compiler_command = compilers.get(compiler)
            if not compiler_command:
                continue
            compiler_path = str(compiler_command).split()[0].strip("\"'")
            candidate = os.path.join(os.path.dirname(compiler_path), tool)
            if os.path.exists(candidate):
                return candidate
        return shutil.which(tool) or tool

    def _resolve_shell(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("bash"),
            shutil.which("sh"),
            "/bin/sh",
            "/system/bin/sh",
        ):
            if not candidate:
                continue
            if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return "sh"

    def _patch_conan_env_scripts(self, shell):
        generators_folder = self.generators_folder
        if not generators_folder or not os.path.isdir(generators_folder):
            return

        bootstrap_paths = self._ohos_tool_paths()
        if not bootstrap_paths:
            return
        bootstrap = ":".join(bootstrap_paths)
        marker = "# libxshmfence OHOS PATH bootstrap"
        for entry in os.listdir(generators_folder):
            if not entry.endswith(".sh") or entry.startswith("deactivate_"):
                continue
            script_path = os.path.join(generators_folder, entry)
            with open(script_path, "r", encoding="utf-8") as handle:
                content = handle.read()

            if marker not in content:
                content = f'{marker}\nexport PATH="{bootstrap}:${{PATH}}"\n' + content
            if shell:
                content = re.sub(
                    r'^export SHELL="[^"]*"$',
                    f'export SHELL="{shell}"',
                    content,
                    flags=re.MULTILINE,
                )
                content = re.sub(
                    r'^export CONFIG_SHELL="[^"]*"$',
                    f'export CONFIG_SHELL="{shell}"',
                    content,
                    flags=re.MULTILINE,
                )
            content = self._patch_missing_compiler_exports(content)

            with open(script_path, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _patch_missing_compiler_exports(self, content):
        for variable, replacement in {
            "CC": self._fallback_compiler("c", "clang"),
            "CXX": self._fallback_compiler("cpp", "clang++"),
        }.items():
            if replacement:
                content = re.sub(
                    rf'^export {variable}="[^"]*"$',
                    f'export {variable}="{replacement}"',
                    content,
                    flags=re.MULTILINE,
                )
        return content

    def _fallback_compiler(self, compiler_key, fallback_name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        configured = compilers.get(compiler_key)
        if configured:
            configured_path = str(configured).split()[0].strip("\"'")
            if os.path.exists(configured_path) and os.access(configured_path, os.X_OK):
                return None
        fallback = shutil.which(fallback_name)
        if fallback and os.path.exists(fallback) and os.access(fallback, os.X_OK):
            return fallback
        return None

    def _add_runtime_library_paths(self, build_env):
        for dependency in self.dependencies.host.values():
            lib_dir = os.path.join(dependency.package_folder, "lib")
            if os.path.isdir(lib_dir):
                build_env.prepend_path("LD_LIBRARY_PATH", lib_dir)

    def _add_dependency_flags(self, toolchain):
        for dependency in self.dependencies.host.values():
            include_dir = os.path.join(dependency.package_folder, "include")
            lib_dir = os.path.join(dependency.package_folder, "lib")
            if os.path.isdir(include_dir):
                toolchain.extra_cflags.append(f"-I{include_dir}")
            if os.path.isdir(lib_dir):
                toolchain.extra_ldflags.append(f"-L{lib_dir}")

    def _prepend_ohos_tool_paths(self):
        tool_paths = self._ohos_tool_paths()
        existing = os.environ.get("PATH", "")
        for path in reversed(tool_paths):
            if os.path.isdir(path):
                if path not in existing.split(os.pathsep):
                    existing = path + (os.pathsep + existing if existing else "")
        os.environ["PATH"] = existing

    def _ohos_tool_paths(self):
        return [
            path
            for path in (
                "/data/service/hnp/bin",
                os.path.join(os.path.expanduser("~"), "usr", "local", "bin"),
                "/bin",
                "/usr/bin",
            )
            if os.path.isdir(path)
        ]

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
