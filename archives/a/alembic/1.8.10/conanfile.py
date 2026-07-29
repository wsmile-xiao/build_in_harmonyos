#!/usr/bin/env python3
"""Conan recipe for alembic 1.8.10 (CMake build system).

Alembic is an open-source computer graphics interchange framework developed by
Sony Pictures Imageworks and Industrial Light & Magic for storing and sharing
3D data (geometry, lights, cameras, etc.) across VFX/animation pipelines.

Build system: CMake (C++14)
Library output: libAlembic (the Abc* CLI tools are disabled via USE_BINARIES=OFF;
this adaptation ships the library only).

Dependencies:
  - Imath: the only hard dependency. Imath is NOT published to the OHOS Conan
    artifact repo, so its source is vendored and built as a standalone static
    library first (see _build_imath), then Alembic's own FIND_PACKAGE(Imath)
    resolves it via CMAKE_PREFIX_PATH. Both static libs (libAlembic + libImath)
    and both header trees (Alembic/ and Imath/) are packaged, so consumers link
    Alembic and Imath together.
  - HDF5/Arnold/PRMan/Maya/PyAlembic: optional, all disabled (defaults).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, patch, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AlembicConan(ConanFile):
    name = "alembic"
    version = "1.8.10"
    description = "Open-source computer graphics interchange framework for storing and sharing 3D data"
    license = "BSD-3-Clause"
    homepage = "https://github.com/alembic/alembic"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Imath is vendored from source (not published to the artifact repo);
        # no Conan dependency is declared.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Primary source: Alembic 1.8.10
        get(self, **self.conan_data["sources"][0], strip_root=True)
        # Vendored Imath source -> imath/ subdir (built standalone by _build_imath).
        get(self, **self.conan_data["sources"][1], strip_root=True,
            destination=os.path.join(self.source_folder, "imath"))

    @property
    def _imath_prefix(self):
        return os.path.join(self.build_folder, "imath-prefix")

    def generate(self):
        tc = CMakeToolchain(self)
        # Alembic uses its own ALEMBIC_SHARED_LIBS option (not BUILD_SHARED_LIBS).
        tc.variables["ALEMBIC_SHARED_LIBS"] = self.options.shared
        # Point Alembic's FIND_PACKAGE(Imath) at the vendored Imath install.
        tc.variables["CMAKE_PREFIX_PATH"] = self._imath_prefix
        # Disable optional components that need unavailable dependencies.
        tc.variables["USE_HDF5"] = False
        tc.variables["USE_ARNOLD"] = False
        tc.variables["USE_PRMAN"] = False
        tc.variables["USE_MAYA"] = False
        tc.variables["USE_PYALEMBIC"] = False
        # Keep the upstream test suite enabled (run via cmake.test() below).
        tc.variables["USE_TESTS"] = True
        # Ship the library only; the Abc* CLI tools lack a uniform --version
        # interface and are out of scope for this library adaptation.
        tc.variables["USE_BINARIES"] = False
        # Avoid -Werror breaking the build on toolchain warning differences.
        tc.variables["ALEMBIC_DEBUG_WARNINGS_AS_ERRORS"] = False
        tc.generate()

    def _build_imath(self):
        """Build the vendored Imath as a standalone static library.

        Imath is built with the same Conan-generated toolchain so the OHOS
        compiler/flags are applied. It is installed into a local prefix that
        Alembic's FIND_PACKAGE(Imath) then consumes via CMAKE_PREFIX_PATH.
        """
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        src = os.path.join(self.source_folder, "imath")
        bld = os.path.join(self.build_folder, "imath-build")
        prefix = self._imath_prefix

        # Apply vendored-Imath patches (e.g. avoid target_compile_features,
        # which CMake 4.x can't support for the unidentified OHOS clang).
        for p in self.conan_data.get("patches", []):
            patch(self, patch_file=p["patch_file"], base_path=src)

        self.run(
            'cmake -S "{src}" -B "{bld}" '
            '-DCMAKE_TOOLCHAIN_FILE="{tc}" '
            '-DCMAKE_INSTALL_PREFIX="{prefix}" '
            '-DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF'.format(
                src=src, bld=bld, tc=toolchain, prefix=prefix))
        self.run('cmake --build "{bld}" --parallel'.format(bld=bld))
        self.run('cmake --install "{bld}"'.format(bld=bld))

    def build(self):
        self._build_imath()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream official test suite (ctest, USE_TESTS=ON).
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, "include")

        # Bring the vendored Imath static lib + headers into the package.
        copy(self, "libImath*.a", src=os.path.join(self._imath_prefix, "lib"),
             dst=libdir, keep_path=False)
        copy(self, "*", src=os.path.join(self._imath_prefix, "include", "Imath"),
             dst=os.path.join(incdir, "Imath"), keep_path=False)

        # Normalize Imath's static lib name (drops the SOVERSION suffix) so
        # consumers link -lImath.
        if os.path.isdir(libdir):
            for fname in os.listdir(libdir):
                if fname.startswith("libImath-") and fname.endswith(".a"):
                    src = os.path.join(libdir, fname)
                    dst = os.path.join(libdir, "libImath.a")
                    if os.path.exists(dst):
                        os.remove(dst)
                    os.rename(src, dst)

        # The package is consumed through Conan's generated CMake config; remove
        # Alembic's/Imath's own installed CMake/pkg-config files which reference
        # the pre-rename library name and an external Imath that is not present.
        for cfg in ("cmake", "pkgconfig"):
            d = os.path.join(libdir, cfg)
            if os.path.isdir(d):
                shutil.rmtree(d)

    def package_info(self):
        self.cpp_info.libs = ["Alembic", "Imath"]
        if self.settings.os in ("Linux", "OHOS"):
            # Alembic links libm (EXTERNAL_MATH_LIBS) and pthreads
            # (Threads::Threads). Declare both so static-link consumers on
            # glibc < 2.34 (where pthread is a separate lib) resolve them;
            # on musl -lpthread is a harmless no-op.
            self.cpp_info.system_libs = ["m", "pthread"]
