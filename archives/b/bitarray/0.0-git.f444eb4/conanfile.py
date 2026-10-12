#!/usr/bin/env python3
"""Conan recipe for bitarray 0.0-git.f444eb4 (noporpoise BitArray C library)."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class BitarrayConan(ConanFile):
    name = "bitarray"
    version = "0.0-git.f444eb4"
    description = (
        "BitArray: a C library for creating and manipulating bit arrays "
        "(bitset / bitmap), with arithmetic, permutation and hash helpers"
    )
    license = "CC0-1.0"
    homepage = "https://github.com/noporpoise/bitarray"
    url = "https://github.com/noporpoise/bitarray"
    topics = ("bit-array", "bitset", "bitmap", "c99", "bit-manipulation")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "bitarray currently supports only OHOS armv8 in this recipe"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c") or "clang"
        ar = shutil.which("llvm-ar") or "/data/service/hnp/bin/llvm-ar"
        source = Path(self.source_folder)
        build = Path(self.build_folder)
        build.mkdir(parents=True, exist_ok=True)

        # Upstream Makefile compiles bit_array.c with
        #   $(CC) -Wall -Wextra -Wc++-compat $(OPT) -fPIC -c bit_array.c
        # and archives libbitarr.a via `ar -csru`.  The library is a single
        # translation unit with zero third-party dependencies.
        obj = build / "bit_array.o"
        library = build / "libbitarr.a"
        self.run(
            f'{shlex.quote(cc)} -std=c99 -Wall -Wextra -Wc++-compat -O2 '
            f'-fPIC -I{shlex.quote(str(source))} '
            f'-c {shlex.quote(str(source / "bit_array.c"))} '
            f'-o {shlex.quote(str(obj))}',
            env="conanbuild",
        )
        self.run(
            f'{shlex.quote(ar)} rcs {shlex.quote(str(library))} '
            f'{shlex.quote(str(obj))}',
            env="conanbuild",
        )

        # Upstream test programs.  `make test` (dev/Makefile) builds and runs
        # bit_array_test (linked against libbitarr.a) and bitlock_test
        # (header-only, links pthread).  The test sources are unmodified;
        # -std=gnu99 is used instead of the Makefile default so POSIX/STD
        # declarations in the system headers stay visible.
        bit_array_test = build / "bit_array_test"
        self.run(
            f'{shlex.quote(cc)} -std=gnu99 -Wall -Wextra -Wc++-compat -O2 '
            f'-I{shlex.quote(str(source))} '
            f'{shlex.quote(str(source / "dev" / "bit_array_test.c"))} '
            f'{shlex.quote(str(library))} '
            f'-o {shlex.quote(str(bit_array_test))}',
            env="conanbuild",
        )
        self._sign(bit_array_test)
        self.run(shlex.quote(str(bit_array_test)), env="conanrun")

        bitlock_test = build / "bitlock_test"
        self.run(
            f'{shlex.quote(cc)} -std=gnu99 -Wall -Wextra -O2 '
            f'-I{shlex.quote(str(source))} '
            f'{shlex.quote(str(source / "dev" / "bitlock_test.c"))} '
            f'-lpthread '
            f'-o {shlex.quote(str(bitlock_test))}',
            env="conanbuild",
        )
        self._sign(bitlock_test)
        self.run(shlex.quote(str(bitlock_test)), env="conanrun")

    def package(self):
        copy(self, "libbitarr.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        # Public headers: bit_array.h includes bit_macros.h; bar.h is the
        # upstream-provided short-name wrapper API (used by the bar test
        # suite upstream), so both are shipped.
        for header in ("bit_array.h", "bit_macros.h", "bar.h"):
            copy(self, header, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["bitarr"]
        self.cpp_info.set_property("cmake_file_name", "bitarray")
        self.cpp_info.set_property("cmake_target_name", "bitarray::bitarray")
        self.cpp_info.set_property("pkg_config_name", "bitarray")

    @staticmethod
    def _sign(executable):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to execute upstream tests on OHOS"
            )
        signed = executable.with_suffix(executable.suffix + ".signed")
        if os.path.isfile(objcopy):
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", str(executable)],
                check=False,
            )
        subprocess.run(
            [signer, "sign", "-inFile", str(executable), "-outFile", str(signed),
             "-selfSign", "1"],
            check=True,
        )
        shutil.move(signed, executable)
        os.chmod(executable, 0o755)
