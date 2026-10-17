from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir
import os


class CnatsConan(ConanFile):
    name = "cnats"
    version = "3.13.0"
    description = "NATS C client library (nats.c) for the NATS messaging system"
    license = "Apache-2.0"
    url = "https://github.com/nats-io/nats.c"
    homepage = "https://nats.io"
    topics = ("nats", "messaging", "client")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.0.16")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 CMakeLists 用 if(UNIX)/elseif(WIN32) 分支定义安装目录与平台源码，
        # OHOS 默认的 CMAKE_SYSTEM_NAME=HarmonyOS 会使 UNIX=FALSE 走错分支
        # （install 无 DESTINATION、unix 平台头缺失）；OHOS musl 提供 librt.a，
        # Linux 分支的 -lrt 可正常链接。
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["NATS_BUILD_WITH_TLS"] = True
        tc.variables["NATS_BUILD_EXAMPLES"] = False
        tc.variables["NATS_BUILD_STREAMING"] = False
        tc.variables["NATS_BUILD_USE_SODIUM"] = False
        tc.variables["NATS_BUILD_LIB_SHARED"] = bool(self.options.shared)
        tc.variables["NATS_BUILD_LIB_STATIC"] = not bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = False
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 上游 pkg-config/CMake 导出按 -lnats 与 Threads::Threads 书写，与 Conan
        # 管理的产物名（静态为 nats_static）及依赖传播方式不一致，查找统一交给 CMakeDeps。
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cnats")
        self.cpp_info.set_property("pkg_config_name", "libnats")
        self.cpp_info.libs = ["nats"] if self.options.shared else ["nats_static"]
        # 制品仓 openssl/3.0.16 配方为包级声明（libs=ssl+crypto，无组件），
        # 必须用包级引用；组件式 openssl::ssl 会报 Component not found。
        self.cpp_info.requires = ["openssl::openssl"]
