#!/usr/bin/env python3
"""Conan recipe for libfcrypto 0-20240414.

libfcrypto is libyal's support library for the cryptographic primitives used
across the libyal toolchain (Blowfish, DES3, RC4 and Serpent contexts plus
error/support helpers).

The 20240414 release archive is self-contained: it bundles the local libcerror
component the library links against and ships the generated Autotools files
(configure / aclocal.m4 / config.guess / config.sub / Makefile.in).  The
recipe therefore never runs ``synclibs.sh`` and never pulls unregistered
vendored dependencies into this PR.

The pinned source is the Debian orig tarball, byte-identical to the official
upstream release asset (libfcrypto-alpha-20240414.tar.gz for tag 20240414);
the platform task version "0-20240414" follows the libyal soname-0
date-version convention (Debian carries the same release as
libfcrypto_0~20240414).  The source URL + SHA-256 live in ``conandata.yml``
and the release identity (tag + commit) is recorded in ``manifest.yaml``.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibfcryptoConan(ConanFile):
    name = "libfcrypto"
    version = "0-20240414"
    description = (
        "Library for cryptographic primitives (Blowfish, DES3, RC4, Serpent) "
        "from the libyal project"
    )
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/libyal/libfcrypto"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("crypto", "blowfish", "des3", "rc4", "serpent", "libyal")
    package_type = "library"
    languages = "C"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # Local libyal component bundled by the release archive (configure.ac).
    _LOCAL_LIBS = ("libcerror",)
    # Generated Autotools files that only the release archive ships.
    _GENERATED_FILES = (
        "configure",
        "aclocal.m4",
        "config.guess",
        "config.sub",
        "Makefile.in",
    )

    def export_sources(self):
        export_conandata_patches(self)

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
                "libfcrypto adaptation currently supports Linux and OHOS"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # An explicit archive filename is required: Conan misclassifies the
        # orig-tarball URL when it has to infer the archive format and would
        # otherwise hand a tarball to the ZIP reader (BadZipFile).
        get(
            self,
            filename="libfcrypto_0~20240414.orig.tar.gz",
            strip_root=True,
            **self.conan_data["sources"],
        )

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        # AutotoolsToolchain already emits --enable-shared/--disable-static or
        # --disable-shared/--enable-static from the "shared" option.
        toolchain.configure_args.extend(
            [
                "--disable-python",
            ]
        )
        if str(self.settings.os) == "OHOS":
            # The bundled config.guess/config.sub (2023-06-23) predate both
            # the HarmonyOS uname and the "ohos" OS, so pass the gnu triple
            # they accept; the patch in patches/ reports the same triple so a
            # bare ./configure (clean-build gate) also works on this host.
            toolchain.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-gnu",
                    "--host=aarch64-unknown-linux-gnu",
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
                "unexpected libfcrypto test_runner.sh layout; "
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
                "unexpected libfcrypto test_runner.sh execution layout; "
                "cannot apply OHOS test dispatch workaround"
            )
        test_runner = test_runner.replace(
            default_runner, default_runner_replacement, 2
        )

        with open(test_runner_path, "w", encoding="utf-8") as test_runner_file:
            test_runner_file.write(test_runner)

    def build(self):
        apply_conandata_patches(self)

        # Release-archive closure check: refuse to build a partial source tree
        # (e.g. a git checkout) instead of silently bootstrapping it.
        missing_dirs = [
            name for name in self._LOCAL_LIBS
            if not os.path.isdir(os.path.join(self.source_folder, name))
        ]
        missing_files = [
            name for name in self._GENERATED_FILES
            if not os.path.isfile(os.path.join(self.source_folder, name))
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
                "libfcrypto/0-20240414 source is not self-contained: "
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
                # configure is POSIX sh, so run it with /bin/sh and pin
                # CONFIG_SHELL to it as a COMMAND-PREFIX assignment: Conan
                # sources the aggregated conanbuild.sh before the command and
                # that file re-exports the profile buildenv CONFIG_SHELL
                # (the hnp bash), so a process-environment pin would be
                # overridden.  autoconf/libtool honour $CONFIG_SHELL for
                # their early shell checks and subshells, and hnp bash 5.3
                # fails its getcwd probe on some HMDFS directories
                # ("working directory cannot be determined"), while the
                # toybox shell resolves the same directories reliably.  The
                # bash interpreter is still used for the test runner via
                # LOG_COMPILER below.
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
                    f'CONFIG_SHELL=/bin/sh "/bin/sh" "{configure_path}" '
                    f"{autotools._configure_args}",
                    cwd=self.source_folder,
                )
            else:
                autotools.configure()
            self.run("make -j2", cwd=self.source_folder)
            # Upstream tests must never run against the operator's real HOME:
            # point HOME at a throw-away directory inside the build folder.
            old_home = os.environ.get("HOME")
            sandbox_home = os.path.join(self.build_folder, "upstream-test-home")
            os.makedirs(sandbox_home, exist_ok=True)
            os.environ["HOME"] = sandbox_home
            try:
                if str(self.settings.os) == "OHOS":
                    self._patch_ohos_test_runner()
                    library_path = os.path.join(
                        self.source_folder, "libfcrypto", ".libs"
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
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home
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
        self.cpp_info.libs = ["fcrypto"]
        self.cpp_info.set_property("cmake_file_name", "libfcrypto")
        self.cpp_info.set_property("cmake_target_name", "libfcrypto::libfcrypto")
        self.cpp_info.set_property("pkg_config_name", "libfcrypto")
