#!/usr/bin/env python3
"""Conan recipe — libodsstream 0.9.18 (PAPPSO ODS/TSV stream library).

libodsstream is the ODS (OpenDocument Spreadsheet) / TSV stream I/O library
of the PAPPSO suite (forgemia.inra.fr/pappso/libodsstream, upstream tag
upstream/0.9.18). It is dependency #2 of the libpappsomspp 0.11.26 chain
(liblzf → libodsstream → libpwizlite → libpappsomspp).

Upstream build facts:
  - CMake (C++20), Qt6 (Core/Gui/Xml + Core5Compat).
  - QuaZip: only used for ODS zip packaging (ziptsvoutputstream.cpp,
    odsdocreader/odsdocwriter). The ohpcd registry quazip packages
    (1.4/1.4.1) are Qt5-linked — their C++ ABI is INCOMPATIBLE with Qt6
    code because Qt6 moved OpenModeFlag into QIODeviceBase, changing the
    mangled names (QuaZipFile::open(QFlags<QIODevice::OpenModeFlag>) vs
    QuaZipFile::open(QFlags<QIODeviceBase::OpenModeFlag>)). Therefore this
    recipe vendors the QuaZip 1.4 sources (vendor-quazip/, same upstream
    tarball as quazip/1.4.1) and builds them against Qt6 during build()
    (fceux 2.6.6 vendored-minizip precedent).
  - Tools ods2tsv / tsv2ods are CLI products (R38: commands.json).
  - Upstream tests (Catch2): test/ has 3 test programs — test_ods (2
    TEST_CASE), test_tsv (2), test_zlib (1) → N=5 TEST_CASEs registered
    via add_test; enabled with -DMAKE_TEST=1. Catch2 3.16.0 from the
    ohpcd registry provides Catch2WithMain.

OHOS adaptations:
  - zlib/1.3.1 (registry binary) is a non-PIC static archive — cannot be
    linked into a shared lib on aarch64 (R_AARCH64_ADD_ABS_LO12_NC on
    z_errmsg); patch 0004 makes the Core target honour BUILD_SHARED_LIBS
    and the recipe default is static.
  - R32: settings.os judged with in ("Linux", "OHOS").
  - R33: compiler/toolchain from Conan CMakeToolchain only.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, mkdir


class LibodsstreamConan(ConanFile):
    name = "libodsstream"
    version = "0.9.18"
    description = "PAPPSO library to read and write ODS (OpenDocument Spreadsheet) files using Qt streams"
    license = "GPL-3.0-or-later"
    homepage = "https://forgemia.inra.fr/pappso/libodsstream"
    url = "https://forgemia.inra.fr/pappso/libodsstream"

    package_type = "library"
    topics = ("ods", "opendocument", "spreadsheet", "pappso", "tsv")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_tools": [True, False],
        "with_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_tools": True,
        "with_tests": True,
    }

    exports_sources = "patches/*", "vendor-quazip/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qt5compat/6.11.1")
        # NOTE: no quazip require — vendored Qt6 build (see module docstring).
        # zlib: linked by vendored QuaZip; registry binary is non-PIC static.
        self.requires("zlib/1.3.1")

    def build_requirements(self):
        if self.options.with_tests:
            self.tool_requires("catch2/3.16.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        src = self.conan_data["sources"][self.version]
        get(self, **src, strip_root=True)

    def _quazip_shim_dir(self):
        return os.path.join(self.build_folder, "quazip-shim")

    def _build_vendored_quazip(self, runtime_env):
        """Build the vendored QuaZip 1.4 sources as a Qt6-linked static
        library, then write a QuaZip-Qt6 config shim so the main build's
        find_package(QuaZip-Qt6) resolves to it."""
        vsrc = None
        for cand in (
            os.path.join(self.source_folder, "vendor-quazip"),
            os.path.join(self.build_folder, "vendor-quazip"),
        ):
            if os.path.isdir(os.path.join(cand, "quazip")):
                vsrc = cand
                break
        if vsrc is None:
            raise ConanException("vendor-quazip sources not found in source/build folder")
        bdir = os.path.join(self.build_folder, "vendor-quazip-build")
        mkdir(self, bdir)
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        with runtime_env.vars(self).apply():
            self.run(
                " ".join([
                    "cmake", f'-S "{vsrc}"', f'-B "{bdir}"', "-G", '"Unix Makefiles"',
                    f'-DCMAKE_TOOLCHAIN_FILE="{toolchain}"',
                    "-DCMAKE_BUILD_TYPE=Release",
                    f'-DCMAKE_INSTALL_PREFIX="{bdir}/install"',
                    "-DQUAZIP_INSTALL=OFF",
                    "-DBUILD_SHARED_LIBS=OFF",
                    "-DQUAZIP_BZIP2=OFF",
                    "-DQUAZIP_QT_MAJOR_VERSION=6",
                ]),
                env="conanbuild",
            )
            self.run(f'cmake --build "{bdir}" -- -j2', env="conanbuild")
        lib = os.path.join(bdir, "quazip", "libquazip1-qt6.a")
        if not os.path.isfile(lib):
            raise ConanException(f"vendored QuaZip library not produced: {lib}")
        shim = self._quazip_shim_dir()
        mkdir(self, shim)
        with open(os.path.join(shim, "QuaZip-Qt6Config.cmake"), "w") as f:
            f.write(
                "include(CMakeFindDependencyMacro)\n"
                "find_dependency(Qt6 COMPONENTS Core Core5Compat)\n"
                "add_library(QuaZip::QuaZip STATIC IMPORTED GLOBAL)\n"
                "set_target_properties(QuaZip::QuaZip PROPERTIES\n"
                f'  IMPORTED_LOCATION "{lib}"\n'
                f'  INTERFACE_INCLUDE_DIRECTORIES "{os.path.join(vsrc, "quazip")}"\n'
                '  INTERFACE_LINK_LIBRARIES "Qt6::Core;Qt6::Core5Compat;zlib::zlib"\n'
                ")\n"
            )
        with open(os.path.join(shim, "QuaZip-Qt5Config.cmake"), "w") as f:
            f.write('include("${CMAKE_CURRENT_LIST_DIR}/QuaZip-Qt6Config.cmake")\n')
        return shim

    def generate(self):
        # quazip_qt_compat.h includes <QtCore5Compat/QTextCodec> when
        # QT_VERSION >= 6 — inject qt5compat headers as a system include.
        qt5compat = self.dependencies.get("qt5compat")
        if qt5compat:
            q5c = os.path.join(qt5compat.package_folder, "include")
            existing = self.conf.get("tools.build:cxxflags")
            flags = list(existing) if isinstance(existing, list) else (
                [existing] if existing else []
            )
            flags.append(f"-isystem {q5c}")
            self.conf.define("tools.build:cxxflags", flags)

        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["MAKE_TEST"] = "ON" if self.options.with_tests else "OFF"
        # SONAME flag missing on OHOS (Platform/HarmonyOS.cmake absent in
        # CMake 4.1 — phonon 4.12.0 precedent).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_PLATFORM_USES_PATH_WHEN_NO_SONAME"] = "1"

        lines = []
        # qtbase MUST end up first on every path list: the qtbase-sql-dbus
        # package (when it appears transitively in the CI graph) ships an
        # empty-shelled Qt6 tree under its own lib/cmake + include dirs
        # that shadows the real Qt6 headers/configs on the include path
        # (CI test_zlib/test_ods/test_tsv compile failures). Because the
        # file below executes list(PREPEND ...) statements top-to-bottom,
        # emitting the qtbase lines LAST puts qtbase FIRST on every path.
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        qtbase_lines = [l for l in lines if qtbase and qtbase.package_folder in l]
        lines = [l for l in lines if l not in qtbase_lines]
        # remaining inserts below push quazip-shim/generators to the front;
        # re-append qtbase afterwards so it ends up in front of THEM too.
        lines.extend(qtbase_lines)
        if qt5compat:
            q5_pkg = qt5compat.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{q5_pkg}/lib/cmake")')
            lines.append(
                f'set(QT_ADDITIONAL_PACKAGES_PREFIX_PATH "{q5_pkg}/lib/cmake")'
            )
        lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
        catch2 = self.dependencies.build.get("catch2")
        if catch2:
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{catch2.package_folder}")')
        # CMakeDeps-generated configs (Qt6 etc.) live in the generators
        # folder; the vendored-QuaZip shim dir is written at build() start,
        # so reference its future location on CMAKE_PREFIX_PATH — the main
        # configure happens after the shim exists (build order: vendored
        # quazip first, then cmake.configure()).
        lines.insert(0, f'list(PREPEND CMAKE_PREFIX_PATH "{self._quazip_shim_dir()}")')
        lines.insert(0, f'list(PREPEND CMAKE_PREFIX_PATH "{self.generators_folder}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if str(self.settings.os) == "OHOS":
            runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        # Build the vendored Qt6-linked QuaZip first, then the main project.
        self._build_vendored_quazip(runtime_env)
        cmake = CMake(self)
        with runtime_env.vars(self).apply():
            cmake.configure()
            cmake.build()
            if self.options.with_tests:
                # cmake.test() would run ctest without our runtime_env
                # (upstream test/CMakeLists sets its own LD_LIBRARY_PATH
                # pointing only at the build dir); run ctest explicitly
                # with the dependency lib dirs on LD_LIBRARY_PATH.
                self.run(
                    f"ctest --test-dir \"{self.build_folder}\" --output-on-failure",
                    env="conanbuild",
                )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Ensure headers land under include/odsstream for consumers
        hdr_src = os.path.join(self.package_folder, "include", "odsstream")
        if not os.path.isdir(hdr_src):
            copy(self, "*.h", src=os.path.join(self.source_folder, "src", "odsstream"),
                 dst=hdr_src)
        # Ship the vendored Qt6-linked QuaZip static lib + headers + a
        # QuaZip-Qt6 config so consumers can resolve the QuaZip::QuaZip
        # target from OdsStreamTargets' INTERFACE_LINK_LIBRARIES.
        vsrc = None
        for cand in (
            os.path.join(self.source_folder, "vendor-quazip"),
            os.path.join(self.build_folder, "vendor-quazip"),
        ):
            if os.path.isdir(os.path.join(cand, "quazip")):
                vsrc = cand
                break
        if vsrc:
            lib = os.path.join(self.build_folder, "vendor-quazip-build",
                               "quazip", "libquazip1-qt6.a")
            if os.path.isfile(lib):
                copy(self, "libquazip1-qt6.a", src=os.path.dirname(lib),
                     dst=os.path.join(self.package_folder, "lib"))
            copy(self, "*.h", src=os.path.join(vsrc, "quazip"),
                 dst=os.path.join(self.package_folder, "include", "quazip"))
            cfg_dir = os.path.join(self.package_folder, "lib", "cmake", "QuaZip-Qt6")
            os.makedirs(cfg_dir, exist_ok=True)
            with open(os.path.join(cfg_dir, "QuaZip-Qt6Config.cmake"), "w") as f:
                f.write(
                    "# Compute the package prefix from this file's location\n"
                    "get_filename_component(QUAZIP6_PREFIX \"${CMAKE_CURRENT_LIST_FILE}\" PATH)\n"
                    "get_filename_component(QUAZIP6_PREFIX \"${QUAZIP6_PREFIX}\" PATH)\n"
                    "get_filename_component(QUAZIP6_PREFIX \"${QUAZIP6_PREFIX}\" PATH)\n"
                    "get_filename_component(QUAZIP6_PREFIX \"${QUAZIP6_PREFIX}\" PATH)\n"
                    "include(CMakeFindDependencyMacro)\n"
                    "find_dependency(Qt6 COMPONENTS Core Core5Compat)\n"
                    "add_library(QuaZip::QuaZip STATIC IMPORTED GLOBAL)\n"
                    "set_target_properties(QuaZip::QuaZip PROPERTIES\n"
                    '  IMPORTED_LOCATION "${QUAZIP6_PREFIX}/lib/libquazip1-qt6.a"\n'
                    '  INTERFACE_INCLUDE_DIRECTORIES "${QUAZIP6_PREFIX}/include/quazip"\n'
                    '  INTERFACE_LINK_LIBRARIES "Qt6::Core;Qt6::Core5Compat"\n'
                    ")\n"
                )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OdsStream")
        self.cpp_info.set_property("cmake_target_name", "OdsStream::Core")
        self.cpp_info.libs = ["odsstream"]
        self.cpp_info.requires = [
            "qtbase::qtbase", "qt5compat::qt5compat", "zlib::zlib"
        ]
        if self.options.with_tools:
            self.conf_info.define("user.libodsstream:ods2tsv", "bin/ods2tsv")
            self.conf_info.define("user.libodsstream:tsv2ods", "bin/tsv2ods")
