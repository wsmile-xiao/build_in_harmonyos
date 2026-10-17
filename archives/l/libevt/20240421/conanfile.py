#!/usr/bin/env python3
"""Conan recipe for libevt 20240421 (Autotools, self-contained libyal release).

The upstream GitHub release artifact for tag 20240421 is no longer
published (libyal prunes old release assets), so this recipe uses the
Debian archive copy of the orig tarball.  The tarball is the upstream
self-contained release package: it bundles 20 local libyal support
libraries plus generated Autotools files, so no external Conan
dependencies are required.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibevtConan(ConanFile):
    name = "libevt"
    version = "20240421"
    description = "Library to access the Windows Event Log (EVT) format"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/libyal/libevt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    _SOURCE_URL = (
        "https://deb.debian.org/debian/pool/main/libe/libevt/"
        "libevt_20240421.orig.tar.gz"
    )
    _SOURCE_SHA256 = (
        "984837219de4155b2fbe5817dea6ce737e39f36457e89511371b3cad0ab18606"
    )
    _LOCAL_LIBS = (
        "libbfio",
        "libcdata",
        "libcdirectory",
        "libcerror",
        "libcfile",
        "libclocale",
        "libcnotify",
        "libcpath",
        "libcsplit",
        "libcthreads",
        "libevt",
        "libexe",
        "libfcache",
        "libfdata",
        "libfdatetime",
        "libfguid",
        "libfvalue",
        "libfwnt",
        "libfwevt",
        "libregf",
        "libuna",
        "libwrc",
    )

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
                "libevt adaptation currently supports Linux and OHOS"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            url=self._SOURCE_URL,
            sha256=self._SOURCE_SHA256,
            filename="libevt_20240421.orig.tar.gz",
            strip_root=True,
        )

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                "--disable-python",
                "--enable-static-executables=no",
            ]
        )
        if self.options.shared:
            toolchain.configure_args.append("--enable-shared")
            toolchain.configure_args.append("--disable-static")
        else:
            toolchain.configure_args.append("--disable-shared")
            toolchain.configure_args.append("--enable-static")
        if str(self.settings.os) == "OHOS":
            toolchain.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-gnu",
                    "--host=aarch64-unknown-linux-gnu",
                ]
            )
        toolchain.generate()

    def _patch_ohos_test_runner(self):
        # On OHOS the libtool wrapper scripts and HMDFS prevent direct
        # execution of uninstalled test binaries.  Teach test_runner.sh
        # to resolve the real ELF under .libs/ and dispatch through it.
        test_runner_path = os.path.join(
            self.source_folder, "tests", "test_runner.sh"
        )
        with open(test_runner_path, encoding="utf-8") as test_runner_file:
            test_runner = test_runner_file.read()

        needle = 'TEST_EXECUTABLE=$( readlink_f "${TEST_EXECUTABLE}" );'
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
        count = test_runner.count(needle)
        if count < 1:
            raise ConanInvalidConfiguration(
                "unexpected libevt test_runner.sh layout; "
                "cannot apply OHOS libtool executable workaround"
            )
        test_runner = test_runner.replace(needle, replacement, count)

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
        count = test_runner.count(default_runner)
        if count < 1:
            raise ConanInvalidConfiguration(
                "unexpected libevt test_runner.sh execution layout; "
                "cannot apply OHOS test dispatch workaround"
            )
        test_runner = test_runner.replace(
            default_runner, default_runner_replacement, count
        )

        with open(test_runner_path, "w", encoding="utf-8") as test_runner_file:
            test_runner_file.write(test_runner)

    def build(self):
        missing_dirs = [
            name for name in self._LOCAL_LIBS
            if not os.path.isdir(os.path.join(self.source_folder, name))
        ]
        generated_files = (
            "configure",
            "aclocal.m4",
            "config.guess",
            "config.sub",
            "Makefile.in",
        )
        missing_files = [
            name for name in generated_files
            if not os.path.isfile(os.path.join(self.source_folder, name))
        ]
        if missing_dirs or missing_files:
            details = []
            if missing_dirs:
                details.append("bundled libyal directories: " + ", ".join(missing_dirs))
            if missing_files:
                details.append("generated Autotools files: " + ", ".join(missing_files))
            raise ConanInvalidConfiguration(
                "libevt/20240421 source is not self-contained: "
                + "; ".join(details)
                + ". Do not run synclibs.sh here: adapt missing libyal "
                "dependencies in separate library worktrees first."
            )

        autotools = Autotools(self)
        old_umask = os.umask(0o022)
        old_ld_library_path = os.environ.get("LD_LIBRARY_PATH")
        try:
            config_shell = os.environ.get(
                "CONFIG_SHELL", "/data/service/hnp/bin/bash"
            )
            if str(self.settings.os) == "OHOS":
                # HMDFS rejects the 0700 temporary directory created by
                # Autoconf, and the device also blocks direct script exec.
                configure_path = os.path.join(self.source_folder, "configure")
                with open(configure_path, encoding="utf-8") as configure_file:
                    configure_text = configure_file.read()
                if "umask 077" in configure_text:
                    with open(configure_path, "w", encoding="utf-8") as configure_file:
                        configure_file.write(configure_text.replace("umask 077", "umask 022"))
                os.chmod(configure_path, 0o755)
                self.run(
                    f'"{config_shell}" "{configure_path}" '
                    f"{autotools._configure_args}",
                    cwd=self.source_folder,
                )
            else:
                autotools.configure()
            self.run("make -j1", cwd=self.source_folder)
            if str(self.settings.os) == "OHOS":
                self._patch_ohos_test_runner()
                library_path = os.path.join(
                    self.source_folder, "libevt", ".libs"
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
            else:
                self.run("make -j1 check", cwd=self.source_folder)
        finally:
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
            "COPYING.LESSER",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["evt"]
        self.cpp_info.bindirs = ["bin"]
