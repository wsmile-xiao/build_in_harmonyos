#!/usr/bin/env python3
"""Conan recipe for libgit2-tools 1.9.6 — git2 command-line tools from libgit2.

libgit2-tools is the packaging name for the `git2` CLI utility that is
built from the official libgit2 source tree (same approach used by the
openSUSE/Debian "libgit2-tools" split packages). The upstream libgit2
CMake build produces:
  - libgit2.so (the library, consumed internally)
  - git2        (the CLI, statically linked against libgit2 objects)

This recipe builds the CLI (and the library it needs) from the official
libgit2 v1.9.6 tarball. The package delivers the `git2` executable.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save


class Libgit2ToolsConan(ConanFile):
    name = "libgit2-tools"
    version = "1.9.6"
    description = "git2 command-line tools built from libgit2 (git core library)"
    license = "GPL-2.0-only WITH GCC-exception-2.0"
    homepage = "https://libgit2.org/"
    url = "https://github.com/libgit2/libgit2"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libgit2-tools supports Linux and OHOS targets, got {self.settings.os}"
            )

    def requirements(self):
        # HTTPS transport + SHA backends
        self.requires("openssl/3.5.6.1")
        # zlib compression (bundle-free, use conan prebuilt)
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # OHOS: soname/rpath rules not provided by the OHOS SDK toolchain
        # files; provide them explicitly so shared library links work.
        if self.settings.os == "OHOS":
            rules = os.path.join(
                self.generators_folder, "ohos-cmake-rules.cmake"
            )
            save(
                self,
                rules,
                "\n".join(
                    (
                        'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                        'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                        'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                        'set(CMAKE_SHARED_LIBRARY_RPATH_LINK_C_FLAG "-Wl,-rpath-link,")',
                        'set(CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN "$ORIGIN")',
                    )
                )
                + "\n",
            )
            tc.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules

        # --- Dependency wiring (find_package overrides) ---
        openssl = self.dependencies["openssl"].cpp_info
        zlib = self.dependencies["zlib"].cpp_info

        tc.cache_variables["OPENSSL_ROOT_DIR"] = self.dependencies[
            "openssl"
        ].package_folder
        tc.cache_variables["OPENSSL_INCLUDE_DIR"] = openssl.includedirs[0]
        tc.cache_variables["OPENSSL_SSL_LIBRARY"] = os.path.join(
            openssl.libdirs[0], "libssl.a"
        )
        tc.cache_variables["OPENSSL_CRYPTO_LIBRARY"] = os.path.join(
            openssl.libdirs[0], "libcrypto.a"
        )
        tc.cache_variables["ZLIB_INCLUDE_DIR"] = zlib.includedirs[0]
        tc.cache_variables["ZLIB_LIBRARY"] = os.path.join(
            zlib.libdirs[0], "libz.a"
        )

        # --- libgit2 build options ---
        # Build the git2 CLI (default ON upstream) plus the library it
        # needs; skip docs/examples/fuzzers.
        tc.cache_variables["BUILD_CLI"] = True
        tc.cache_variables["BUILD_EXAMPLES"] = False
        tc.cache_variables["BUILD_FUZZERS"] = False
        tc.cache_variables["BUILD_TESTS"] = False
        # HTTPS transport via OpenSSL (conan prebuilt)
        tc.cache_variables["USE_HTTPS"] = "OpenSSL"
        # SHA1: keep upstream default (CollisionDetection / sha1dc) —
        # upstream explicitly warns against OpenSSL SHA1 (SHAttered).
        # SHA256 from OpenSSL (upstream default builtin is fine too, but
        # OpenSSL hardware acceleration is preferable).
        tc.cache_variables["USE_SHA256"] = "OpenSSL"
        # zlib from conan (not bundled)
        tc.cache_variables["USE_BUNDLED_ZLIB"] = False
        # SSH transport disabled: libgit2 upstream requires libssh2 >= 0.28
        # with newer APIs; keep the tool minimal and deterministic.
        tc.cache_variables["USE_SSH"] = False
        # No GSSAPI / SPNEGO on OHOS
        tc.cache_variables["USE_GSSAPI"] = "OFF"
        # No NTLM client (requires HTTPS stack internals)
        tc.cache_variables["USE_NTLMCLIENT"] = False
        # No iconv needed
        tc.cache_variables["USE_ICONV"] = False
        # Regex backend: leave upstream autodetect. On OHOS (musl, no
        # regcomp_l, no system PCRE) this resolves to the bundled PCRE2
        # backend ("builtin"), which is also the safest choice: the
        # musl regcomp backend's regfree() has no double-free guard
        # (upstream git_regexp_dispose for REGCOMP is a bare regfree),
        # which crashes upstream test userdiff's compile/dispose cycle.
        tc.cache_variables["USE_THREADS"] = True
        # Versioned soname
        tc.cache_variables["SONAME"] = True
        # Werror off for portability
        tc.cache_variables["ENABLE_WERROR"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()
        # libgit2-tools ships the CLI; also keep the library artifacts so
        # the package is self-contained (git2 is statically linked with the
        # libgit2 objects, the .so is a by-product of the same build).

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        # The library artifacts are a by-product; expose them as the
        # libgit2 library so consumers linking against this package work.
        self.cpp_info.libs = ["git2"]
