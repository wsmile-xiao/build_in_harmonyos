#!/usr/bin/env python3
"""Conan recipe for barada-pam 0.5.3.

The upstream project installs the ``barada-add`` provisioning command and a
PAM module. It is therefore packaged as an application rather than as a
normal linkable C++ library; consumers load ``pam_barada.so`` through PAM.
"""

import os
import platform
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BaradaPamConan(ConanFile):
    name = "barada-pam"
    version = "0.5.3"
    description = (
        "PAM module and command-line provisioning tool for HOTP authentication"
    )
    license = "GPL-3.0-only"
    homepage = "https://barada.sourceforge.net/"
    url = "https://salsa.debian.org/debian/barada-pam"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The upstream configure checks these libraries directly. linux-pam
        # supplies the PAM headers/module ABI; Boost supplies filesystem and
        # lexical_cast; OpenSSL supplies HMAC and random-byte APIs.
        self.requires("boost/1.90.0.4")
        self.requires("linux-pam/1.7.2")
        self.requires("openssl/3.5.6")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "barada-pam requires a Linux/OHOS PAM runtime"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps supplies dependency include/library flags to the
        # configure probes and link commands. AutotoolsToolchain supplies the
        # compiler, prefix and platform-specific configure arguments.
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=/")
        if str(self.settings.os) == "OHOS":
            # The OHOS clang target cannot run on the x86_64 WSL build host.
            # Tell Autoconf this is a cross build so it does not execute the
            # generated aarch64 probe binary during configure.
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
            # WSL has qemu-aarch64-static but no OHOS musl dynamic loader.
            # libtool consumes -all-static for test/CLI executables; plain
            # -static is dropped by the old libtool shipped in this tarball.
            tc.extra_ldflags.append("-all-static")
        tc.generate()
        if str(self.settings.os) == "OHOS":
            # The shared OHOS profile points Autotools at device Bash, but
            # that Bash cannot reliably resolve HMDFS Conan build folders.
            # Override only this recipe's generated build environment; do
            # not modify the shared profile.
            build_env = VirtualBuildEnv(self)
            environment = build_env.environment()
            environment.define("CONFIG_SHELL", "/bin/sh")
            environment.define("SHELL", "/bin/sh")
            build_env.generate()
        # HexTest is an upstream executable and must be run with the Conan
        # dependency runtime paths before package() creates the final layout.
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        self._freeze_autotools_inputs()
        autotools.make(args=self._autotools_make_args() + ["-j1"])

        if str(self.settings.os) == "OHOS":
            # The static HexTest/WSL CLI links do not use Util::hexDump(),
            # whose PAM logger is unavailable in linux-pam's static package.
            # Compile functions separately so --gc-sections can discard that
            # unused path without introducing an unresolved symbol.
            util_obj = os.path.join(self.build_folder, "src", "Util.o")
            if os.path.exists(util_obj):
                os.unlink(util_obj)
            autotools.make(
                target="-C src Util.o",
                args=self._autotools_make_args() + [
                    "CXXFLAGS='-stdlib=libc++ -std=c++17 -O3 "
                    "-ffunction-sections -fdata-sections'",
                ],
            )

            if self._is_wsl_host():
                # WSL's qemu binfmt has no OHOS dynamic loader. Keep the
                # production CLI normally linked on OHOS workers, but make
                # this local preflight artifact executable under qemu. The
                # CLI never calls Util::hexDump(), so the unresolved PAM
                # logger is not part of its exercised control flow.
                barada_add = os.path.join(
                    self.build_folder, "src", "barada-add"
                )
                if os.path.exists(barada_add):
                    os.unlink(barada_add)
                autotools.make(
                    target="-C src barada-add",
                    args=self._autotools_make_args() + [
                        "LIBS=",
                        "barada_add_LDADD='-static -Wl,--gc-sections "
                        "-lcrypto -lboost_filesystem -lpthread -ldl'",
                    ],
                )

            # linux-pam publishes shared libraries only, so production
            # barada-add and pam_barada.so stay normally linked. HexTest
            # does not call its pam_syslog path; relink this upstream test
            # without PAM libraries so WSL qemu can execute it without the
            # OHOS dynamic loader. The consumer test below still exercises
            # the real installed PAM module through dlopen/dlsym.
            hex_test = os.path.join(self.build_folder, "src", "HexTest")
            if os.path.exists(hex_test):
                os.unlink(hex_test)
            autotools.make(
                target="-C src HexTest",
                args=self._autotools_make_args() + [
                    "LIBS=",
                    "HexTest_LDADD='-static -Wl,--gc-sections -lcrypto -lpthread -ldl'",
                ],
            )

        # The source tree declares HexTest as noinst_PROGRAMS but does not add
        # it to TESTS, so ``make check`` only builds it. Keep the official
        # check target and explicitly execute the upstream test binary.
        autotools.make(
            target="check",
            args=self._autotools_make_args() + ["-j1"],
        )
        self.run(
            '"{}"'.format(os.path.join(self.build_folder, "src", "HexTest")),
            env="conanrun",
        )

    @staticmethod
    def _is_wsl_host():
        return (
            platform.system() == "Linux"
            and "microsoft-standard" in platform.release().lower()
        )

    def _autotools_make_args(self):
        if str(self.settings.os) == "OHOS":
            # The release tarball already contains the generated Autotools
            # files.  HMDFS timestamps can make make believe they are stale;
            # do not invoke unavailable aclocal/automake/autoconf on device.
            return ["ACLOCAL=true", "AUTOMAKE=true", "AUTOCONF=true"]
        return []

    def _freeze_autotools_inputs(self):
        """Keep a release tarball from regenerating Autotools files in make.

        The patch updates configure.ac and the shipped configure script. The
        old Automake rules compare those files by mtime and otherwise invoke
        aclocal/automake or re-run configure, which are not part of the OHOS
        runtime image. The configure step has already consumed the patched
        inputs, so make must use the generated files as shipped.
        """
        config_status = os.path.join(self.build_folder, "config.status")
        if os.path.isfile(config_status):
            # HMDFS may truncate nanosecond mtimes.  A one-nanosecond
            # rollback can therefore leave configure newer than config.status
            # and make invokes config.status --recheck, regenerating the
            # unpatched Autotools script.  Leave a real timestamp margin.
            stamp = os.stat(config_status).st_mtime_ns - 2_000_000_000
            configure = os.path.join(self.source_folder, "configure")
            if stamp > 0 and os.path.isfile(configure):
                os.utime(configure, ns=(stamp, stamp))

        for root, _, filenames in os.walk(self.source_folder):
            if "Makefile.in" not in filenames:
                continue
            makefile_in = os.path.join(root, "Makefile.in")
            dependencies = [os.path.join(root, "Makefile.am")]
            if root == self.source_folder:
                dependencies.extend(
                    os.path.join(self.source_folder, name)
                    for name in ("configure.ac", "aclocal.m4")
                )
            existing = [
                os.stat(path).st_mtime_ns
                for path in dependencies
                if os.path.isfile(path)
            ]
            if existing:
                # HMDFS can truncate mtimes to coarse granularity.  Keep
                # generated Makefile.in files strictly newer than every
                # Autotools input, otherwise make regenerates configure and
                # loses the patched config.status machinery.
                stamp = max(existing) + 2_000_000_000
                if os.stat(makefile_in).st_mtime_ns < stamp:
                    os.utime(makefile_in, ns=(stamp, stamp))

    def package(self):
        Autotools(self).install(args=self._autotools_make_args())
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        if str(self.settings.os) == "OHOS":
            self._sign_elf_files()

    def package_info(self):
        # This package is consumed as a PAM application/module, not with
        # ``-lbarada-pam``. Keep the module directory visible to consumers and
        # expose barada-add as the package command.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib/security"]
        self.cpp_info.set_property("cmake_file_name", "barada-pam")
        self.cpp_info.set_property("cmake_target_name", "barada-pam::module")

        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib/security")
        )

    def _sign_elf_files(self):
        """Sign every installed ELF executable and shared object for OHOS."""
        objcopy = self._find_ohos_tool("llvm-objcopy")
        objdump = self._find_ohos_tool("llvm-objdump")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not objdump or not signer:
            raise ConanException(
                "OHOS signing tools unavailable: llvm-objcopy, llvm-objdump "
                "and binary-sign-tool are required"
            )

        elf_files = self._installed_elf_files()
        if not elf_files:
            raise ConanException(
                "OHOS package contains no ELF files to sign; expected "
                "barada-add and pam_barada.so"
            )

        for path in elf_files:
            original_mode = stat.S_IMODE(os.stat(path).st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(path)
            ) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                shutil.copy2(path, unsigned)
                self._run_signing_tool(
                    [objcopy, "--remove-section", ".codesign", unsigned],
                    f"remove the old code signature from {path}",
                    allow_failure=True,
                )
                self._run_signing_tool(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        unsigned,
                        "-outFile",
                        unsigned,
                        "-selfSign",
                        "1",
                    ],
                    f"sign {path}",
                )
                if not self._has_codesign_section(objdump, unsigned):
                    raise ConanException(
                        f"OHOS signing did not add a .codesign section to {path}"
                    )
                os.replace(unsigned, path)
            os.chmod(path, original_mode)

    def _installed_elf_files(self):
        files = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                path = os.path.join(root, filename)
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                try:
                    with open(path, "rb") as handle:
                        if handle.read(4) == b"\x7fELF":
                            files.append(path)
                except OSError as error:
                    raise ConanException(
                        f"Unable to inspect installed file {path}: {error}"
                    )
        return sorted(files)

    @staticmethod
    def _run_signing_tool(command, action, allow_failure=False):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanException(f"Unable to {action}: {error}") from error
        if result.returncode != 0 and not allow_failure:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanException(
                f"Unable to {action}: {detail or 'tool exited unsuccessfully'}"
            )
        return result

    @classmethod
    def _has_codesign_section(cls, objdump, path):
        result = cls._run_signing_tool(
            [objdump, "-h", path], f"inspect ELF sections in {path}"
        )
        return any(
            ".codesign" in line.split() for line in result.stdout.splitlines()
        )

    def _find_ohos_tool(self, name):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("cpp", "")
        compiler_dir = os.path.dirname(compiler)
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")
