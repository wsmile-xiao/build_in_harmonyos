#!/usr/bin/env python3
"""Conan recipe for secpwgen 1.3 — secure password / passphrase generator.

secpwgen derives high-entropy secrets from the OpenSSL CSPRNG: Diceware
(8192-word) and S/Key (2048-word) passphrases with optional "enhanced"
symbol interleaving, filtered ASCII random strings, BASE64 raw random bits
and the koremutake syllable encoding introduced in 1.3.  The passphrase and
the RNG state live in mlock()'ed memory that is zeroed on exit; core dumps
are disabled and surplus privileges are dropped before generation starts.

Upstream ships a hand-written `Makefile.proto` and instructs the packager to
copy it to `Makefile`, uncomment a crypto backend and edit PREFIX.  There is
no configure script, no CMake and no test target.  build() therefore drives
`make -f Makefile.proto` with command-line variable assignments rather than
patching the build system:

    CC            taken from Conan conf `tools.build:compiler_executables`
                  (R33 — never a bare shell ${CC}, which is empty on release
                  workers and silently produces a host build)
    CRYPTO_OBJS   secure_random_openssl.o — selects the OpenSSL SRNG backend;
                  upstream leaves it commented out (cryptlib is the other one)
    CFLAGS        adds -DOPENSSL_SUPPRESS_DEPRECATED: secure_random_openssl.c
                  deliberately uses the low-level Blowfish API (BF_set_key /
                  BF_ecb_encrypt), deprecated but still shipped since 3.0
    LDFLAGS       -L<openssl>/lib -lcrypto -lm, and drops the upstream
                  default `LINK_STATIC = -static`, which is wrong for a
                  relocatable Conan package

HarmonyOS PC (aarch64) adaptation:
    * openssl/3.5.6 is consumed in its static variant (that recipe builds
      `no-shared` per R26, libcrypto being a system-name library), so the
      packaged binary is self-contained and DT_NEEDED carries libc.so only.
    * patches/0001-secure_memory_unix.c.patch guards drop_privileges().
      Upstream calls seteuid(getuid()) unconditionally, which is a no-op for
      an ordinary non-setuid invocation.  HarmonyOS refuses the privileged-id
      syscall issued by an unprivileged process with an *uncatchable* SIGSYS
      (knowledge E051, exit code 159), so the unpatched binary dies during
      startup before printing anything.  The guard skips the syscall when the
      effective uid already equals the real uid.  It is plain POSIX — no
      platform macro (R8/PF5) — and keeps upstream behaviour for genuine
      setuid binaries.
    * mlockall(MCL_FUTURE)/mlock() and setrlimit(RLIMIT_CORE) failures are
      already non-fatal upstream ("WARNING: using insecure memory."), which
      is exactly the degradation the OHOS application sandbox needs, so no
      further patch is required.

Artifacts: bin/secpwgen + share/man/man1/secpwgen.1 (software-level
commands.json declares the CLI, R38).
License: MIT.
"""
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class SecpwgenConan(ConanFile):
    name = "secpwgen"
    version = "1.3"
    description = (
        "Secure password and passphrase generator using the OpenSSL CSPRNG: "
        "Diceware/S-Key passphrases, filtered ASCII random strings, BASE64 "
        "raw random bits and koremutake encoding, with memory locking"
    )
    license = "MIT"
    homepage = "https://github.com/itoffshore/secpwgen"
    url = "https://github.com/itoffshore/secpwgen"
    topics = ("password", "passphrase", "diceware", "security", "openssl", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)
        # The HarmonyOS ABI checker lives next to the consumer tests but is also
        # needed at build() time (only there is secure_memory_unix.o available
        # for the E051 guard check), so export it with the recipe.
        copy(self, "ohos_abi_check.py",
             src=os.path.join(self.recipe_folder, "test_package"),
             dst=os.path.join(self.export_sources_folder, "test_package"))

    def layout(self):
        basic_layout(self)
        # Hand-written Makefile.proto project: build in the source folder so
        # that the object files and the `secpwgen` binary land next to the
        # sources, exactly as upstream's Makefile expects.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # secure_random_openssl.c: <openssl/rand.h> RAND_bytes +
        # <openssl/blowfish.h> BF_set_key/BF_ecb_encrypt, linked with -lcrypto.
        self.requires("openssl/3.5.6")

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(
                "secpwgen requires a POSIX host (Linux or OHOS): it uses "
                "mmap/mprotect/mlockall and <sys/resource.h>")

    @property
    def _abi_checker(self):
        return os.path.join(self.export_sources_folder, "test_package",
                            "ohos_abi_check.py")

    @staticmethod
    def _first_dir(dep, attr):
        """First cpp_info directory of a dependency, made absolute."""
        dirs = list(getattr(dep.cpp_info, attr, []) or [])
        if not dirs:
            return ""
        path = dirs[0]
        return path if os.path.isabs(path) else os.path.join(dep.package_folder, path)

    def generate(self):
        openssl = self.dependencies["openssl"]
        self._ossl_inc = self._first_dir(openssl, "includedirs")
        self._ossl_lib = self._first_dir(openssl, "libdirs")
        if not self._ossl_inc or not self._ossl_lib:
            raise ConanException(
                "openssl package exposes no include/lib dirs — cannot wire "
                "secure_random_openssl.o")
        # No generator files needed: Makefile.proto consumes everything through
        # variables injected on the make command line in build().

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler path from Conan conf, never from an undefined shell var.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R9: -j1.  GNU make: command-line assignments beat makefile ones, so
        # this simultaneously selects the OpenSSL backend (CRYPTO_OBJS), feeds
        # the cross compiler (CC), and replaces the upstream CFLAGS/LDFLAGS —
        # dropping `LINK_STATIC = -static`, which cannot work against the
        # Conan-provided libcrypto.a in a relocatable package.
        self.run(
            'make -f Makefile.proto -j1 CC="{0}" '
            'CRYPTO_OBJS=secure_random_openssl.o '
            'CFLAGS="-O2 -Wall -DOPENSSL_SUPPRESS_DEPRECATED -I{1}" '
            'LDFLAGS="-L{2} -lcrypto -lm"'.format(cc, self._ossl_inc, self._ossl_lib)
        )
        binary = os.path.join(self.build_folder, "secpwgen")
        if not os.path.isfile(binary):
            raise ConanException("build(): make did not produce %s" % binary)
        # HMDFS/chmod guard (E046): make the artifact executable explicitly.
        os.chmod(binary, 0o755)
        # HarmonyOS artifact checks A1-A4 (test_package/ohos_abi_check.py).
        # --object adds A4: secure_memory_unix.o must reference geteuid, which
        # only the E051 drop_privileges() guard does — the unpatched
        # translation unit never calls it.  The object file exists only here,
        # not in the package, so A4 cannot move to test_package.
        obj = os.path.join(self.build_folder, "secure_memory_unix.o")
        self.run(" ".join(shlex.quote(arg) for arg in (
            sys.executable, self._abi_checker,
            "--binary", binary, "--object", obj)))

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        licdir = os.path.join(self.package_folder, "licenses")
        for d in (bindir, mandir, licdir):
            os.makedirs(d, exist_ok=True)
        # Direct copy instead of `make install`: the upstream rule uses
        # `cp -i` (interactive, silently skips on a non-tty when the target
        # exists) and installs into a hardcoded $(PREFIX) with no mkdir -p.
        # copy()'s src must be a *folder* (it walks it and fnmatches names),
        # so pass the build folder and the bare file name as the pattern.
        copy(self, "secpwgen", src=self.build_folder, dst=bindir,
             keep_path=False)
        copy(self, "secpwgen.1", src=self.source_folder, dst=mandir,
             keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=licdir, keep_path=False)
        exe = os.path.join(bindir, "secpwgen")
        if not os.path.isfile(exe):
            raise ConanException("package(): missing build artifact %s" % exe)
        os.chmod(exe, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # Application package: nothing to re-export to consumers, but the CLI
        # must be resolvable through PATH in VirtualRunEnv (test_package).
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
