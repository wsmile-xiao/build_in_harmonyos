#!/usr/bin/env python3
"""Conan test_package - sensorfw 0.15.2 consumer test (OpenHarmony PC / aarch64).

What this verifies
------------------
`conan create` compiles `test_sensorfw.cpp` against the *packaged* headers and
libraries and then executes it, so a broken package fails the build instead of
passing silently: a missing symbol, a stale library, a mis-packaged header
directory or a plugin that cannot be loaded at run time all surface here.

Six consumer cases are exercised (3 in C++, 3 in shell; see test.sh):

  consumer.api.types      datatype API round-trips (TimedXyzData / TimedUnsigned
                          / CompassData) - real objects, real fields
  consumer.api.qtmeta     XYZ QObject facade: direct getters, QObject::property()
                          through the Qt meta-object system, metaObject()->className()
  consumer.ohos.dlopen    **OHOS-specific**: every plugin shipped in
                          lib/sensord-qt5/ is dlopen()ed with RTLD_NOW and must
                          resolve. This is the direct regression test for patch
                          0004 (plugins carry their own DT_NEEDED on
                          libsensorfw-qt5) AND for patch 0005 (compasschain also
                          needs the four filter/chain modules it instantiates,
                          which live in the same plugin directory). On the
                          unpatched upstream sources this case necessarily fails
                          with
                            "Error relocating libXxx-qt5.so:
                             _ZN15InputDevAdaptorC2ERK7QStringi: symbol not found"
                          because the HarmonyOS/musl dlopen resolves undefined
                          symbols only inside the object's own DT_NEEDED closure.
  consumer.ohos.elfarch   packaged artefacts are AArch64 ELF
  consumer.ohos.packaging package contains zero symbolic links (an entry that is
                          a versioned .so symlink is treated as absent when the
                          loader resolves DT_NEEDED at start-up) while keeping the
                          full versioned SONAME layout as real files; the header
                          layout matches the upstream install rules exactly (flat
                          except for datatypes/); no qmake intermediate
                          (moc_predefs.h) leaks
  consumer.daemon.help    bin/sensorfwd really runs and prints its usage

Why test.sh wraps the run
-------------------------
1. Start-up DT_NEEDED resolution treats a versioned .so SYMBOLIC LINK as absent
   (the program fails with `Error loading shared library <name>`), while the same
   files as real files load fine - verified as a controlled A/B on one and the
   same file set. This is NOT a blanket "no symlinks" rule: the very same symlink
   loads fine through dlopen("<bare name>") and dlopen("<absolute path>") in fresh
   processes, so the limitation is specific to the start-up path.
   sensorfw's own artefacts are real files because the harmonyos-clang mkspec sets
   `QMAKE_LN_SHLIB = cp -f`, but the Qt dependency package ships libQt5*.so.5 as
   symlinks. test.sh therefore deref-copies the DT_NEEDED closure of the test
   binary and of every plugin into a private directory and runs against it - the
   same technique used by archives/y/yasw/0.6/test_package/test.sh. The search path
   for that closure includes the package's own plugin directory, because patch 0005
   makes libcompasschain-qt5.so depend on four modules that live there rather than
   in libdirs.
2. The consumer test binary takes the packaged plugin directory as argv[1], so a
   bare `ctest` entry could not work (see CMakeLists.txt).

File location: archives/s/sensorfw/0.15.2/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SensorfwTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # sensorfw declares Qt as a plain (non-transitive) requirement, exactly
        # like upstream's sensord-qt5.pc (empty "Requires:"), so the consumer has
        # to pull Qt in itself.  Two reasons this has to be explicit here:
        #   1. the packaged headers include <QDBusArgument>/<QObject>/<QString>,
        #      so the consumer compiles against Qt;
        #   2. sensorfw-config.cmake DOES emit find_dependency(qt) (CMakeDeps
        #      builds its dependency-name list from "consumer deps INTERSECT
        #      package's direct deps", independent of transitive_headers/libs),
        #      and qt/5.15.19.1 sets cmake_find_mode = "none" so no qt-config.cmake
        #      ever exists.  That call is resolved by the bridge in
        #      test_package/cmake/qt-config.cmake, which CMakeLists.txt puts FIRST
        #      on CMAKE_PREFIX_PATH.  Requiring qt here is still what supplies the
        #      real Qt5 targets (qt dependency -> Qt5::Core/Qt5::DBus) that the
        #      bridge and the packaged headers need.
        # Same pattern as archives/a/attica5/5.116.0/test_package/conanfile.py,
        # which requires qt5-qtbase itself.
        self.requires("qt/5.15.19.1")

    def layout(self):
        # cmake_layout() puts the build tree under test_package/build/<build_type>
        # and the generators under .../generators.  `build/` is covered by the
        # repository .gitignore, so conan create leaves no trace in the PR file
        # set (W2 atomicity / PF1 single-package gate).
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _qt_cmake_dir(self):
        """<qt package>/lib/cmake - the relocatable Qt5 config tree.

        qt/5.15.19.1 sets `cmake_find_mode = "none"` (it ships the real
        Qt5Config.cmake set itself), so CMakeDeps generates nothing for it and
        CMakeLists.txt has to be pointed at that directory explicitly.
        """
        qt = self.dependencies["qt"]
        if qt.package_folder is None:
            raise ConanException("qt package has no package folder")
        cmake_dir = os.path.join(qt.package_folder, "lib", "cmake")
        if not os.path.isdir(cmake_dir):
            raise ConanException(f"Qt5 cmake config dir not found: {cmake_dir}")
        return cmake_dir

    def _test_binary(self):
        """Absolute path of the consumer test executable built by CMake."""
        for directory in self.cpp.build.bindirs:
            binary = os.path.join(directory, "test_sensorfw")
            if os.path.isfile(binary):
                return binary
        raise ConanException(
            "test_sensorfw was not built into {}".format(self.cpp.build.bindirs)
        )

    # ── build / test ─────────────────────────────────────────────────────────

    def build(self):
        cmake = CMake(self)
        cmake.configure(
            variables={"SENSORFW_QT_CMAKE_DIR": self._qt_cmake_dir()},
        )
        cmake.build()

    def test(self):
        pkg = self.dependencies["sensorfw"]
        test_sh = os.path.join(self.recipe_folder, "test.sh")
        # Logs and the deref-relocation directory go to the (gitignored) build
        # folder, never into the archives/ source tree.
        log_dir = self.build_folder
        # test.sh needs bash, so this must NOT be read from CONFIG_SHELL: that
        # variable legitimately means "/bin/sh" in autoconf and in this
        # repository's gate environments (the CI profile and scripts/ohc-run.py
        # both export CONFIG_SHELL=/bin/sh, where /bin/sh is mksh), so picking
        # it up here would silently run the script under mksh.  That is exactly
        # how `conan-verify` G2 failed once: mksh rejected the script's bash
        # process substitution with `syntax error: unexpected '< '`.
        # Use a dedicated override, then fall back through the usual locations.
        bash = os.environ.get("SENSORFW_TEST_SHELL", "")
        if not bash:
            for candidate in ("/data/service/hnp/bin/bash", "/usr/bin/bash",
                              "/bin/bash", "/usr/local/bin/bash"):
                if os.path.isfile(candidate):
                    bash = candidate
                    break
        if not bash:
            raise ConanException("no bash interpreter found to run test.sh")
        # env="conanrun" -> VirtualRunEnv injects each dependency's
        # LD_LIBRARY_PATH (sensorfw lib dir, qt lib dir, libudev-zero).
        self.run(
            f'"{bash}" "{test_sh}" "{self._test_binary()}" '
            f'"{pkg.package_folder}" "{log_dir}"',
            env="conanrun",
        )
