#!/usr/bin/env python3
"""Conan recipe for lsof 4.99.0 -- LiSt Open Files command-line tool.

lsof uses its own custom Configure script (not autotools) and a plain Makefile.
The Configure script probes the system by compiling test programs to determine
available features (IPv6, UXP socket, PTY endpoint, etc.) and generates
machine.h + Makefile.

Build system: custom Configure + make
Output: lsof binary (command-line tool, not a library)

Key adaptation for OHOS:
- Configure script's Mksrc shebang patched to /data/service/hnp/bin/bash
- dlsof.h patched to resolve sockaddr_storage redefinition (linux/socket.h
  vs sys/socket.h conflict)
- LSOF_INCLUDE set to OHOS sysroot include path (discovered via clang -print-sysroot)
- LINUX_CONF_CC set to Conan-provided clang
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LsofConan(ConanFile):
    name = "lsof"
    version = "4.99.0"
    description = "LiSt Open Files - a command-line utility that displays information about files opened by processes"
    license = "SSPL-1.0"
    homepage = "https://github.com/lsof-org/lsof"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # lsof has no external dependencies (pure C, only libc)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R32: Platform compatibility check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanDbalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars
        cc = self.conf.get("tools.build:compiler_executables:c", "clang", check_type=str)

        # Find OHOS sysroot include path from compiler
        # lsof's Configure script needs LSOF_INCLUDE to find system headers
        lsof_include = "/usr/include"
        try:
            result = subprocess.run(
                [cc, "-print-sysroot"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                sysroot = result.stdout.strip()
                candidate = os.path.join(sysroot, "usr", "include")
                if os.path.isdir(candidate):
                    lsof_include = candidate
        except Exception:
            pass  # Fallback to /usr/include

        # R5: Use CONFIG_SHELL for Configure script (OHOS has no /bin/sh)
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        # Set env vars for lsof's Configure script
        # LINUX_CONF_CC: compiler for probing system features
        # LSOF_INCLUDE: include path for system headers
        os.environ["LINUX_CONF_CC"] = cc
        os.environ["LSOF_INCLUDE"] = lsof_include

        # Run lsof's custom Configure script
        # -n: skip AFS/customization/inventory checks (non-interactive)
        # linux: select Linux dialect
        self.run(f"{config_shell} ./Configure -n linux")

        # R9: Always use -j1
        self.run(f"make CC={cc} -j1")

    def package(self):
        # lsof has no make install rule; copy binary manually
        copy(self, "lsof", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

        # R7: Self-sign ELF binary on OHOS for local execution
        if self.settings.os == "OHOS":
            lsof_path = os.path.join(self.package_folder, "bin", "lsof")
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            if os.path.isfile(sign_tool) and os.path.isfile(lsof_path):
                signed_path = f"{lsof_path}.signed"
                try:
                    self.run(
                        f'{sign_tool} sign -inFile "{lsof_path}"'
                        f' -outFile "{signed_path}"'
                        f' -selfSign 1 -signAlg SHA256withECDSA',
                        quiet=True
                    )
                    if os.path.isfile(signed_path):
                        os.replace(signed_path, lsof_path)
                        os.chmod(lsof_path, 0o755)
                except Exception:
                    pass  # Signing may fail on some environments; non-fatal

    def package_info(self):
        # lsof is a command-line tool, not a library
        self.cpp_info.lib = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]