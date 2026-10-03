#!/usr/bin/env python3
"""Consumer test for the packaged libgccjit 16.1.1 JIT library.

The test links the consumer program against libgccjit.so and runs a real
in-process JIT compilation: libgccjit compiles a small C function,
materialises executable machine code (the W^X / SELinux-sensitive JIT
path), executes the generated function and verifies the result.
"""

import os
import re
import shlex
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class LibgccjitTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_jit.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _sign_program(self, path):
        if str(self.settings.os) != "OHOS":
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not (os.path.isfile(signer) and objcopy and readelf):
            raise ConanInvalidConfiguration(
                "Running the JIT test on OHOS requires binary-sign-tool, "
                "llvm-objcopy and llvm-readelf"
            )
        elf_header = subprocess.run(
            [readelf, "-h", path],
            capture_output=True,
            text=True,
            check=True,
        )
        if not re.search(r"Type:\s+(?:EXEC|DYN)\b", elf_header.stdout):
            raise ConanInvalidConfiguration(
                "JIT test output is not a runnable ELF file: {}".format(path)
            )
        original_mode = stat.S_IMODE(os.stat(path).st_mode)
        with tempfile.TemporaryDirectory(
            prefix=".conan-sign-", dir=os.path.dirname(path)
        ) as temp_dir:
            os.chmod(temp_dir, 0o775)
            unsigned = os.path.join(temp_dir, "unsigned")
            signed = os.path.join(temp_dir, "signed")
            shutil.copy2(path, unsigned)
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", unsigned],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    unsigned,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                check=True,
            )
            signed_header = subprocess.run(
                [readelf, "-h", signed],
                capture_output=True,
                text=True,
                check=True,
            )
            if not re.search(
                r"Type:\s+(?:EXEC|DYN)\b", signed_header.stdout
            ):
                raise ConanInvalidConfiguration(
                    "Signing did not produce a runnable ELF: {}".format(path)
                )
            signed_sections = subprocess.run(
                [readelf, "-S", signed],
                capture_output=True,
                text=True,
                check=True,
            )
            if ".codesign" not in signed_sections.stdout:
                raise ConanInvalidConfiguration(
                    "Signing did not add .codesign: {}".format(path)
                )
            os.replace(signed, path)
            os.chmod(
                path,
                original_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH,
            )

    def build(self):
        dependency = self.dependencies["libgccjit"]
        include = os.path.join(dependency.package_folder, "include")
        lib = os.path.join(dependency.package_folder, "lib")
        if not (os.path.isfile(os.path.join(include, "libgccjit.h")) and
                os.path.isdir(lib)):
            raise ConanInvalidConfiguration(
                "The libgccjit package is missing its public headers or "
                "library directory: {} / {}".format(include, lib)
            )
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compiler_executables.get("c", "clang")
        source = os.path.join(self.source_folder, "test_jit.c")
        executable = os.path.join(self.build_folder, "jit_test_program")
        # -Wl,-rpath keeps the JIT consumer runnable on OHOS where the
        # loader does not search package lib directories by default.
        self.run(
            '{} "{}" -I"{}" -L"{}" -Wl,-rpath,"{}" -lgccjit -o "{}"'.format(
                cc, source, include, lib, lib, executable
            ),
            ignore_errors=False,
        )
        self._sign_program(executable)

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-building: JIT consumer linked successfully; execution skipped"
            )
            return
        executable = os.path.join(self.build_folder, "jit_test_program")
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                "The JIT test executable was not found: {}".format(executable)
            )
        env_prefix = ""
        if str(self.settings.os) == "OHOS":
            # libgccjit's in-process (embedded) driver does not run the
            # packaged bin/gcc wrapper, so the -B startfile paths the
            # wrapper injects are all missing.  Derive the same two
            # directories (sysroot crt files and the packaged libgcc) and
            # pass them to test_jit.c through the environment; it injects
            # them with gcc_jit_context_add_driver_option.
            dependency = self.dependencies["libgccjit"]
            compiler_executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            cc = compiler_executables.get("c", "clang")
            sysroot = os.path.normpath(
                os.path.join(
                    os.path.dirname(os.path.realpath(cc)),
                    "..",
                    "..",
                    "sysroot",
                )
            )
            if not os.path.isdir(os.path.join(sysroot, "usr", "include")):
                raise ConanInvalidConfiguration(
                    "OHOS SDK sysroot headers were not found: {}".format(sysroot)
                )
            # Match the recipe's _target_triplet: get_gnu_triplet does not
            # yield the OHOS triple (aarch64-linux-ohos).
            target = "aarch64-linux-ohos"
            crt_dir = os.path.join(sysroot, "usr", "lib", target)
            gcc_lib_root = os.path.join(
                dependency.package_folder, "lib", "gcc", target
            )
            version_dirs = sorted(
                d for d in os.listdir(gcc_lib_root)
                if os.path.isdir(os.path.join(gcc_lib_root, d))
            )
            if not version_dirs:
                raise ConanInvalidConfiguration(
                    "No GCC version directory under {}".format(gcc_lib_root)
                )
            gcc_dir = os.path.join(gcc_lib_root, version_dirs[-1])
            # libgccjit JIT-compiles into a temporary fake.so and dlopens
            # it; OHOS rejects unsigned ELF loads (E077, Permission
            # denied).  Point the in-process JIT at binary-sign-tool so
            # the patched dlopen path signs fake.so before loading it.
            signer = shutil.which("binary-sign-tool") or (
                "/data/service/hnp/bin/binary-sign-tool"
            )
            env_prefix = (
                "OHOS_JIT_B_CRT={} OHOS_JIT_B_GCC={} "
                "OHOS_JIT_SIGNER={} ".format(
                    shlex.quote("-B{}/".format(crt_dir)),
                    shlex.quote("-B{}/".format(gcc_dir)),
                    shlex.quote(signer),
                )
            )
        self.run(
            env_prefix + shlex.quote(executable),
            env="conanrun",
            ignore_errors=False,
        )
