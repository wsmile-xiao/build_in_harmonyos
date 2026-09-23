#!/usr/bin/env python3
"""Conan recipe for GNU ccRTP 2.1.2 (autotools build).

GNU ccRTP is a C++ RTP (Real-time Transport Protocol) library built on top of
the GNU uCommon C++ framework.  This recipe builds the core RTP library on
OHOS/aarch64 with SRTP disabled (SRTP is an optional crypto layer; upstream
configure hard-fails when neither libgcrypt nor OpenSSL is found, and the
crypto backend is not needed for the core RTP functionality).

OHOS adaptations (patches, numbered as in conandata.yml, all strip=1 git-style):
  - 0001 autoconf/config.guess:  recognize HarmonyOS -> aarch64-unknown-linux-ohos
                            (shipped 2013 script cannot guess build type on OHOS)
  - 0002 autoconf/config.sub:    accept -linux-ohos* kernel/OS triples
  - 0003 configure:         define SRTP_OPENSSL/SRTP_GCRYPT automake
                            conditionals unconditionally.  configure.ac only
                            emits them inside the SRTP-enabled branch, so a
                            --disable-srtp build aborts with 'conditional
                            "SRTP_OPENSSL" was never defined'.  Also umask 022
                            for the config.status tmp dir (E129 HMDFS setgid)
  - 0004 src/CryptoContextCtrl.cpp:  SrtpEncryptionNull/SrtpAuthenticationNull
                            are referenced outside the SRTP_SUPPORT guards, but
                            they are declared in ccrtp/CryptoContext.h which is
                            only pulled in (via SrtpSymCrypto.h) when SRTP is
                            enabled -> include ccrtp/CryptoContext.h explicitly

Compile standard: the profile uses cppstd=17.  ccrtp's own WARN_FLAGS pass
`-ansi` (C++03) which would trigger ucommon's legacy `nullptr` shim in
platform.h -> collides with libc++'s `nullptr` macro.  The -std=c++17 flag is
appended to CXXFLAGS (last on the command line, after AM_CXXFLAGS) so it
overrides `-ansi` and the shim is skipped.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class CcrtpConan(ConanFile):
    name = "ccrtp"
    version = "2.1.2"
    description = "GNU ccRTP - C++ RTP (Real-time Transport Protocol) library"
    license = "LGPL-2.1-or-later"
    url = "https://www.gnu.org/software/ccrtp/"
    homepage = "https://www.gnu.org/software/ccrtp/"
    topics = ("rtp", "srtp", "streaming", "network", "gnu")

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ccrtp supports Linux/OHOS only")
        if str(self.settings.os) == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # GNU ccRTP is built on uCommon (configure requires commoncpp >= 6.2.2).
        # ucommon/7.0.1 is the published version on ohpcd (R36: released first).
        # transitive_headers=True: ccrtp's *public* headers include <ucommon/*> and
        # <commoncpp/*>, so downstream consumers must see ucommon's include dirs.
        # Conan's transform_downstream() sets headers=False for static->static
        # chains by default, which would drop ucommon's include dirs from the
        # consumer's CMakeDeps graph (E-draft: ccrtp transitive include). The
        # cpp_info.requires=["ucommon::ucommon"] alone is NOT enough — it only
        # carries the link edge, not the include paths of a hidden dep.
        self.requires("ucommon/7.0.1", transitive_headers=True)

    def build_requirements(self):
        # configure uses PKG_CHECK_MODULES for the `commoncpp` pkg-config module
        self.tool_requires("pkgconf/3.0.5")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps: inject CPPFLAGS/LDFLAGS from ucommon + transitive deps
        AutotoolsDeps(self).generate()
        # PkgConfigDeps: generate ucommon.pc (and transitive dep .pc files)
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # configure hard-checks the `commoncpp` pkg-config module
        # (PKG_CHECK_MODULES commoncpp >= 6.2.2), but ucommon's recipe sets
        # pkg_config_name=ucommon so PkgConfigDeps only produces ucommon.pc.
        # Shim commoncpp.pc -> Requires ucommon + -lcommoncpp (the compat layer
        # ships inside the ucommon package).
        commoncpp_pc = os.path.join(self.generators_folder, "commoncpp.pc")
        if not os.path.exists(commoncpp_pc):
            with open(commoncpp_pc, "w", encoding="utf-8") as f:
                f.write(
                    "Name: commoncpp\n"
                    "Description: GNU Common C++ compat layer (provided by ucommon)\n"
                    "Version: 7.0.1\n"
                    "Requires: ucommon\n"
                    "Libs: -lcommoncpp\n"
                )
        # The conanbuild env does not auto-set PKG_CONFIG_PATH; point
        # configure's pkg-config at the generators folder.
        tc.configure_args.append("PKG_CONFIG_PATH={}".format(self.generators_folder))
        # SRTP is an optional crypto layer; upstream configure hard-fails when
        # neither libgcrypt nor OpenSSL is present. Disable it for this port.
        tc.configure_args.append("--disable-srtp")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        # Keep C++17 (profile cppstd) so ucommon's C++03 nullptr shim is skipped
        # even though ccrtp's WARN_FLAGS pass -ansi.  CXXFLAGS comes after
        # AM_CXXFLAGS on the compile line, so -std=c++17 wins.
        tc.extra_cxxflags.append("-std=c++17")
        tc.generate()
        # OHOS loader has no default search path for conan-cached shared libs.
        # configure's conftest runs compiled programs; without LD_LIBRARY_PATH
        # pointing at every dep lib dir it dies with "Error loading shared
        # library" (exit 127) -> configure aborts with "cannot run C compiled
        # programs". Same fix as aaphoto/0.45 (E064).
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path(
                    "LD_LIBRARY_PATH",
                    os.path.join(dep.package_folder, libdir),
                )
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        apply_conandata_patches(self)
        # Dependency packages ship libtool .la wrappers whose libdir field
        # points at the CI build's fake prefix ("//lib" / "/lib"), which does
        # not exist here.  libtool then fails the final link with "'//lib/...'
        # is not a valid libtool archive".  Remove the .la wrappers from the
        # dependency package dirs so libtool links the real .so/.a files.
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                la_dir = os.path.join(dep.package_folder, libdir)
                for la in glob.glob(os.path.join(la_dir, "*.la")):
                    os.remove(la)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream has no automake TESTS (make check is a no-op); run it anyway
        # for parity with the CI "make check" gate and record the result.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Remove libtool *.la wrappers (not usable by consumers).
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["ccrtp"]
        self.cpp_info.set_property("cmake_file_name", "ccrtp")
        self.cpp_info.set_property("cmake_target_name", "ccrtp::ccrtp")
        self.cpp_info.set_property("pkg_config_name", "ccrtp")
        # ccrtp's public headers include <commoncpp/*> and <ucommon/*>, so
        # consumers must link the ucommon target.  Declared explicitly as well
        # as via requirements(): CMakeDeps keeps ucommon's include dirs in the
        # transitive graph only when this is set.
        self.cpp_info.requires = ["ucommon::ucommon"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
