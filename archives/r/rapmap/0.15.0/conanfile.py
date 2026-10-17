#!/usr/bin/env python3
"""Conan recipe - RapMap 0.15.0 (CMake, application).

RapMap is the transcriptome short-read mapper that salmon delegates its
quasi-mapping step to.  Upstream ships one executable, ``rapmap``, with two
subcommands (``quasiindex`` / ``quasimap``) plus a bash helper ``RunRapMap.sh``.

Three of upstream's dependencies are pulled in at build time by
``ExternalProject_Add`` -- two of them with ``curl -k -L`` straight from GitHub
(cereal 1.2.2 and a forked jemalloc 4.5.0, which is then bootstrapped through
``autogen.sh``) and one (libdivsufsort) from a tarball that is rebuilt by a
nested CMake invocation that does not inherit the cross-compilation toolchain.
All four real dependencies are published on the OHOS registry; this recipe
consumes cereal, libdivsufsort and zlib as Conan packages and the build never
touches the network.  jemalloc is the one deliberate exception: the packaged
5.3.0 binary links but segfaults every invocation here, so HarmonyOS PC runs
on the system allocator (patches 0001/0010 document the measurement).

Upstream sources are used unmodified except for ten portability patches:

* ``0001`` -- consume cereal / libdivsufsort / zlib-side dependencies from
  Conan, drop the three ``ExternalProject_Add`` download steps, and replace the
  jemalloc fallback with a configure-time STATUS message that names the
  allocator decision (nothing can silently reach the network either way).
* ``0002`` -- link suffix-array work through the ``divsufsort*`` imported
  targets and build only the scalar ksw2pp objects off x86 (the SIMD kernels are
  ``#ifdef __SSE2__`` no-ops there and ``-msse2`` / ``-msse4.1`` are x86-only).
* ``0003`` -- guard the x86 ``cpuid`` SIMD probe and the SSE alignment entry
  points by architecture, falling back to the scalar kernels upstream already
  provides for its own non-SIMD path.
* ``0004`` -- install ``scripts/RunRapMap.sh`` with an ``/usr/bin/env bash``
  shebang (this platform has no /bin/bash).
* ``0005`` -- replace the BSD ``ACCESSPERMS`` mkdir mode with the equivalent
  POSIX ``S_IRWXU|S_IRWXG|S_IRWXO``.
* ``0006`` -- use standard ``uint64_t`` instead of the BSD ``u_int64_t`` in
  BooPHF.hpp.
* ``0007`` -- select between the two POSIX ``strerror_r`` signatures by return
  type in zstr's strict_fstream.hpp.
* ``0008`` -- guard the x86 ``asm("pause")`` spin hint by architecture and use
  ``std::this_thread::yield()`` elsewhere.
* ``0009`` -- drop the ``-lgomp`` link that nothing references once patch 0001
  consumes the published libdivsufsort.
* ``0010`` -- link zlib through the ``zlib::zlib`` imported target; keep the
  system allocator, because the registry's jemalloc 5.3.0 segfaults every
  invocation here while the build without it is fully green.

The upstream regression suite is two CTest cases (``quasi_map_test``,
``quasi_map_test_ph``) that index and map the bundled ``sample_data`` corpus;
they run inside ``build()`` and need no network.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class RapmapConan(ConanFile):
    name = "rapmap"
    version = "0.15.0"
    description = (
        "RapMap - fast mapping of short reads to transcriptomes using "
        "quasi-mapping; provides the rapmap quasiindex/quasimap CLI"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/COMBINE-lab/RapMap"
    url = "https://github.com/COMBINE-lab/RapMap"
    topics = ("bioinformatics", "read-mapping", "quasi-mapping", "transcriptome", "indexing")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # Ships the four patches declared in conandata.yml alongside the recipe.
        export_conandata_patches(self)

    def requirements(self):
        # inflate/deflate of the stored index and of gzipped input
        self.requires("zlib/1.3.1")
        # header-only serialization of the index header (patch 0001 consumes it
        # through find_package(cereal) instead of fetching cereal 1.2.2)
        self.requires("cereal/1.3.2")
        # suffix-array construction: divsufsort() / divsufsort64()
        self.requires("libdivsufsort/2.0.1")
        # The allocator upstream routes through FAST_MALLOC_LIB stays out on
        # HarmonyOS PC: the registry's jemalloc/5.3.0 links but segfaults every
        # invocation (even --version, before any mapping code runs), while the
        # same build without it passes ctest 2/2 and the 27-assertion consumer
        # test.  System allocator; patches 0001/0010 carry the decision.

    def layout(self):
        cmake_layout(self)

    def source(self):
        # conandata.yml lists two GitHub-official endpoints for the identical
        # tarball (same sha256); Conan walks the list and only raises on the
        # last entry, so a single flaky endpoint cannot fail the build.
        #
        # The local filename must be pinned: the codeload endpoint (first, and
        # the fast one) ends in the bare tag name
        # ".../tar.gz/refs/tags/salmon-v0.15.0" with no archive suffix, so Conan
        # infers the archive type from that name, falls back to zipfile and dies
        # with "BadZipFile: File is not a zip file" even though the bytes
        # downloaded and matched the sha256.  Naming the file ".tar.gz" makes the
        # detection explicit instead of inferred.
        get(self, **self.conan_data["sources"],
            filename="RapMap-salmon-v0.15.0.tar.gz",
            retry=2, retry_wait=10, strip_root=True)

    def generate(self):
        # CMakeDeps writes the <pkg>-config.cmake files the patched CMakeLists
        # looks for (libdivsufsort / cereal) and the imported targets
        # divsufsort::divsufsort, divsufsort64::divsufsort64, cereal::cereal.
        # CMakeToolchain alone only produces conan_toolchain.cmake.
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # Upstream appends -march=native to CMAKE_CXX_FLAGS unless NO_NATIVE_ARCH
        # is set.  The package is distributed to other HarmonyOS aarch64 machines,
        # so pinning the ISA of the build host would produce an executable that
        # can SIGILL elsewhere.  Upstream already provides this switch, so we use
        # it instead of inventing a flag.
        tc.variables["NO_NATIVE_ARCH"] = True
        tc.generate()
        # VirtualRunEnv so the freshly linked executable can resolve the Conan
        # runtime libraries while the upstream CTest suite runs from build().
        VirtualRunEnv(self).generate(scope="build")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        # src/CMakeLists.txt registers exactly two CTest cases:
        #   quasi_map_test     -- rapmap quasiindex + rapmap quasimap
        #   quasi_map_test_ph  -- same with --perfectHash
        # Both drive the just-built binary over the corpus checked into
        # sample_data/ (transcripts.fasta, reads_1.fastq, reads_2.fastq) and
        # fail if the produced .sam is missing, so a green run is a real
        # index-and-map round trip, not a smoke echo.
        # The test scripts locate the binary through ${CMAKE_BINARY_DIR} and
        # resolve their corpus against TOPLEVEL_DIR, therefore the suite is run
        # from the CMake build directory where the generator placed the binary.
        self.run("ctest --output-on-failure --test-dir .",
                 cwd=self.build_folder, env="conanrun")

    def package(self):
        copy(self, "License.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Application package: it ships executables only, no consumable library.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []
        # rapmap links the pthread-based allocator and zlib statically; the
        # runtime libraries it does need come from the Conan run environment.
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m"]
