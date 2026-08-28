#!/usr/bin/env python3
"""Conan recipe for libcotp 4.2.1 — HarmonyOS PC (OHOS aarch64) adaptation.

DT_NEEDED fix (no _BRIDGE, no patchelf, no LD_LIBRARY_PATH masking):
  - Upstream CMakeLists.txt line ~121 sets SOVERSION ${CMAKE_PROJECT_VERSION_MAJOR} (=4),
    producing SONAME=libcotp.so.4 on the build-tree shared library.
  - With a SONAME present, CMAKE_PLATFORM_USES_PATH_WHEN_NO_SONAME=1 (set by
    Platform/OHOS.cmake → Platform/Linux.cmake) does NOT trigger, so the linker
    writes the BARE name (libcotp.so.4) into the test ELF's DT_NEEDED instead of
    the file path (../libcotp.so) that appeared when no SONAME was set.
  - CMAKE_BUILD_RPATH points at the build lib output dir so the test executable can
    locate libcotp.so.4 at runtime.  This is runtime path resolution, NOT a
    workaround for a bad DT_NEEDED.

OpenSSL HMAC backend include/link fix:
  - Upstream reads the classic find_package(OpenSSL) ALL-CAPS result variables
    (OPENSSL_INCLUDE_DIR / OPENSSL_LIBRARIES); Conan's CMakeDeps config-mode only
    emits the mixed-case prefix (OpenSSL_INCLUDE_DIR).  We bridge this purely via
    the cmake_additional_variables_prefixes CMakeDeps property (no source patch).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, save

required_conan_version = ">=2.0.0"


class LibCotpRecipe(ConanFile):
    name = "libcotp"
    version = "4.2.1"
    description = "C library for generating TOTP/HOTP codes (RFC 6238/4226)"
    license = "Apache-2.0"
    url = "https://github.com/paolostivanin/libcotp"
    homepage = "https://github.com/paolostivanin/libcotp"
    topics = ("totp", "hotp", "otp", "2fa", "mfa")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    # ── configuration ──────────────────────────────────────────────

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("openssl/3.5.6", transitive_headers=True)

    def build_requirements(self):
        # Criterion is a test-only dependency — not a runtime requirement.
        self.test_requires("criterion/2.4.3")

    # ── source ─────────────────────────────────────────────────────

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── generate ───────────────────────────────────────────────────

    def _ohos_lld_runtime_fix(self):
        """Derive the SDK LLVM runtime lib dir from the actual compiler path and
        prepend it to LD_LIBRARY_PATH so the OHOS lld linker can find libxml2.so.16.

        - Only active for OHOS.
        - Derives the path dynamically from tools.build:compiler_executables —
          no hardcoded SDK version or currentUser absolute path in the recipe.
        - Preserves any pre-existing LD_LIBRARY_PATH.
        """
        if self.settings.os != "OHOS":
            return None
        compilers = self.conf.get("tools.build:compiler_executables", check_type=dict) or {}
        cc = compilers.get("c")
        if not cc:
            return None
        # cc is typically <sdk>/llvm/bin/clang → lib dir is <sdk>/llvm/lib
        bin_dir = os.path.dirname(cc)
        llvm_dir = os.path.dirname(bin_dir)
        lib_dir = os.path.join(llvm_dir, "lib")
        if not os.path.isdir(lib_dir):
            return None
        # Apply LD_LIBRARY_PATH directly to os.environ so the CMake/lld
        # subprocess inherits it during configure() and build().  Env scripts
        # produced by Environment.save_script() are NOT sourced by the CMake
        # build helper, so configure-time linker invocations would otherwise
        # fail with "Error loading shared library libxml2.so.16 ... lld".
        # Prepend lib_dir, preserving any pre-existing LD_LIBRARY_PATH.
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = (
            lib_dir + (os.pathsep + existing if existing else "")
        )
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        return env

    def generate(self):
        tc = CMakeToolchain(self)

        # Enable upstream Criterion tests.  Upstream CMakeLists.txt gates them
        # behind the `BUILD_TESTS` option (NOT CMake's standard BUILD_TESTING):
        #     option(BUILD_TESTS "Build base32 and cotp tests" OFF)
        #     if (BUILD_TESTS) enable_testing(); add_subdirectory(tests) endif()
        # We must build them so the test_cotp ELF is produced and we can verify
        # its DT_NEEDED references the bare SONAME (libcotp.so.4) rather than a
        # relative file path.
        tc.variables["BUILD_TESTS"] = True

        # Upstream CMakeLists.txt defaults HMAC_WRAPPER="gcrypt", which would
        # require libgcrypt as an extra dependency.  libcotp also supports the
        # openssl HMAC backend, which is already required (find_package(OpenSSL)).
        # Use openssl so no new runtime dependency is introduced.
        tc.variables["HMAC_WRAPPER"] = "openssl"

        # ── Platform/HarmonyOS.cmake — enable ELF SONAME emission ──────────
        # The OHOS-adapted Conan toolchain sets CMAKE_SYSTEM_NAME=HarmonyOS.
        # CMake (4.1) ships no Modules/Platform/HarmonyOS.cmake, so platform
        # detection falls through to the "Generic" platform, which leaves
        # CMAKE_SHARED_LIBRARY_SONAME_C_FLAG empty.  Without that flag, CMake
        # never passes -Wl,-soname,libcotp.so.4 to the linker, so:
        #   - libcotp.so carries NO DT_SONAME (verified: readelf -d shows none);
        #   - the upstream tests/CMakeLists links test_cotp against the bare
        #     build-tree libcotp.so target, and CMakePlatformUsesPath (the
        #     CMAKE_PLATFORM_USES_PATH_WHEN_NO_SONAME fallback) then records a
        #     relative *file path* (../libcotp.so) in the test ELF's DT_NEEDED
        #     instead of the bare SONAME — exactly the bug to fix.
        # The stock OHOS platform is represented by Modules/Platform/OHOS.cmake,
        # which simply does `include(Platform/Linux)`; Platform/Linux.cmake sets:
        #     CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,"
        #     CMAKE_PLATFORM_USES_PATH_WHEN_NO_SONAME 1
        # So we drop a Platform/HarmonyOS.cmake that mirrors OHOS.cmake into the
        # generators dir and prepend that dir to CMAKE_MODULE_PATH; CMake's
        # platform-file lookup (Modules/CMakeDetermineSystem.cmake) searches
        # ${CMAKE_MODULE_PATH}/Platform/<SYSTEM_NAME>.cmake before its built-in
        # Modules/Platform, so our file is picked up at project() time.  This is
        # pure CMake convention (no upstream source touched, no profile edit).
        gen_dir = self.generators_folder
        platform_dir = os.path.join(gen_dir, "Platform")
        os.makedirs(platform_dir, exist_ok=True)
        save(self, os.path.join(platform_dir, "HarmonyOS.cmake"),
            "# Conan-generated: alias HarmonyOS -> OHOS -> Linux platform rules\n"
            "# so that CMAKE_SHARED_LIBRARY_SONAME_C_FLAG (\"-Wl,-soname,\") and\n"
            "# CMAKE_PLATFORM_USES_PATH_WHEN_NO_SONAME are defined for HarmonyOS.\n"
            "include(Platform/OHOS)  # -> include(Platform/Linux)\n")
        # Prepend the generators dir (not Platform/) to CMAKE_MODULE_PATH; CMake
        # appends "/Platform" internally during platform detection.
        tc.cache_variables["CMAKE_MODULE_PATH"] = gen_dir + " ${CMAKE_MODULE_PATH}"

        # ── Inject find_package(Criterion) via CMAKE_PROJECT_cotp_INCLUDE ─────
        # Upstream's top-level CMakeLists.txt NEVER calls find_package(Criterion)
        # — only the tests/ subdirectory references it, and even there just as a
        # bare library/target name (`target_link_libraries(test_cotp PRIVATE
        # cotp criterion)`), NOT via find_package.  Consequently Conan's
        # CriterionTargets.cmake is never loaded, the `criterion`/`criterion::criterion`
        # imported targets are never created, and the bare `criterion` in
        # target_link_libraries() degrades to `-lcriterion` with no include dir
        # -> 'criterion/criterion.h' not found in the test sources.
        #
        # CMAKE_PROJECT_<name>_INCLUDE is a CMake variable that CMake auto-includes
        # immediately after the matching project() call (here project(cotp)) and
        # BEFORE any add_subdirectory()/find_package in the upstream file.  We drop
        # a tiny .cmake fragment that calls find_package(Criterion) (loading the
        # CMakeDeps-generated CriterionConfig.cmake + the cmake_target_aliases bare
        # `criterion` target declared above).  This is the standard CMake hook for
        # injecting setup without editing upstream sources.
        save(self, os.path.join(gen_dir, "conan_find_criterion.cmake"),
            "# Conan-generated: load CMakeDeps criterion targets so upstream's\n"
            "# bare `criterion` reference in tests/CMakeLists.txt resolves.\n"
            "find_package(Criterion REQUIRED CONFIG)\n")
        tc.variables["CMAKE_PROJECT_cotp_INCLUDE"] = \
            os.path.join(gen_dir, "conan_find_criterion.cmake")

        # Control library output location so we have a stable build-tree lib dir.
        lib_out = os.path.join(self.build_folder, "lib")
        tc.variables["CMAKE_LIBRARY_OUTPUT_DIRECTORY"] = lib_out

        # ── RPATH strategy: install-rpath-only, empty install RPATH ───────────
        # Goal: the produced ELF (libcotp.so.4.2.1 and the test_cotp test exe)
        # must carry NO DT_RPATH/DT_RUNPATH at all, so CMake's install step has
        # nothing to rewrite — no RPATH_CHANGE / RPATH_REMOVE in
        # cmake_install.cmake, and no Conan cache / currentUser absolute path
        # leaks into the final package lib.
        #
        #   CMAKE_BUILD_WITH_INSTALL_RPATH=ON  -> the build-tree ELF uses the
        #     INSTALL RPATH from the very start, so CMake never records a
        #     separate build-tree RPATH that it would later have to strip.
        #   CMAKE_INSTALL_RPATH=""             -> the install RPATH is empty,
        #     hence the build-tree ELF (built under install-rpath mode) already
        #     has no RPATH/RUNPATH.
        #
        # We deliberately do NOT set CMAKE_BUILD_RPATH / CMAKE_BUILD_RPATH_USE_ORIGIN
        # / CMAKE_SKIP_INSTALL_RPATH: those previously caused CMake to emit a
        # build-tree RPATH (pointing at the Conan build folder) and then a
        # RPATH_CHANGE entry in cmake_install.cmake to strip it on install.
        # The upstream Criterion tests find libcotp.so.4 via LD_LIBRARY_PATH
        # constructed in test() from build_folder/lib + criterion cpp_info.libdirs
        # (see below), so no ELF RPATH is needed for them either.
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        tc.variables["CMAKE_INSTALL_RPATH"] = ""

        tc.generate()

        deps = CMakeDeps(self)
        # Upstream calls find_package(OpenSSL REQUIRED) and
        # find_package(Criterion REQUIRED) with capital first letters.
        # CMakeDeps generates lowercase config filenames by default; fix the
        # cmake_file_name so upstream find_package resolves on case-sensitive FS.
        deps.set_property("openssl", "cmake_file_name", "OpenSSL")
        deps.set_property("criterion", "cmake_file_name", "Criterion")

        # ── OpenSSL legacy variable case mismatch ──────────────────────────
        # Upstream CMakeLists.txt (openssl HMAC branch) reads the classic
        # find_package(OpenSSL) result variables in ALL-CAPS:
        #     set(HMAC_INCLUDE_DIR ${OPENSSL_INCLUDE_DIR})
        #     set(HMAC_LIBRARIES   ${OPENSSL_LIBRARIES})
        # These are the names exported by CMake's BUILT-IN FindOpenSSL.cmake
        # (module mode).  Conan's CMakeDeps runs in CONFIG mode and emits the
        # same information under the mixed-case prefix matching cmake_file_name
        # ("OpenSSL"): OpenSSL_INCLUDE_DIR / OpenSSL_LIBRARIES.  CMake variables
        # are case-sensitive, so the all-caps upstream references resolved to
        # empty strings — whmac_openssl.c failed with 'openssl/conf.h' not
        # found and the cotp link line dropped libcrypto entirely.
        #
        # Fix (no upstream source modification, no injected fragment): ask
        # CMakeDeps to ALSO emit the legacy all-caps prefix by adding "OPENSSL"
        # to cmake_additional_variables_prefixes.  The generated OpenSSLConfig.cmake
        # then sets both OpenSSL_INCLUDE_DIR AND OPENSSL_INCLUDE_DIR (plus
        # _LIBRARIES / _INCLUDE_DIRS / _DEFINITIONS) from the same aggregated
        # cpp_info, so upstream's ${OPENSSL_INCLUDE_DIR}/${OPENSSL_LIBRARIES}
        # resolve to the Conan openssl package's include dir and the
        # OpenSSL::openssl imported target respectively.
        deps.set_property("openssl", "cmake_additional_variables_prefixes", ["OPENSSL"])

        # ── Criterion: upstream tests use the bare `criterion` target name ──
        # tests/CMakeLists.txt does:
        #     target_link_libraries(test_cotp PRIVATE cotp criterion)
        # CMakeDeps only creates the namespaced imported target
        # `criterion::criterion` (with INTERFACE_INCLUDE_DIRECTORIES pointing at
        # the criterion headers).  The bare `criterion` is not a target, so
        # CMake falls back to `-lcriterion` and the criterion include dir never
        # reaches test_cotp -> 'criterion/criterion.h' not found.  Add a bare
        # `criterion` ALIAS target (cmake_target_aliases) that links to
        # `criterion::criterion`, so the upstream bare name resolves to a real
        # imported target and its INTERFACE_INCLUDE_DIRECTORIES propagate.
        deps.set_property("criterion", "cmake_target_aliases", ["criterion"])
        deps.generate()

        # OHOS lld/libxml2 runtime fix (see _ohos_lld_runtime_fix).
        env = self._ohos_lld_runtime_fix()
        if env is not None:
            envvars = env.vars(self)
            envvars.save_script("ohos_lld_runtime")

    # ── build + upstream tests ────────────────────────────────────

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _build_test_runtime_env(self):
        """Construct a runtime Environment for the upstream Criterion tests so
        they can locate libcotp.so.4 and libcriterion at execution time WITHOUT
        relying on any DT_RPATH/DT_RUNPATH baked into the ELF.

        The library ELFs are built under CMAKE_BUILD_WITH_INSTALL_RPATH=ON with
        CMAKE_INSTALL_RPATH="" (see generate()), so they intentionally carry NO
        RPATH/RUNPATH at all.  The test executable (test_cotp) therefore resolves
        its runtime shared libraries purely through this environment:

          - prepend build_folder/lib  -> libcotp.so.4 (just built)
          - prepend criterion dependency cpp_info.libdirs -> libcriterion.so
          - any other transitive runtime libs provided by VirtualRunEnv
            (openssl libcrypto etc.) are still honored via VirtualRunEnv

        Paths are derived dynamically from Conan's dependency model and the
        build folder — never hardcoded to a Conan cache / currentUser path.
        Returns an Environment object (caller saves it to a script and passes
        the script name to CMake.test(env=...)).
        """
        env = Environment()

        # 1) build-tree libcotp.so.4 output dir (CMAKE_LIBRARY_OUTPUT_DIRECTORY).
        build_lib = os.path.join(self.build_folder, "lib")
        if os.path.isdir(build_lib):
            env.prepend_path("LD_LIBRARY_PATH", build_lib)

        # 2) criterion runtime lib dir(s) from cpp_info — dynamic, not hardcoded.
        try:
            crit = self.dependencies["criterion"]
        except KeyError:
            crit = None
        if crit is not None:
            for libdir in crit.cpp_info.libdirs:
                if libdir and os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)

        return env

    def test(self):
        # Run the REAL upstream Criterion test suite via ctest in the build tree.
        # This is separate from test_package and must not be replaced by it.
        #
        # The library ELF carries no RPATH (install-rpath-only, empty install
        # RPATH — see generate()), so the tests resolve libcotp.so.4 and
        # libcriterion via the LD_LIBRARY_PATH constructed in
        # _build_test_runtime_env() + any VirtualRunEnv-provided paths.
        test_env = self._build_test_runtime_env()
        envvars = test_env.vars(self)
        envvars.save_script("libcotp_upstream_tests")

        cmake = CMake(self)
        cmake.test(output_on_failure=True, env="libcotp_upstream_tests")

    # ── package ────────────────────────────────────────────────────

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "COTP")
        self.cpp_info.set_property("cmake_target_name", "COTP::cotp")
        self.cpp_info.libs = ["cotp"]
        self.cpp_info.requires = ["openssl::openssl"]
