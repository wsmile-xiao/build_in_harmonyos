#!/usr/bin/env python3
"""Conan recipe for libevent 2.1.13."""

import glob
import json
import os
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    export_conandata_patches,
    get,
    load,
    unzip,
)


class LibeventConan(ConanFile):
    name = "libevent"
    version = "2.1.13"
    description = "Event notification library with fast non-blocking I/O"
    license = "BSD-3-Clause"
    homepage = "https://libevent.org/"
    url = "https://github.com/libevent/libevent"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
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
        if self.settings.os not in ("Linux", "OHOS", "Windows"):
            raise ConanInvalidConfiguration(
                f"libevent is validated only for Linux, OHOS, and Windows, not {self.settings.os}"
            )

    def build_requirements(self):
        self.test_requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        local_archive = os.environ.get("LIBEVENT_SOURCE_ARCHIVE")
        if local_archive:
            if not os.path.isfile(local_archive):
                raise ConanInvalidConfiguration(
                    f"LIBEVENT_SOURCE_ARCHIVE does not exist: {local_archive}"
                )
            check_sha256(self, local_archive, self.conan_data["sources"]["sha256"])
            unzip(self, local_archive, strip_root=True)
            return
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        zlib_include, zlib_library = self._zlib_test_layout()
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["EVENT__LIBRARY_TYPE"] = (
            "SHARED" if self.options.shared else "STATIC"
        )
        tc.variables["EVENT__DISABLE_OPENSSL"] = True
        tc.variables["EVENT__DISABLE_BENCHMARK"] = True
        tc.variables["EVENT__DISABLE_SAMPLES"] = True
        tc.variables["EVENT__DISABLE_TESTS"] = False
        tc.variables["EVENT__DISABLE_REGRESS"] = False
        tc.variables["EVENT__DISABLE_THREAD_SUPPORT"] = False
        tc.variables["ZLIB_ROOT"] = self.dependencies["zlib"].package_folder.replace(
            "\\", "/"
        )
        # libevent 2.1.13 still gates zlib tests on the legacy singular
        # variables even when CMakeDeps provides ZLIB::ZLIB and plural values.
        tc.cache_variables["ZLIB_INCLUDE_DIR"] = zlib_include.replace("\\", "/")
        tc.cache_variables["ZLIB_LIBRARY"] = zlib_library.replace("\\", "/")
        if not self.options.shared and self.settings.os != "Windows":
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)

        if self.settings.os == "OHOS":
            # Conan maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS. CMake has no
            # built-in platform module for it, so complete the shared-linker
            # contract used by libevent's in-tree tests.
            tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            tc.cache_variables["CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG"] = "-Wl,-rpath,"
            tc.cache_variables["CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP"] = ":"
            tc.cache_variables["CMAKE_SHARED_LIBRARY_RPATH_LINK_C_FLAG"] = (
                "-Wl,-rpath-link,"
            )
            tc.cache_variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        self._verify_zlib_enabled()
        cmake.build()

        if not can_run(self):
            self.output.warning(
                "The target cannot run on this build host; upstream tests must run on a native worker."
            )
            return

        if self.settings.os == "OHOS":
            self._sign_build_artifacts()
        self._run_upstream_tests()

    def package(self):
        CMake(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if self.settings.os == "OHOS" and self.options.shared:
            libraries = glob.glob(
                os.path.join(self.package_folder, "lib", "**", "*.so*"),
                recursive=True,
            )
            self._sign_paths(libraries, required=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Libevent")
        self.cpp_info.set_property("pkg_config_name", "libevent")
        runtime_bindirs = (
            ["bin", "lib"] if self.settings.os == "Windows" else ["bin"]
        )
        self.cpp_info.bindirs = runtime_bindirs

        core = self.cpp_info.components["core"]
        core.libs = ["event_core"]
        core.bindirs = runtime_bindirs
        core.set_property("cmake_target_name", "libevent::core")
        core.set_property("pkg_config_name", "libevent_core")
        if self.settings.os in ("Linux", "OHOS"):
            core.system_libs = ["pthread"]
        elif self.settings.os == "Windows":
            core.system_libs = ["ws2_32", "advapi32", "iphlpapi"]

        extra = self.cpp_info.components["extra"]
        extra.libs = ["event_extra"]
        extra.bindirs = runtime_bindirs
        extra.requires = ["core"]
        extra.set_property("cmake_target_name", "libevent::extra")
        extra.set_property("pkg_config_name", "libevent_extra")
        if self.settings.os == "Windows":
            extra.system_libs = ["shell32"]

        event = self.cpp_info.components["event"]
        event.libs = ["event"]
        event.bindirs = runtime_bindirs
        event.set_property("cmake_target_name", "libevent::event")
        event.set_property("pkg_config_name", "libevent")
        if self.settings.os in ("Linux", "OHOS"):
            event.system_libs = ["pthread"]
        elif self.settings.os == "Windows":
            event.system_libs = ["ws2_32", "shell32", "advapi32", "iphlpapi"]

        if self.settings.os != "Windows":
            pthreads = self.cpp_info.components["pthreads"]
            pthreads.libs = ["event_pthreads"]
            pthreads.bindirs = runtime_bindirs
            pthreads.requires = ["core"]
            pthreads.set_property("cmake_target_name", "libevent::pthreads")
            pthreads.set_property("pkg_config_name", "libevent_pthreads")

    def _run_upstream_tests(self):
        ctest = shutil.which("ctest") or "ctest"
        test_tmp = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(test_tmp, exist_ok=True)
        loader_environment = Environment()
        loader_environment.define("TMPDIR", test_tmp)
        loader_environment.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.build_folder, "lib")
        )
        with VirtualRunEnv(self).vars().apply(), loader_environment.vars(
            self
        ).apply():
            self.run(
                self._shell_join(
                    [
                        ctest,
                        "--output-on-failure",
                        "--no-tests=error",
                        "-E",
                        "^test-dumpevents__",
                    ]
                ),
                cwd=self.build_folder,
            )
            self._run_dumpevents_checks(ctest)

    def _zlib_test_layout(self):
        dependency = self.dependencies["zlib"]
        include_dirs = list(dependency.cpp_info.includedirs or ["include"])
        library_dirs = list(dependency.cpp_info.libdirs or ["lib"])
        library_names = list(dependency.cpp_info.libs or ["z"])

        def absolute(path):
            return path if os.path.isabs(path) else os.path.join(
                dependency.package_folder, path
            )

        include_dirs = [absolute(path) for path in include_dirs]
        zlib_include = next(
            (
                path
                for path in include_dirs
                if os.path.isfile(os.path.join(path, "zlib.h"))
            ),
            "",
        )
        suffixes = (".a", ".so", ".dylib", ".lib", ".dll.a")
        filenames = []
        for name in library_names:
            filenames.extend(
                [f"lib{name}{suffix}" for suffix in suffixes]
                + [f"{name}{suffix}" for suffix in suffixes]
            )
        zlib_library = next(
            (
                os.path.join(directory, filename)
                for directory in map(absolute, library_dirs)
                for filename in filenames
                if os.path.isfile(os.path.join(directory, filename))
            ),
            "",
        )
        if not zlib_include or not zlib_library:
            raise ConanInvalidConfiguration(
                "zlib test requirement must provide zlib.h and a linkable library"
            )
        return zlib_include, zlib_library

    def _verify_zlib_enabled(self):
        config = os.path.join(
            self.build_folder, "include", "event2", "event-config.h"
        )
        if not os.path.isfile(config) or "#define EVENT__HAVE_LIBZ 1" not in load(
            self, config
        ):
            raise ConanInvalidConfiguration(
                "libevent configured without zlib; bufferevent_zlib would be skipped"
            )

    def _run_dumpevents_checks(self, ctest):
        listing = subprocess.run(
            [ctest, "--show-only=json-v1"],
            cwd=self.build_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if listing.returncode:
            raise ConanException(
                f"ctest JSON listing failed ({listing.returncode}): {listing.stderr}"
            )
        tests = [
            test
            for test in json.loads(listing.stdout).get("tests", [])
            if str(test.get("name", "")).startswith("test-dumpevents__")
        ]
        if not tests:
            raise ConanException("No registered test-dumpevents checks were found")

        checker = os.path.join(self.source_folder, "test", "check-dumpevents.py")
        for test in tests:
            command = test.get("command") or []
            if not command:
                raise ConanException(f"Missing command for {test.get('name')}")
            environment = os.environ.copy()
            for prop in test.get("properties", []):
                if prop.get("name") != "ENVIRONMENT":
                    continue
                values = prop.get("value") or []
                if isinstance(values, str):
                    values = [values]
                for assignment in values:
                    key, separator, value = str(assignment).partition("=")
                    if separator:
                        environment[key] = value

            producer = subprocess.run(
                [command[0]],
                cwd=self.build_folder,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            consumer = subprocess.run(
                [sys.executable, checker],
                cwd=self.build_folder,
                env=environment,
                input=producer.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if producer.returncode or consumer.returncode:
                raise ConanException(
                    f"{test.get('name')} real pipeline failed: "
                    f"producer={producer.returncode}, checker={consumer.returncode}, "
                    f"producer_stderr={producer.stderr.decode(errors='replace')}, "
                    f"checker_stderr={consumer.stderr.decode(errors='replace')}"
                )
            self.output.info(f"{test.get('name')}: real stdout pipeline passed")

    def _sign_build_artifacts(self):
        candidates = glob.glob(
            os.path.join(self.build_folder, "bin", "*"), recursive=False
        )
        candidates.extend(
            glob.glob(
                os.path.join(self.build_folder, "lib", "**", "*.so*"),
                recursive=True,
            )
        )
        self._sign_paths(candidates, required=True)

    def _sign_paths(self, paths, required):
        paths = sorted(
            {
                path
                for path in paths
                if os.path.isfile(path) and not os.path.islink(path) and self._is_elf(path)
            }
        )
        if not paths:
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            message = "HarmonyOS execution requires llvm-objcopy and binary-sign-tool"
            if required:
                raise ConanInvalidConfiguration(message)
            self.output.warning(message)
            return
        for path in paths:
            self._sign_elf_atomically(path, objcopy, signer)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(
                self._shell_join(
                    [objcopy, "--remove-section", ".codesign", temporary]
                )
            )
            self.run(
                self._shell_join(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        temporary,
                        "-outFile",
                        temporary,
                        "-selfSign",
                        "1",
                    ]
                )
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c", "") or compilers.get("cpp", "")
        compiler_dir = os.path.dirname(compiler)
        candidates = (
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        )
        return next((path for path in candidates if os.path.isfile(path)), "")

    def _shell_join(self, arguments):
        arguments = [str(argument) for argument in arguments]
        if self.settings.os == "Windows":
            return subprocess.list2cmdline(arguments)
        return shlex.join(arguments)
