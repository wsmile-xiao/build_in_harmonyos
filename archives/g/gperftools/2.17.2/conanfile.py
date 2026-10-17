#!/usr/bin/env python3
"""Conan recipe for gperftools 2.17.2 on Linux/OHOS."""

import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GperftoolsConan(ConanFile):
    name = "gperftools"
    version = "2.17.2"
    description = "High-performance C++ memory allocator and performance analysis libraries"
    license = "BSD-3-Clause"
    homepage = "https://github.com/gperftools/gperftools"
    url = "https://github.com/gperftools/gperftools"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_cpu_profiler": [True, False],
        "build_heap_profiler": [True, False],
        "build_debugalloc": [True, False],
        "enable_libunwind": [True, False],
        "enable_frame_pointers": [True, False],
        "enable_stacktrace_via_backtrace": [True, False],
        "emergency_malloc": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_cpu_profiler": False,
        "build_heap_profiler": False,
        "build_debugalloc": False,
        "enable_libunwind": False,
        "enable_frame_pointers": False,
        "enable_stacktrace_via_backtrace": False,
        "emergency_malloc": False,
    }

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    @property
    def _build_minimal(self):
        return not (
            self.options.get_safe("build_cpu_profiler", False)
            or self.options.get_safe("build_heap_profiler", False)
        )

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self._build_minimal:
            self.options.rm_safe("enable_libunwind")
            self.options.rm_safe("enable_frame_pointers")
            self.options.rm_safe("enable_stacktrace_via_backtrace")
            self.options.rm_safe("emergency_malloc")

    def validate(self):
        check_min_cppstd(self, 17)
        os_name = str(self.settings.os)
        if os_name not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gperftools 2.17.2 is supported on Linux/OHOS only, not {os_name}"
            )
        if os_name == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "gperftools 2.17.2 OHOS adaptation targets aarch64/armv8"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.get_safe("enable_libunwind", False):
            self.requires("libunwind/1.6.2")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()

        toolchain = AutotoolsToolchain(self)
        yes_no = lambda value: "yes" if value else "no"
        toolchain.configure_args.extend(
            [
                f"--enable-shared={yes_no(bool(self.options.shared))}",
                f"--enable-static={yes_no(not bool(self.options.shared))}",
                f"--enable-cpu-profiler={yes_no(bool(self.options.get_safe('build_cpu_profiler', False)))}",
                f"--enable-heap-profiler={yes_no(bool(self.options.get_safe('build_heap_profiler', False)))}",
                f"--enable-debugalloc={yes_no(bool(self.options.get_safe('build_debugalloc', False)))}",
                f"--enable-minimal={yes_no(self._build_minimal)}",
            ]
        )
        if str(self.settings.os) == "OHOS":
            # HarmonyOS exposes sbrk at link time, but the device runtime does
            # not provide the process-break semantics expected by tcmalloc.
            # Force Autoconf to use the mmap allocator path instead.
            toolchain.configure_args.append("ac_cv_func_sbrk=no")
            # The OHOS runtime cannot safely initialize gperftools' initial
            # exec TLS fast path during process startup.  Use its portable
            # pthread-key path; the device probe shows this preserves the
            # allocator's libc symbol overrides and avoids the startup crash.
            toolchain.extra_cxxflags.append("-DTCMALLOC_FORCE_BAD_TLS")
        if self._build_minimal:
            toolchain.configure_args.extend(
                [
                    "--enable-libunwind=no",
                    "--enable-frame-pointers=no",
                    "--enable-stacktrace-via-backtrace=no",
                    "--enable-emergency-malloc=no",
                ]
            )
        else:
            toolchain.configure_args.extend(
                [
                    f"--enable-libunwind={yes_no(bool(self.options.get_safe('enable_libunwind', False)))}",
                    f"--enable-frame-pointers={yes_no(bool(self.options.get_safe('enable_frame_pointers', False)))}",
                    f"--enable-stacktrace-via-backtrace={yes_no(bool(self.options.get_safe('enable_stacktrace_via_backtrace', False)))}",
                    f"--enable-emergency-malloc={yes_no(bool(self.options.get_safe('emergency_malloc', False)))}",
                ]
            )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)

        # HMDFS may not preserve executable bits when extracting the release
        # archive.  Restore the bits for the generated autotools helpers.
        for script_name in (
            "configure",
            "config.guess",
            "config.sub",
            "install-sh",
            "missing",
            "test-driver",
        ):
            script_path = os.path.join(self.source_folder, script_name)
            if os.path.isfile(script_path):
                os.chmod(script_path, os.stat(script_path).st_mode | stat.S_IXUSR)

        if str(self.settings.os) == "OHOS":
            # HMDFS can make getcwd(2) fail after Conan creates the build
            # tree.  Autoconf's configure and the Conan bash wrapper both
            # accept a valid logical PWD, which avoids the resulting
            # "working directory cannot be determined" failure.
            os.environ["PWD"] = self.build_folder

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1"])

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)

    def _add_component(self, library):
        component = self.cpp_info.components[library]
        component.libs = [library]
        component.set_property("cmake_target_name", f"gperftools::{library}")
        component.set_property("pkg_config_name", f"lib{library}")

        os_name = str(self.settings.os)
        if os_name in ("Linux", "OHOS"):
            component.cflags.append("-pthread")
            component.cxxflags.append("-pthread")
            component.exelinkflags.append("-pthread")
        if os_name == "Linux":
            component.system_libs.extend(["pthread", "m"])
        if self.options.get_safe("enable_libunwind", False):
            component.requires.append("libunwind::libunwind")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gperftools")
        self.cpp_info.set_property("cmake_target_name", "gperftools::gperftools")

        self._add_component("tcmalloc_minimal")
        if self.options.get_safe("build_debugalloc", False):
            self._add_component("tcmalloc_minimal_debug")
        if self.options.get_safe("build_heap_profiler", False):
            self._add_component("tcmalloc")
            if self.options.get_safe("build_debugalloc", False):
                self._add_component("tcmalloc_debug")
        if self.options.get_safe("build_cpu_profiler", False):
            self._add_component("profiler")
            if "tcmalloc" in self.cpp_info.components:
                self._add_component("tcmalloc_and_profiler")

        default_component = self.cpp_info.components["gperftools"]
        for library in (
            "tcmalloc_and_profiler",
            "tcmalloc",
            "tcmalloc_debug",
            "tcmalloc_minimal_debug",
            "tcmalloc_minimal",
        ):
            if library in self.cpp_info.components:
                default_component.requires = [library]
                if library != "tcmalloc_and_profiler" and "profiler" in self.cpp_info.components:
                    default_component.requires.append("profiler")
                break
