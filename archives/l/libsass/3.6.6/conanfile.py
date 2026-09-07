#!/usr/bin/env python3
"""Conan recipe for the LibSass C/C++ library."""

import glob
import os
import shlex
import shutil
import subprocess
import tarfile
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LibsassConan(ConanFile):
    name = "libsass"
    version = "3.6.6"
    description = "C/C++ implementation of the Sass stylesheet language"
    license = "MIT"
    homepage = "https://sass-lang.com/libsass/"
    url = "https://github.com/sass/libsass"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS", "Windows"):
            raise ConanInvalidConfiguration(
                f"libsass is validated only for Linux, OHOS, and Windows, not {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        source_data = self.conan_data["sources"][str(self.version)]
        local_archive = os.environ.get("LIBSASS_SOURCE_ARCHIVE")
        if local_archive:
            if not os.path.isfile(local_archive):
                raise ConanInvalidConfiguration(
                    f"LIBSASS_SOURCE_ARCHIVE does not exist: {local_archive}"
                )
            check_sha256(self, local_archive, source_data["sha256"])
            with tempfile.TemporaryDirectory() as temp_dir:
                with tarfile.open(local_archive, "r:gz") as archive:
                    root = os.path.realpath(temp_dir)
                    for member in archive.getmembers():
                        target = os.path.realpath(os.path.join(temp_dir, member.name))
                        if target != root and not target.startswith(root + os.sep):
                            raise ConanInvalidConfiguration(
                                f"unsafe path in LIBSASS_SOURCE_ARCHIVE: {member.name}"
                            )
                    archive.extractall(temp_dir)
                source_root = os.path.join(temp_dir, f"libsass-{self.version}")
                if not os.path.isdir(source_root):
                    raise ConanInvalidConfiguration(
                        "LIBSASS_SOURCE_ARCHIVE does not contain the expected source root"
                    )
                shutil.copytree(source_root, self.source_folder, dirs_exist_ok=True)
        else:
            get(self, **source_data, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        build_env = VirtualBuildEnv(self)
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        for executable in executables.values():
            if executable:
                build_env.environment().append_path("PATH", os.path.dirname(str(executable)))
        build_env.generate()

    def build(self):
        self._run_make("all")
        self._run_upstream_tests()

    def package(self):
        lib_dir = os.path.join(self.source_folder, "lib")
        for pattern in ("libsass.a", "libsass.so", "libsass.dylib", "libsass.dll", "libsass.dll.a"):
            copy(self, pattern, src=lib_dir, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=True,
        )
        for license_file in ("LICENSE", "COPYING"):
            copy(
                self,
                license_file,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.libs = ["sass"]
        self.cpp_info.set_property("cmake_file_name", "libsass")
        self.cpp_info.set_property("cmake_target_name", "libsass::libsass")
        self.cpp_info.set_property("pkg_config_name", "libsass")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl"]

    def _run_make(self, target):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = self._make_tool(executables.get("c"), "cc")
        cxx = self._make_tool(executables.get("cpp"), "c++")
        ar = self._make_tool(
            executables.get("ar") or self._llvm_tool("llvm-ar", cxx), "ar"
        )

        cflags = self._conf_list("tools.build:cflags")
        cxxflags = self._conf_list("tools.build:cxxflags")
        ldflags = self._conf_list("tools.build:sharedlinkflags")
        sysroot = self._sysroot(executables)
        if sysroot:
            sysroot_value = self._make_path(sysroot)
            sysroot_flag = f"--sysroot={sysroot_value}"
            cflags.append(sysroot_flag)
            cxxflags.append(sysroot_flag)
            ldflags.append(sysroot_flag)

        for include_dir in self._sysroot_include_dirs(executables, sysroot):
            include_flag = f"-isystem {self._make_path(include_dir)}"
            cflags.append(include_flag)
            cxxflags.append(include_flag)

        include_flag = f"-I {os.path.join(self.source_folder, 'include')}"
        cflags = ["-Wall", "-O2", include_flag] + cflags
        cxxflags = ["-Wall", "-O2", "-std=c++11", include_flag] + cxxflags
        build_mode = "shared" if bool(self.options.shared) else "static"
        command = [
            "make",
            "-j1",
            target,
            f"BUILD={build_mode}",
            f"CC={cc}",
            f"CXX={cxx}",
            f"AR={ar}",
            "PREFIX=/",
            f"LIBSASS_VERSION={self.version}",
            f"CFLAGS={' '.join(cflags)}",
            f"CXXFLAGS={' '.join(cxxflags)}",
        ]
        if ldflags:
            command.append(f"LDFLAGS={' '.join(ldflags)}")
        self.run(self._shell_join(command), cwd=self.source_folder, env="conanbuild")

    def _run_upstream_tests(self):
        if not can_run(self):
            self.output.warning("Cross-built libsass cannot run the upstream test binaries on this host.")
            return

        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = self._make_tool(executables.get("cpp"), "c++")
        test_dir = os.path.join(self.source_folder, "test")
        flags = [
            "-std=c++11",
            "-O1",
            "-g",
            "-fno-omit-frame-pointer",
            "-I",
            os.path.join(self.source_folder, "include"),
        ] + self._conf_list("tools.build:cxxflags")
        sysroot = self._sysroot(executables)
        if sysroot:
            flags.append(f"--sysroot={self._make_path(sysroot)}")
        for include_dir in self._sysroot_include_dirs(executables, sysroot):
            flags.append(f"-isystem {self._make_path(include_dir)}")

        build_tests = [
            "make",
            "-C",
            test_dir,
            "-j1",
            f"CXX={cxx}",
            f"CXXFLAGS={' '.join(flags)}",
            "build/test_shared_ptr",
            "build/test_util_string",
        ]
        self.run(self._shell_join(build_tests), cwd=self.source_folder, env="conanbuild")
        for name in ("test_shared_ptr", "test_util_string"):
            executable = os.path.join(test_dir, "build", name)
            if os.name == "nt":
                executable += ".exe"
            if not os.path.isfile(executable):
                raise ConanException(f"upstream test binary was not created: {executable}")
            self.run(self._shell_join([executable]), cwd=test_dir, env="conanbuild")

    def _llvm_tool(self, name, compiler):
        compiler_dir = os.path.dirname(str(compiler))
        candidates = (
            os.path.join(compiler_dir, name),
            os.path.join(compiler_dir, "..", "bin", name),
            shutil.which(name) or "",
        )
        return next((path for path in candidates if os.path.isfile(path)), "")

    @staticmethod
    def _make_tool(configured, fallback):
        path = configured or shutil.which(fallback) or fallback
        if os.name != "nt" or " " not in str(path):
            return str(path)
        basename = os.path.basename(str(path))
        return basename

    def _conf_list(self, name):
        values = self.conf.get(name, default=[]) or []
        if isinstance(values, str):
            return [values]
        return [str(value) for value in values]

    def _sysroot(self, executables):
        sysroot = self.conf.get("tools.build:sysroot", default=None)
        if str(self.settings.os) != "OHOS":
            return sysroot

        # Some OHOS workers expose a generic /sysroot alongside a compiler
        # whose SDK lives under a versioned ohos-sdk.org directory.  The
        # generic path can exist without libc headers, so only accept it when
        # it contains the headers required by libc++.
        if sysroot:
            configured = os.path.normpath(str(sysroot)).replace("\\", "/")
            if os.path.isfile(os.path.join(configured, "usr", "include", "features.h")):
                return configured

        compiler = executables.get("cpp") or executables.get("c")
        if not compiler:
            return sysroot
        compiler_dir = os.path.dirname(str(compiler))
        candidates = [os.path.join(compiler_dir, "..", "..", "sysroot")]
        sdk_parent = os.path.normpath(os.path.join(compiler_dir, ".."))
        for pattern in (
            os.path.join(sdk_parent, "ohos-sdk.org", "*", "ohos", "native", "sysroot"),
            os.path.join(sdk_parent, "ohos-sdk", "*", "ohos", "native", "sysroot"),
        ):
            candidates.extend(sorted(glob.glob(pattern)))

        for candidate in candidates:
            candidate = os.path.normpath(candidate).replace("\\", "/")
            if os.path.isfile(os.path.join(candidate, "usr", "include", "features.h")):
                return candidate
        return sysroot or os.path.normpath(candidates[0]).replace("\\", "/")

    def _sysroot_include_dirs(self, executables, sysroot):
        # With --sysroot, Clang already adds the target C include directories.
        # A leading -isystem usr/include makes libc++ cstddef include the
        # musl stddef.h directly, which lacks the global nullptr_t typedef.
        return []

    @staticmethod
    def _make_path(path):
        return str(path).replace("\\", "/").replace(" ", "\\ ")

    @staticmethod
    def _shell_join(arguments):
        arguments = [str(argument) for argument in arguments]
        if os.name == "nt":
            return subprocess.list2cmdline(arguments)
        return shlex.join(arguments)
