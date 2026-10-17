#!/usr/bin/env python3
"""Conan recipe for libfwsi 20240423.

The upstream release is mirrored by Debian. The release archive contains the
bundled local libyal components and generated Autotools files, so this recipe
never runs synclibs.sh and never adds unregistered dependencies.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibfwsiConan(ConanFile):
    name = "libfwsi"
    version = "20240423"
    description = "Library to access the Windows Shell Item format"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/libyal/libfwsi"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("libyal", "autotools", "harmonyos")
    package_type = "library"
    languages = "C"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    _LOCAL_LIBS = (
        "libcdata",
        "libcerror",
        "libclocale",
        "libcnotify",
        "libcthreads",
        "libfdatetime",
        "libfguid",
        "libfole",
        "libfwps",
        "libuna",
    )

    _GENERATED_FILES = (
        "configure",
        "aclocal.m4",
        "config.guess",
        "config.sub",
        "Makefile.in",
    )

    _UNLISTED_LIBRARY_TESTS = ()

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        os_name = str(self.settings.os)
        if os_name not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libfwsi adaptation currently supports Linux and OHOS"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            filename="libfwsi_20240423.orig.tar.gz",
            strip_root=True,
            **self.conan_data["sources"],
        )

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                "--disable-python",
            ]
        )
        if str(self.settings.os) == "OHOS":
            toolchain.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-ohos",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )
        toolchain.generate()

    def _patch_ohos_test_runner(self):
        test_runner_path = os.path.join(
            self.source_folder, "tests", "test_runner.sh"
        )
        with open(test_runner_path, encoding="utf-8") as test_runner_file:
            test_runner = test_runner_file.read()

        needle = "TEST_EXECUTABLE=$( readlink_f \"${TEST_EXECUTABLE}\" );"
        replacement = (
            needle
            + "\n\n"
            + "\tlocal TEST_EXECUTABLE_BASENAME=`basename "
            + "${TEST_EXECUTABLE}`;"
            + "\n"
            + "\tlocal TEST_EXECUTABLE_DIRNAME=`dirname "
            + "${TEST_EXECUTABLE}`;"
            + "\n"
            + "\tlocal LIBTOOL_EXECUTABLE=\"${TEST_EXECUTABLE_DIRNAME}/.libs/"
            + "${TEST_EXECUTABLE_BASENAME}\";"
            + "\n"
            + "\tif test -x \"${LIBTOOL_EXECUTABLE}\";"
            + "\n"
            + "\tthen"
            + "\n"
            + "\t\tTEST_EXECUTABLE=\"${LIBTOOL_EXECUTABLE}\";"
            + "\n"
            + "\tfi;"
        )
        if test_runner.count(needle) != 2:
            raise ConanInvalidConfiguration(
                "unexpected libfwsi test_runner.sh layout; "
                "cannot apply OHOS libtool executable workaround"
            )
        test_runner = test_runner.replace(needle, replacement, 2)

        default_runner = (
            "\telse\n"
            "\t\tif ! test -x \"${TEST_EXECUTABLE}\";"
        )
        default_runner_replacement = (
            "\telse\n"
            "\t\tTEST_EXECUTABLE=$( find_binary_executable "
            "\"${TEST_EXECUTABLE}\" );\n"
            "\t\tif ! test -x \"${TEST_EXECUTABLE}\";"
        )
        if test_runner.count(default_runner) != 2:
            raise ConanInvalidConfiguration(
                "unexpected libfwsi test_runner.sh execution layout; "
                "cannot apply OHOS test dispatch workaround"
            )
        test_runner = test_runner.replace(
            default_runner, default_runner_replacement, 2
        )

        with open(test_runner_path, "w", encoding="utf-8") as test_runner_file:
            test_runner_file.write(test_runner)

    def _patch_ohos_config_sub(self):
        config_sub_path = os.path.join(self.source_folder, "config.sub")
        with open(config_sub_path, encoding="utf-8") as config_sub_file:
            config_sub = config_sub_file.read()

        os_needle = "| android* | bsd*"
        os_replacement = "| android* | ohos* | bsd*"
        os_new_needle = "\t| android* \\"
        os_new_replacement = "\t| android* \\\n\t| ohos* \\"
        if (
            os_replacement not in config_sub
            and os_new_replacement not in config_sub
        ):
            if os_needle in config_sub:
                config_sub = config_sub.replace(os_needle, os_replacement, 1)
            elif os_new_needle in config_sub:
                config_sub = config_sub.replace(
                    os_new_needle, os_new_replacement, 1
                )
            else:
                raise ConanInvalidConfiguration(
                    "unexpected config.sub OS validation list; cannot add OHOS"
                )

        kernel_needle = "linux-android* | linux-newlib*"
        kernel_replacement = (
            "linux-android* | linux-ohos* | linux-newlib*"
        )
        kernel_new_needle = "linux-android*- | linux-dietlibc*-"
        kernel_new_replacement = (
            "linux-android*- | linux-ohos*- | linux-dietlibc*-"
        )
        if (
            kernel_replacement not in config_sub
            and kernel_new_replacement not in config_sub
        ):
            if kernel_needle in config_sub:
                config_sub = config_sub.replace(
                    kernel_needle, kernel_replacement, 1
                )
            elif kernel_new_needle in config_sub:
                config_sub = config_sub.replace(
                    kernel_new_needle, kernel_new_replacement, 1
                )
            else:
                raise ConanInvalidConfiguration(
                    "unexpected config.sub kernel-OS validation list; cannot add OHOS"
                )

        with open(config_sub_path, "w", encoding="utf-8") as config_sub_file:
            config_sub_file.write(config_sub)

    def build(self):
        missing_dirs = [
            library for library in self._LOCAL_LIBS
            if not os.path.isdir(os.path.join(self.source_folder, library))
        ]
        missing_files = [
            filename for filename in self._GENERATED_FILES
            if not os.path.isfile(os.path.join(self.source_folder, filename))
        ]
        if missing_dirs or missing_files:
            details = []
            if missing_dirs:
                details.append(
                    "bundled libyal directories: " + ", ".join(missing_dirs)
                )
            if missing_files:
                details.append(
                    "generated Autotools files: " + ", ".join(missing_files)
                )
            raise ConanInvalidConfiguration(
                "libfwsi/20240423 source is not self-contained: "
                + "; ".join(details)
                + ". Do not run synclibs.sh here: adapt missing libyal "
                "dependencies in separate library worktrees first."
            )

        autotools = Autotools(self)
        old_umask = os.umask(0o022)
        old_ld_library_path = os.environ.get("LD_LIBRARY_PATH")
        old_home = os.environ.get("HOME")
        sandbox_home = os.path.join(self.build_folder, "upstream-test-home")
        os.makedirs(sandbox_home, exist_ok=True)
        os.environ["HOME"] = sandbox_home
        try:
            config_shell = os.environ.get(
                "CONFIG_SHELL", "/data/service/hnp/bin/bash"
            )
            if str(self.settings.os) == "OHOS":
                self._patch_ohos_config_sub()
                configure_path = os.path.join(self.source_folder, "configure")
                with open(configure_path, encoding="utf-8") as configure_file:
                    configure_text = configure_file.read()
                if "umask 077" in configure_text:
                    with open(
                        configure_path, "w", encoding="utf-8"
                    ) as configure_file:
                        configure_file.write(
                            configure_text.replace("umask 077", "umask 022")
                        )
                os.chmod(configure_path, 0o755)
                self.run(
                    f'"{config_shell}" "{configure_path}" '
                    f"{autotools._configure_args}",
                    cwd=self.source_folder,
                )
            else:
                autotools.configure()
            self.run("make -j4", cwd=self.source_folder)
            if str(self.settings.os) == "OHOS":
                self._patch_ohos_test_runner()
                library_path = os.path.join(
                    self.source_folder, "libfwsi", ".libs"
                )
                if old_ld_library_path:
                    os.environ["LD_LIBRARY_PATH"] = (
                        library_path + os.pathsep + old_ld_library_path
                    )
                else:
                    os.environ["LD_LIBRARY_PATH"] = library_path
                self.run(
                    f'make -j1 check LOG_COMPILER="{config_shell}"',
                    cwd=self.source_folder,
                )
                for test_name in self._UNLISTED_LIBRARY_TESTS:
                    executable = os.path.join(
                        self.source_folder,
                        "tests",
                        ".libs",
                        f"{self.name[3:]}_test_{test_name}",
                    )
                    self.run(
                        f'"{executable}"',
                        cwd=os.path.join(self.source_folder, "tests"),
                    )
                    self.output.info(
                        f"UNLISTED_UPSTREAM_TEST {test_name}: PASS"
                    )
            else:
                self.run("make -j1 check", cwd=self.source_folder)
        finally:
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home
            if old_ld_library_path is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = old_ld_library_path
            os.umask(old_umask)

    def package(self):
        self.run(
            f'make install DESTDIR="{self.package_folder}"',
            cwd=self.source_folder,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "COPYING.LESSER",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["fwsi"]
        self.cpp_info.set_property("cmake_file_name", "libfwsi")
        self.cpp_info.set_property("cmake_target_name", "libfwsi::libfwsi")
        self.cpp_info.set_property("pkg_config_name", "libfwsi")
