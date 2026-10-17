#!/usr/bin/env python3
"""Conan recipe for ed25519 0.0-git.b1f19fa (orlp portable Ed25519).

orlp/ed25519 is a portable, dependency-free Ed25519 (EdDSA over
Curve25519) implementation: keypair generation, signing, verification,
keypair scalar addition and X25519-style key exchange, all built on an
in-tree SHA-512 plus field/group/scalar arithmetic. Upstream ships NO
build system at all (no CMakeLists.txt / Makefile — only a src/ folder
of 10 .c + 7 .h files, a test driver test.c and two prebuilt Windows
DLLs); the readme integration model is "add all .c and .h files in the
src/ folder to your project". This recipe turns that file set into a
thin static library instead:

  * compiles the ten upstream src/*.c translation units with the
    HarmonyOS Clang toolchain (-std=c99 -Wall -pedantic -O2) and
    archives libed25519.a with llvm-ar,
  * compiles the UNMODIFIED upstream test driver test.c, links it
    against the freshly built static library, runs it on the OHOS
    target after self-signing with binary-sign-tool, and asserts the
    happy-path outputs ("valid signature" exactly twice — before and
    after scalar addition — plus "correctly detected signature change"
    and "key exchange was correct") while rejecting every failure-path
    output,
  * packages the public ed25519.h together with the in-tree internal
    headers and license.txt; the Windows DLLs shipped in the tarball
    root are never packaged.

Upstream snapshot: master @ b1f19fab4aebe607805620d25a5e42566ce46a0e
(the 7-hex prefix b1f19fa is the version tag per the git-snapshot
convention 0.0-git.{hash7} for repositories without release tags).

Zero third-party dependencies: SHA-512, field / group / scalar
arithmetic are all implemented in-tree (self-contained primitives).
"""
import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


ED25519_SOURCES = [
    "add_scalar.c",
    "fe.c",
    "ge.c",
    "key_exchange.c",
    "keypair.c",
    "sc.c",
    "seed.c",
    "sha512.c",
    "sign.c",
    "verify.c",
]

# Happy-path outputs of the upstream driver: each must appear (with
# "valid signature" exactly twice — the second one covers the keypair
# after ed25519_add_scalar), and no failure-path output may show up.
UPSTREAM_MUST = (
    "valid signature",
    "correctly detected signature change",
    "key exchange was correct",
)
UPSTREAM_MUST_NOT = (
    "invalid signature",
    "did not detect signature change",
    "key exchange was incorrect",
)


class Ed25519Conan(ConanFile):
    name = "ed25519"
    version = "0.0-git.b1f19fa"
    description = "Portable Ed25519 digital signatures (keypair/sign/verify/key exchange), C99, zero dependencies"
    license = "Zlib"
    homepage = "https://github.com/orlp/ed25519"
    url = "https://github.com/orlp/ed25519"
    topics = ("ed25519", "eddsa", "digital-signature", "cryptography", "c99")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "ed25519 currently supports only OHOS armv8 in this recipe"
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

        common = (
            f'{shlex.quote(cc)} -std=c99 -Wall -pedantic -O2 '
            f'-I{shlex.quote(str(source / "src"))}'
        )

        # 1) static library from the ten upstream translation units
        objects = []
        for src_file in ED25519_SOURCES:
            obj = build / (src_file + ".o")
            self.run(
                f'{common} -c {shlex.quote(str(source / "src" / src_file))} '
                f'-o {shlex.quote(str(obj))}',
                env="conanbuild",
            )
            objects.append(obj)
        library = build / "libed25519.a"
        self.run(
            f'{shlex.quote(ar)} rcs {shlex.quote(str(library))} '
            + " ".join(shlex.quote(str(o)) for o in objects),
            env="conanbuild",
        )

        # 2) upstream test driver: unmodified test.c, linked against the
        #    library built above, executed natively on OHOS. The driver
        #    always exits 0, so correctness is asserted on its output:
        #    the four semantic checks (sign+verify on the initial keypair,
        #    sign+verify after ed25519_add_scalar, tampered-signature
        #    rejection, key-exchange agreement from both sides) must all
        #    print their happy-path line and no failure line may appear.
        #    The trailing 6x10000 performance sweeps are timing output
        #    only and are not counted as assertions.
        test_executable = build / "ed25519-test"
        self.run(
            f'{common} {shlex.quote(str(source / "test.c"))} '
            f'{shlex.quote(str(library))} '
            f'-o {shlex.quote(str(test_executable))}',
            env="conanbuild",
        )
        self._sign(test_executable)
        result = subprocess.run(
            [str(test_executable)],
            capture_output=True,
            text=True,
            timeout=300,
            env=dict(os.environ),
        )
        output = (result.stdout or "") + (result.stderr or "")
        valid_count = output.count("valid signature") - output.count(
            "invalid signature"
        )
        if (
            result.returncode != 0
            or valid_count != 2
            or any(m not in output for m in UPSTREAM_MUST)
            or any(m in output for m in UPSTREAM_MUST_NOT)
        ):
            raise ConanException(
                "upstream ed25519 test.c driver failed (rc=%d):\n%s"
                % (result.returncode, output)
            )

    def package(self):
        copy(self, "libed25519.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "license.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["ed25519"]
        self.cpp_info.set_property("cmake_file_name", "ed25519")
        self.cpp_info.set_property("cmake_target_name", "ed25519::ed25519")
        self.cpp_info.set_property("pkg_config_name", "ed25519")

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
