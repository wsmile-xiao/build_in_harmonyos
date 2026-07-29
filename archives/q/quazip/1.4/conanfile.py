import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.scm import Git


class QuazipConan(ConanFile):
    name = "quazip"
    version = "1.4"
    description = "Qt/C++ wrapper over minizip for accessing ZIP archives"
    homepage = "https://github.com/stachenov/quazip"
    license = "LGPL-2.1-or-later"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # zlib/1.3.1 is provided as a non-PIC static archive on OpenHarmony.
    # Keep QuaZip static so AArch64 linking does not require -fPIC from zlib.
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("qt5-qtbase/5.15.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"][self.version]
        urls = source["url"]
        if isinstance(urls, str):
            urls = [urls]

        for url in urls:
            try:
                get(self, url=url, sha256=source["sha256"], strip_root=True)
            except ConanException as error:
                self.output.warning(f"Failed to download QuaZip source from {url}: {error}")
            else:
                break
        else:
            self.output.warning(
                "Falling back to the checksum-pinned GitCode QuaZip mirror"
            )
            try:
                git = Git(self, self.source_folder)
                git.clone(url=source["git_mirror"], target=".")
                git.checkout(source["git_commit"])
            except ConanException as error:
                raise ConanException(
                    "Unable to download QuaZip source from GitHub or clone "
                    f"the GitCode mirror: {error}"
                ) from error

        apply_conandata_patches(self)

    def generate(self):
        deps = CMakeDeps(self)
        # QuaZip calls find_package(Qt5 COMPONENTS Core). Map the Conan
        # package name to that upstream CMake package.
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.set_property("zlib", "cmake_file_name", "ZLIB")
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.generate()

        tc = CMakeToolchain(self)
        moc_path = os.path.join(
            self.dependencies["qt5-qtbase"].package_folder, "bin", "moc"
        )
        if not os.path.isfile(moc_path):
            raise ConanException(
                "qt5-qtbase/5.15.2 does not provide the required bin/moc tool"
            )
        # CMakeDeps exports Qt5 libraries but not the Qt5::moc executable
        # target used by QuaZip's AUTOMOC configuration.
        tc.variables["CMAKE_AUTOMOC_EXECUTABLE"] = moc_path
        rcc_path = os.path.join(
            self.dependencies["qt5-qtbase"].package_folder, "bin", "rcc"
        )
        if not os.path.isfile(rcc_path):
            raise ConanException(
                "qt5-qtbase/5.15.2 does not provide the required bin/rcc tool"
            )
        # qztest compiles a .qrc file, but CMakeDeps does not export the
        # Qt5::rcc executable target used by AUTORCC.
        tc.variables["CMAKE_AUTORCC_EXECUTABLE"] = rcc_path
        tc.variables["QUAZIP_QT_MAJOR_VERSION"] = "5"
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["QUAZIP_ENABLE_TESTS"] = True
        tc.variables["QUAZIP_BZIP2"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        qt5_lib = os.path.join(
            self.dependencies["qt5-qtbase"].package_folder, "lib"
        )
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", qt5_lib)
        with env.vars(self).apply():
            self.run("ctest --output-on-failure", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["quazip1-qt5"]
        self.cpp_info.includedirs = [
            "include/QuaZip-Qt5-1.4",
            "include/QuaZip-Qt5-1.4/quazip",
        ]
        self.cpp_info.requires = ["qt5-qtbase::Qt5Core", "zlib::zlib"]
        self.cpp_info.set_property("cmake_file_name", "QuaZip-Qt5")
        self.cpp_info.set_property(
            "cmake_target_name", "QuaZip-Qt5::quazip1-qt5"
        )
