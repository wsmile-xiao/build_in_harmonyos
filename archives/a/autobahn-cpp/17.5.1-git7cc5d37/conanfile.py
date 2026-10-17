from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class AutobahnCppConan(ConanFile):
    name = "autobahn-cpp"
    version = "17.5.1-git7cc5d37"
    description = "Header-only WAMP client library for C++"
    license = "BSL-1.0"
    homepage = "https://github.com/crossbario/autobahn-cpp"
    url = homepage
    topics = ("wamp", "websocket", "boost", "asio", "header-only")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.90.0.4")
        self.requires("msgpack-cxx/7.0.0")
        self.requires("openssl/3.5.6")
        self.requires("websocketpp/0.8.2.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # The upstream CMake project only creates an INTERFACE target.  The
        # optional examples require a router and are not part of this package;
        # apply the source-level Asio compatibility patch before packaging.
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.hpp", src=self.source_folder + "/autobahn",
             dst=self.package_folder + "/include/autobahn")
        copy(self, "*.ipp", src=self.source_folder + "/autobahn",
             dst=self.package_folder + "/include/autobahn")
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=self.package_folder + "/licenses")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "autobahn-cpp")
        self.cpp_info.set_property("cmake_target_name", "autobahn-cpp::autobahn-cpp")
        self.cpp_info.set_property("pkg_config_name", "autobahn-cpp")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
