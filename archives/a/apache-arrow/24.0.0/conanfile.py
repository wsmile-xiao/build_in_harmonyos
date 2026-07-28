from conan import ConanFile
from conan.tools.files import collect_libs, get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout


class ApacheArrowConan(ConanFile):
    name = "apache-arrow"
    version = "24.0.0"
    description = "Apache Arrow C++ — cross-language development platform for in-memory data"
    license = "Apache-2.0"
    homepage = "https://arrow.apache.org/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def configure(self):
        # Arrow 24.0.0 强制要求 C++20（SetupCxxFlags.cmake:151），
        # CI profile 默认 cppstd=17，必须覆盖。
        self.settings.compiler.cppstd = "20"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 最小化编译：只构建 C++ 核心库，关闭所有非核心模块
        # OHOS 处理器兼容：见 patches/0001-setupcxxflags-unknown-processor.patch
        # OHOS uses CMake's unknown Platform/HarmonyOS path, so Arrow's
        # VERSION/SOVERSION properties don't emit ELF SONAME by default. The
        # SONAME fix lives in patches/0002-buildutils-ohos-soname.patch.
        # Keep new-dtags for any remaining runtime path emitted by the linker.
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,--enable-new-dtags"
        # Avoid CMake package-registry leakage from Arrow's vendored dependencies
        # between shared/static builds in the same worker home.
        tc.variables["CMAKE_FIND_USE_PACKAGE_REGISTRY"] = "FALSE"
        tc.variables["CMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY"] = "FALSE"
        tc.variables["ARROW_RPATH_ORIGIN"] = "OFF"
        tc.variables["ARROW_INSTALL_NAME_RPATH"] = "OFF"
        # Avoid fetching xsimd from GitHub in restricted CI/device networks.
        # Core Arrow APIs remain available without NEON/runtime SIMD dispatch.
        tc.variables["ARROW_SIMD_LEVEL"] = "NONE"
        tc.variables["ARROW_RUNTIME_SIMD_LEVEL"] = "NONE"
        tc.variables["ARROW_BUILD_TESTS"] = "OFF"
        tc.variables["ARROW_WITH_PYTHON"] = "OFF"
        tc.variables["ARROW_WITH_JAVA"] = "OFF"
        tc.variables["ARROW_BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["ARROW_BUILD_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.variables["ARROW_IPC"] = "ON"
        tc.variables["ARROW_MIMALLOC"] = "OFF"
        tc.variables["ARROW_COMPUTE"] = "ON"
        tc.variables["ARROW_CSV"] = "ON"
        tc.variables["ARROW_FILESYSTEM"] = "ON"
        tc.variables["ARROW_JSON"] = "ON"
        # 关闭额外功能以加快编译
        tc.variables["ARROW_FLIGHT"] = "OFF"
        tc.variables["ARROW_DATASET"] = "OFF"
        tc.variables["ARROW_ORC"] = "OFF"
        tc.variables["ARROW_PARQUET"] = "OFF"
        tc.variables["ARROW_GANDIVA"] = "OFF"
        tc.variables["ARROW_CUDA"] = "OFF"
        tc.variables["ARROW_JEMALLOC"] = "OFF"
        # 外部依赖：CI 工位无法从 GitHub 下载源码，关掉不需要的
        # re2/zlib 等会通过 FetchContent 从 GitHub 拉取——CI 网络不可达
        tc.variables["ARROW_WITH_RE2"] = "OFF"
        tc.variables["ARROW_WITH_ZLIB"] = "OFF"
        tc.variables["ARROW_WITH_ZSTD"] = "OFF"
        tc.variables["ARROW_WITH_LZ4"] = "OFF"
        tc.variables["ARROW_WITH_SNAPPY"] = "OFF"
        tc.variables["ARROW_WITH_BROTLI"] = "OFF"
        tc.variables["ARROW_WITH_BZ2"] = "OFF"
        tc.variables["ARROW_WITH_UTF8PROC"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMakeLists.txt 在解压后的 cpp/ 子目录中
        import os
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "cpp"))
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "Arrow")
        self.cpp_info.set_property("cmake_target_name", "Arrow::arrow")
        alias = "Arrow::arrow_shared" if self.options.shared else "Arrow::arrow_static"
        self.cpp_info.set_property("cmake_target_aliases", [alias])

        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
