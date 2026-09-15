#!/usr/bin/env python3
"""Conan recipe for codecrypt 1.8 — post-quantum cryptography tool (ccr).

codecrypt is a GnuPG-like unix tool for encryption and signing that uses only
quantum-computer-resistant algorithms (McEliece QC-MDPC for encryption,
FMTSeq hash-based Merkle tree for signatures).  Upstream ships a single
`ccr` CLI binary; there is no installable library.

Build: Autotools, bootstrapped from the tag tarball via `bash autogen.sh`
(the tarball ships configure.ac but no pre-generated `configure`).

Dependencies (all published on ohpcd):
  - gmp/6.3.0.1     (bignum, hard requirement of configure.ac)
  - fftw/3.3.11     (FFT for XSynd stream cipher, hard requirement)
  - cryptopp/8.9.0  (SHA/RIPEMD/TIGER hash algorithm variants; configure
                     would also accept --without-cryptopp, but cryptopp IS
                     published, so keep the full algorithm suite)

OHOS adaptations (patch 0001, applied to src/pwrng.cpp only):
  - musl on OHOS has neither <readpassphrase.h> nor getpass(3).  The upstream
    source itself suggests (in a comment) inlining a readpassphrase()
    implementation "from e.g. openssh's openbsd-compat".  The patch adds a
    minimal termios-based ohos_readpassphrase() behind `#elif !defined(HAVE_GETPASS)` (POSIX feature-macro guard, no platform macro),
    with echo disabled while typing and terminal state restored afterwards.

Build notes (matching other OHOS autotools recipes):
  - the tarball ships no `configure`, so build() runs `bash autogen.sh`
    first (automake/libtool pulled in via tool_requires);
  - the generated `configure` is patched in-tree to drop `umask 077` from the
    config.status temp-dir creation (E114: HMDFS turns a 0700 temp dir into an
    unwritable drwx--S--- dir);
  - make runs with -j1 (E074: HMDFS jobserver fifo EPERM);
  - LD_LIBRARY_PATH is prepended with dependency libdirs so configure's
    conftest binaries can run (shared gmp/fftw are not in the default loader
    path);
  - AutotoolsDeps LIBS would include -lgmpxx (C++ binding of gmp); the C
    conftest cannot load it (needs libc++).  codecrypt only uses the C API
    (__gmpz_init etc.), so LIBS is set to the exact set configure needs.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class CodecryptConan(ConanFile):
    name = "codecrypt"
    version = "1.8"
    description = ("Post-quantum cryptography tool (ccr): GnuPG-like unix "
                   "program for encryption and signing using only "
                   "quantum-computer-resistant algorithms "
                   "(McEliece QC-MDPC + FMTSeq Merkle signatures)")
    license = "LGPL-3.0-or-later"
    homepage = "http://e-x-a.org/codecrypt/"
    url = "https://github.com/exaexa/codecrypt"

    # Single CLI binary, not a library (R38: commands.json at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0.1")
        self.requires("fftw/3.3.11")
        self.requires("cryptopp/8.9.0")

    def build_requirements(self):
        # The tarball ships no `configure`; bootstrap needs the full
        # autotools suite.  The build host (CI sandbox / minimal OHOS image)
        # only has autoconf under /data/service/hnp/bin, so pull in automake
        # and libtool as tool_requires (same approach as
        # abiword-plugin-clarisworks / aaphoto).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def configure(self):
        # Upstream is C++11 code (autogen.sh: ccr_CXXFLAGS = -Wall -std=c++11).
        # Under C++17 the global `typedef unsigned char byte` (src/types.h)
        # becomes ambiguous with std::byte in every TU that has
        # `using namespace std` (hashfile.cpp etc.).  Drop the profile cppstd
        # so the toolchain does not inject -std=c++17; upstream's own
        # -std=c++11 (baked into the generated Makefile) applies.
        self.settings.rm_safe("compiler.cppstd")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "codecrypt is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # AutotoolsDeps feeds -I/-L/-l of gmp/fftw/cryptopp into
        # configure/make.  It also adds -lgmpxx (C++ bindings) which the C
        # conftest cannot run (needs libc++); codecrypt only uses the C API,
        # so LIBS is fixed up below.
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS",
        # kernel "HongMeng Kernel") and its compiler probe also fails under
        # the HMDFS tmp dir (E114-style permission issue).  Pass the triplet
        # explicitly (config.sub supports *-linux-ohos) so configure never
        # runs the config.guess probe.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

        # pkg-config module name upstream expects is `libcrypto++`, while the
        # conan cryptopp package provides `cryptopp.pc`.  PKG_CHECK_MODULES
        # honors pre-set CRYPTOPP_CFLAGS/CRYPTOPP_LIBS env vars, so feed the
        # dependency paths directly.
        env = Environment()
        cryptopp = self.dependencies["cryptopp"]
        cryptopp_includes = " ".join(
            "-I" + os.path.join(cryptopp.package_folder, d)
            for d in cryptopp.cpp_info.includedirs)
        cryptopp_libdirs = " ".join(
            "-L" + os.path.join(cryptopp.package_folder, d)
            for d in cryptopp.cpp_info.libdirs)
        env.define("CRYPTOPP_CFLAGS", cryptopp_includes)
        env.define("CRYPTOPP_LIBS", cryptopp_libdirs + " -lcryptopp")
        # AutotoolsDeps LIBS contains -lgmpxx; override with the exact libs
        # configure/make need (C API only).
        gmp = self.dependencies["gmp"]
        fftw = self.dependencies["fftw"]
        env.define("LIBS", "-lfftw3 -lgmp -lcryptopp -lm")
        for d in gmp.cpp_info.libdirs:
            env.prepend_path("LD_LIBRARY_PATH",
                             os.path.join(gmp.package_folder, d))
        for d in fftw.cpp_info.libdirs:
            env.prepend_path("LD_LIBRARY_PATH",
                             os.path.join(fftw.package_folder, d))
        for d in cryptopp.cpp_info.libdirs:
            env.prepend_path("LD_LIBRARY_PATH",
                             os.path.join(cryptopp.package_folder, d))
        env.vars(self, scope="build").save_script("conanbuild_ccr")

    def build(self):
        # Bootstrap: the tarball ships no `configure`; autogen.sh generates
        # Makefile.am + configure from configure.ac. chmod first: tarball
        # extracts with -rwxrwx--- and the CI user lacks group bit (E126).
        os.chmod(os.path.join(self.source_folder, "autogen.sh"), 0o755)
        self.run("bash autogen.sh", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS forces
        # setgid; `umask 077 && mktemp -d` creates a drwx--S--- temp dir that
        # is not writable even by its owner, breaking config.status).
        _conf = os.path.join(self.source_folder, "configure")
        replace_in_file(self, _conf,
                        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
        replace_in_file(self, _conf,
                        '(umask 077 && mkdir "$tmp")',
                        'mkdir "$tmp"')
        autotools = Autotools(self)
        autotools.configure()
        # R9/E074: single job — parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Standalone ccr binary, no library artifacts
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
