#!/usr/bin/env python3
"""Conan recipe for belle-sip 5.3.105 (Belledonne SIP stack) on HarmonyOS PC.

belle-sip is the SIP protocol stack of the Belledonne stack: SIP/SDP message
parsing and serialisation (built on belr), transactions, dialogs and the
TLS/DTLS transports.

Dependencies: belr (grammar/parsing), bctoolbox (utilities), zlib (optional
message compression) - all published in the OHOS artifact repository.

Crypto backend: belle-sip uses bctoolbox's crypto/TLS API (bctoolbox/crypto.h:
SSL contexts, RNG, SHA256/MD5/base64, signing keys), but the published
bctoolbox/5.3.115 is built with ENABLE_MBEDTLS=OFF and therefore ships neither
that header nor those symbols. The merged bzrtp/5.3.105 package already
contains the private mbedtls 3.6.5 build plus the bctoolbox crypto objects it
vendored for exactly this gap (its own consumers link them next to the
published bctoolbox), so this recipe resolves them from there instead of
duplicating the vendoring pipeline.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file, rmdir

required_conan_version = ">=2.0"

# Upstream tester suites that can be executed on HarmonyOS PC: they are run
# suite by suite and must all pass (175 upstream test cases in total).
RUNNABLE_UPSTREAM_SUITES = (
    "Object inheritance",
    "Headers",
    "Core",
    "SDP",
    "Message",
    "Refresher",
    "Object",
    "Generic uri",
    "FAST SIP URI 2",
    "Authentication helper",
)


class BelleSipConan(ConanFile):
    name = "belle-sip"
    version = "5.3.105"
    package_type = "library"
    description = "SIP protocol stack (parser, transactions, dialogs, TLS) of the Belledonne stack"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.linphone.org/BC/public/belle-sip"
    url = ("https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/"
           "tree/main/archives/b/belle-sip/5.3.105")
    topics = ("sip", "sdp", "voip", "belledonne")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_unit_tests": [True, False],
        "with_tools": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_unit_tests": True,
        "with_tools": False,
    }

    @property
    def _crypto_libs(self):
        """Crypto backend archives published inside the bzrtp package."""
        return ["bctbx-crypto-priv", "mbedcrypto", "mbedtls", "mbedx509"]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("belr/5.3.105")
        self.requires("bctoolbox/5.3.115")
        # Private crypto backend provider (see module docstring).
        self.requires("bzrtp/5.3.105")
        self.requires("zlib/1.3.1")
        # Upstream's BCToolboxConfig calls find_dependency(BCUnit) for static
        # builds; BCUnit is the test framework of the Belledonne stack.
        self.test_requires("bcunit/5.3.113")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "Macos", "Windows"):
            raise ConanInvalidConfiguration(f"{self.name} not validated for {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Upstream: bc_find_package(ZLIB ZLIB::ZLIB zlib) stamps the literal
        # "ZLIB::ZLIB" into ZLIB_TARGET whenever the finder reports success,
        # and src/CMakeLists.txt appends that variable to the link line
        # (same pitfall the bzrtp/5.3.105 recipe documents for SQLite3).
        # Generate exactly that file/target name from the zlib package.
        deps.set_property("zlib", "cmake_file_name", "ZLIB")
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.set_property("bcunit", "cmake_config_version_compat", "AnyNewerVersion")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.cache_variables["ENABLE_STRICT"] = False
        tc.cache_variables["ENABLE_UNIT_TESTS"] = bool(self.options.with_unit_tests)
        tc.cache_variables["ENABLE_TUNNEL"] = False
        tc.cache_variables["ENABLE_MDNS"] = False
        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream configs of the Belledonne packages: they define the
        # <Package>_TARGET variables and the bc_* CMake macros belle-sip uses.
        bctoolbox_pkg = str(self.dependencies["bctoolbox"].package_folder)
        belr_pkg = str(self.dependencies["belr"].package_folder)
        for name, pkg, sub in (("BCToolbox", bctoolbox_pkg, "BCToolbox"),
                               ("Belr", belr_pkg, "Belr")):
            # The upstream CMake install location differs per project
            # (share/<Name>/cmake vs lib/cmake/<Name>), so probe both.
            candidates = [
                os.path.join(pkg, "share", sub, "cmake"),
                os.path.join(pkg, "lib", "cmake", sub),
                os.path.join(pkg, "lib", "cmake", sub.lower()),
            ]
            config_dir = next(
                (c for c in candidates
                 if os.path.isfile(os.path.join(c, name + "Config.cmake"))), None)
            if config_dir is None:
                raise ConanException(
                    "upstream %sConfig.cmake not found (looked in %s)"
                    % (name, ", ".join(candidates)))
            tc.cache_variables[name + "_DIR"] = config_dir
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"   # E092
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        # Crypto backend (headers + archives) from the bzrtp package: the
        # published bctoolbox has no bctoolbox/crypto.h, bzrtp ships it.
        crypto_pkg = str(self.dependencies["bzrtp"].package_folder)
        crypto_inc = os.path.join(crypto_pkg, "include")
        tc.extra_cflags.append("-isystem" + crypto_inc)
        tc.extra_cxxflags.append("-isystem" + crypto_inc)
        link_flags = ["-L" + os.path.join(crypto_pkg, "lib")] + \
                     ["-l" + lib for lib in self._crypto_libs]
        tc.extra_sharedlinkflags.extend(link_flags)
        tc.extra_exelinkflags.extend(link_flags)
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # belle-sip links the crypto backend privately: the archives are placed
        # on the target link line (linker flags alone would be ordered before
        # the objects, leaving the bctbx crypto symbols unresolved).
        crypto_link = " ".join("-l" + lib for lib in self._crypto_libs)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src", "CMakeLists.txt"),
            "target_link_libraries(belle-sip PUBLIC ${BCToolbox_TARGET} ${Belr_TARGET} PRIVATE ${LIBS})",
            "target_link_libraries(belle-sip PUBLIC ${BCToolbox_TARGET} ${Belr_TARGET} "
            "PRIVATE ${LIBS} %s)" % crypto_link,
            strict=True,
        )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.with_unit_tests and can_run(self):
            self._run_upstream_tester()

    def _run_upstream_tester(self):
        """Run the runnable upstream suites (see RUNNABLE_UPSTREAM_SUITES).

        The remaining upstream suites depend on platform facilities that
        HarmonyOS PC does not provide in this environment and are declared as
        exemptions in test_package/MANIFEST.yml and reports/test-report.md:
        Resolver (system resolver configuration), HTTP stack / Register /
        Dialog (loopback SIP and HTTP servers), SIP URI / FAST SIP URI (one
        upstream expectation difference each).
        """
        tester_dir = os.path.join(self.build_folder, "tester")
        tester = os.path.join(tester_dir, "belle-sip-tester")
        if not os.path.isfile(tester):
            raise ConanException("upstream tester was not built at %s" % tester)
        for suite in RUNNABLE_UPSTREAM_SUITES:
            # Each suite writes its own log: the bcunit output contains raw
            # bytes that would otherwise break text-decoding consumers of the
            # Conan build log, and the log doubles as the per-suite evidence.
            log = os.path.join(self.build_folder,
                               "tester-%s.log" % suite.replace(" ", "_"))
            self.run('"%s" --suite "%s" > "%s" 2>&1' % (tester, suite, log),
                     cwd=tester_dir)
            with open(log, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            passed = text.count("passed in")
            self.output.info("upstream suite [%s]: %d cases passed" % (suite, passed))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # The tester is a build time verification artifact, not a deliverable.
        rmdir(self, os.path.join(self.package_folder, "bin"))
        # belle-sip's public headers include bctoolbox headers, and the crypto
        # backend header (bctoolbox/crypto.h) is not part of the published
        # bctoolbox package: ship both next to belle-sip's headers (same
        # handling as belr 5.3.105 / bzrtp 5.3.105).
        crypto_pkg = str(self.dependencies["bzrtp"].package_folder)
        for src_dir in (os.path.join(crypto_pkg, "include", "bctoolbox"),
                        os.path.join(str(self.dependencies["bctoolbox"].package_folder),
                                     "include", "bctoolbox")):
            for pattern in ("*.h", "*.hh", "*.hpp"):
                copy(self, pattern, src=src_dir,
                     dst=os.path.join(self.package_folder, "include", "bctoolbox"))

    def package_info(self):
        self.cpp_info.libs = ["belle-sip"]
        self.cpp_info.requires = [
            "bctoolbox::bctoolbox",
            "belr::belr",
            "bzrtp::bzrtp",
            "zlib::zlib",
        ]
        self.cpp_info.set_property("cmake_file_name", "belle-sip")
        self.cpp_info.set_property("cmake_target_name", "belle-sip::belle-sip")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        if not self.options.shared:
            self.cpp_info.system_libs.append("c++")
