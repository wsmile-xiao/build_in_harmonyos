#!/usr/bin/env python3
"""Conan recipe for MashMap 3.1.3 — a fast approximate aligner for long DNA sequences.

Upstream: https://github.com/marbl/MashMap (tag v3.1.3), C++17, CMake.

The release builds two executables, ``mashmap`` (minmer based approximate mapper)
and ``mashmap-align`` (segment aligner on top of it), and links GNU Scientific
Library plus zlib.  No C++ source change is needed for the OpenHarmony port:
the sources are plain POSIX/C++17 and the OHOS musl sysroot ships zlib.h,
libpthread.a and libm.a.  What does need work is the build description:

* ``target_link_libraries`` names the dependencies by bare link name (``gsl``,
  ``gslcblas``, ``z``).  That only resolves when the libraries happen to sit in
  the default system library search path; a cross build with the dependencies
  staged outside the sysroot also needs their include directories, so the
  recipe routes both through their config packages (patches/0001-*.patch).
* ``OPTIMIZE_FOR_NATIVE`` defaults to ON and appends ``-march=native``.  That
  flag describes the *build machine*, not the target, so it is turned off here
  the same way the FreeBSD port and the Gentoo ebuild turn it off.
* ``USE_HTSLIB`` is an optional htslib dependency and is left off, which keeps
  the graph at the two libraries upstream links unconditionally.
* The configure step shells out to ``git describe`` through
  ``scripts/generate_git_version.sh``.  A release tarball has no git metadata
  and the header it emits is not referenced anywhere in the sources, so the
  step is skipped instead of running a command that cannot succeed.
* Conan maps ``os=OHOS`` onto the CMake system name ``HarmonyOS``, which CMake
  does not know; the GNU system name plus the ``aarch64`` processor are stated
  explicitly instead (E092).

build() runs the project's own test procedure from
``.github/workflows/build-and-test.yml`` on the upstream yeast data set:
``mashmap -v``, the S. cerevisiae self mapping, and the coverage assertion of
``scripts/test.sh``.
"""

import collections
import os
import platform
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# Build machines that can execute aarch64 OpenHarmony binaries directly.
_NATIVE_MACHINES = ("aarch64", "arm64")

# Upstream test procedure, taken from .github/workflows/build-and-test.yml and
# INSTALL.txt.  Kept as named constants so the recipe and MANIFEST.yml cannot
# drift apart silently.
_UPSTREAM_REFERENCE = os.path.join("data", "scerevisiae8.fa.gz")
_UPSTREAM_VERSION_FLAG = "-v"
_UPSTREAM_VERSION_OUTPUTS = ("3.1.3", "v3.1.3")
# scripts/test.sh is invoked upstream with 0.92 as the minimum per sequence
# coverage threshold.
_UPSTREAM_COVERAGE_THRESHOLD = 0.92
# Upstream passes `$(nproc --all)`; a fixed count keeps the emulation run on an
# x86_64 builder inside a predictable wall clock.
_UPSTREAM_THREADS = 2


class MashmapConan(ConanFile):
    name = "mashmap"
    version = "3.1.3"
    description = "Fast approximate aligner for long DNA sequences (minmer + MinHash based)"
    license = "AGPL-3.0-only"
    homepage = "https://github.com/marbl/MashMap"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # GSL supplies the hypergeometric/binomial statistics behind the
        # significance filter; zlib supplies the gzopen/gzread layer that reads
        # the compressed references.
        self.requires("gsl/2.8", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1.2", transitive_headers=True, transitive_libs=True)

    def _emulation_needed(self):
        """True when the built binaries cannot run on this build machine.

        `cross_building()` is not a usable signal here: the OHOS profile is
        passed as both -pr:h and -pr:b, so Conan sees identical host and build
        settings even though the compiler targets aarch64 OpenHarmony from an
        x86_64 Linux builder.  The build machine CPU is the reliable signal.
        """
        return cross_building(self) or platform.machine().lower() not in _NATIVE_MACHINES

    def _run_target(self, command, **kwargs):
        if self._emulation_needed():
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to execute OpenHarmony binaries on this host"
                )
            command = f'"{qemu}" {command}'
        self.run(command, **kwargs)

    def generate(self):
        tc = CMakeToolchain(self)
        # -march=native describes the build machine, not the aarch64 OHOS
        # target: enabling it would bake host-only ISA extensions into a
        # package that has to run on every HarmonyOS PC.
        tc.variables["OPTIMIZE_FOR_NATIVE"] = "OFF"
        # Optional htslib dependency; keeping it off holds the graph at the two
        # libraries upstream links unconditionally.
        tc.variables["USE_HTSLIB"] = "OFF"
        # scripts/generate_git_version.sh runs `git describe`, which has no
        # answer inside a release tarball, and the header it emits is
        # unreferenced by every source file.
        tc.variables["SKIP_VERSION_FILE"] = "ON"
        if self.settings.os in ("Linux", "OHOS"):
            # E092: Conan maps os=OHOS onto the CMake system name "HarmonyOS",
            # which CMake does not know.  State the GNU system name instead.
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            # Conan arch is "armv8"; CMake expects "aarch64".
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()
        # Config packages for the staged dependencies. The toolchain file picks
        # their location up through conan_cmakedeps_paths.cmake, which is what
        # makes the find_package() calls introduced by the patch resolve.
        CMakeDeps(self).generate()
        # Runtime search paths for the staged gsl/zlib shared objects, needed
        # because build() executes the freshly linked binaries.
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream test procedure and gate on its real output.

        Three cases, in the order .github/workflows/build-and-test.yml runs
        them:

        1. ``mashmap -v`` has to print the release version.
        2. A full S. cerevisiae self mapping has to produce a PAF file.
        3. ``scripts/test.sh``'s per sequence coverage assertion, at its
           upstream threshold of 0.92.

        Case 3 is recomputed here instead of by running the script: the script
        shells out to ``bedtools``, a Linux-only x86_64 binary that is absent
        from the HarmonyOS toolchain and cannot be executed on the aarch64
        target.  The arithmetic it performs (merged query intervals of the PAF
        over the .fai sequence length, threshold 0.92) is reproduced exactly.
        """
        binary = os.path.join(self.build_folder, "bin", "mashmap")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(f"upstream test binary is missing: {binary}")

        # -- case 1: version banner -------------------------------------
        version_log = os.path.join(self.build_folder, "upstream_version.log")
        self._run_target(
            f'"{binary}" {_UPSTREAM_VERSION_FLAG} > "{version_log}" 2>&1',
            env="conanbuild",
        )
        with open(version_log, encoding="utf-8", errors="replace") as handle:
            # MashMap reports the version through the logger, which writes to
            # stderr, so the log holds both streams.  Every line is inspected
            # rather than only the last one, so a trailing diagnostic cannot be
            # mistaken for a wrong version string.
            lines = [line.strip() for line in handle.read().splitlines() if line.strip()]
        if not any(line in _UPSTREAM_VERSION_OUTPUTS for line in lines):
            raise ConanInvalidConfiguration(
                f"upstream case 1: `mashmap -v` printed {lines!r}, expected a line equal to "
                f"one of {_UPSTREAM_VERSION_OUTPUTS}"
            )
        self.output.info(f"[upstream 1/3] mashmap -v -> {_UPSTREAM_VERSION_OUTPUTS[0]}")

        # -- case 2: yeast self mapping ---------------------------------
        reference = os.path.join(self.source_folder, _UPSTREAM_REFERENCE)
        index = reference + ".fai"
        if not (os.path.isfile(reference) and os.path.isfile(index)):
            raise ConanInvalidConfiguration(
                f"upstream case 2: {reference} or its .fai index is missing"
            )
        paf = os.path.join(self.build_folder, "scerevisiae8.paf")
        map_log = os.path.join(self.build_folder, "upstream_map.log")
        self._run_target(
            f'"{binary}" -r "{reference}" -q "{reference}" --pi 95 -n 1 -Y \'#\''
            f' --threads {_UPSTREAM_THREADS} -o "{paf}" > "{map_log}" 2>&1',
            env="conanbuild",
        )
        if not os.path.isfile(paf) or os.path.getsize(paf) == 0:
            with open(map_log, encoding="utf-8", errors="replace") as handle:
                tail = handle.read()[-2000:]
            raise ConanInvalidConfiguration(
                f"upstream case 2: the mapping produced no PAF output; log tail:\n{tail}"
            )
        self.output.info(f"[upstream 2/3] yeast self mapping -> {os.path.getsize(paf)} bytes of PAF")

        # -- case 3: per sequence coverage ------------------------------
        coverages, records = self._paf_coverage(paf, index)
        unmapped = sorted(name for name, _ in coverages.items() if name not in records)
        if unmapped:
            raise ConanInvalidConfiguration(
                f"upstream case 3: {len(unmapped)} sequences received no mapping, "
                f"first few: {unmapped[:5]}"
            )
        worst_name, worst = min(coverages.items(), key=lambda item: item[1])
        if worst < _UPSTREAM_COVERAGE_THRESHOLD:
            raise ConanInvalidConfiguration(
                f"upstream case 3: coverage of {worst_name} is {worst:.4f}, "
                f"below the upstream threshold {_UPSTREAM_COVERAGE_THRESHOLD}"
            )
        self.output.info(
            f"[upstream 3/3] scripts/test.sh equivalent: {len(coverages)} sequences, "
            f"lowest coverage {worst:.4f} ({worst_name}) >= {_UPSTREAM_COVERAGE_THRESHOLD}"
        )

    @staticmethod
    def _paf_coverage(paf_path, fai_path):
        """Per sequence query coverage, the quantity scripts/test.sh asserts.

        Returns ``({sequence: coverage}, {sequence: mapped})``: the coverage of
        every sequence listed in the .fai (including the ones that never got a
        mapping, whose coverage is 0.0) and the set of sequences the PAF
        actually mentions.
        """
        lengths = {}
        with open(fai_path, encoding="utf-8") as handle:
            for line in handle:
                fields = line.rstrip("\n").split("\t")
                if len(fields) >= 2:
                    lengths[fields[0]] = int(fields[1])

        # PAF columns 1/4/5 are query name, query start and query end.
        spans = collections.defaultdict(list)
        mapped = set()
        with open(paf_path, encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                fields = line.rstrip("\n").split("\t")
                spans[fields[0]].append((int(fields[2]), int(fields[3])))
                mapped.add(fields[0])

        coverages = {}
        for name, length in lengths.items():
            covered = 0
            current = None
            for start, end in sorted(spans.get(name, [])):
                if current is None:
                    current = [start, end]
                elif start <= current[1]:
                    current[1] = max(current[1], end)
                else:
                    covered += current[1] - current[0]
                    current = [start, end]
            if current is not None:
                covered += current[1] - current[0]
            coverages[name] = covered / length if length else 0.0
        return coverages, mapped

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # OHOS/HMDFS: files landed by an install step (cmake.install, meson
        # install, ...) carry a kernel level "not executable" attribute that
        # makes every later exec fail with EPERM "Operation not permitted" —
        # not EACCES, so chmod is no help.  Re-copying the build-tree product
        # over the installed path creates a fresh inode without that attribute
        # while keeping the bytes identical.  Same pitfall and fix as
        # mmsd-tng 2.6.4 (meson flavour, knowledge draft
        # mmsd-tng-2.6.4-meson-install-executable-eperm).  Only the two
        # packaged executables are re-copied; this package ships no libraries,
        # whose install copies would have to stay untouched.
        bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        for name in ("mashmap", "mashmap-align"):
            source = os.path.join(self.build_folder, "bin", name)
            if not os.path.isfile(source):
                raise ConanInvalidConfiguration(f"built command is missing: {source}")
            copy(self, name, src=os.path.join(self.build_folder, "bin"), dst=bin_dst, keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
