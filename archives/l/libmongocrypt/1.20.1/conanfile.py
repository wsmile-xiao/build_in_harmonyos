#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


def _u(path):
    return str(path).replace("\\", "/")


class LibmongocryptConan(ConanFile):
    name = "libmongocrypt"
    version = "1.20.1"
    description = ("MongoDB Client-Side Field Level Encryption (CSFLE) core library: "
                   "key management, FLE1/FLE2 payload crypto and KMS protocol handling")
    license = "Apache-2.0"
    homepage = "https://github.com/mongodb/libmongocrypt"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # 制品仓已发布 (R36)。非 Apple/Windows 平台 libmongocrypt 只有 OpenSSL 一种
        # 后端 (CMakeLists.txt: set (MONGOCRYPT_CRYPTO OpenSSL))。
        self.requires("openssl/3.5.6")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # codeload URL 的末段是 tag 名（无 .tar.gz 后缀），conan get() 会误判成 zip
        # （azure-core-cpp / cdda2wav 同款坑），用 filename 显式声明归档类型。
        get(self, strip_root=True, filename="libmongocrypt-1.20.1.tar.gz",
            **self.conan_data["sources"]["libmongocrypt"])
        get(self, destination="mongo-c-driver", strip_root=True,
            filename="mongo-c-driver-2.3.3.tar.gz",
            **self.conan_data["sources"]["mongo-c-driver"])

    def _sources_ready(self):
        src = self.source_folder
        return (os.path.isfile(os.path.join(src, "src", "mongocrypt.h"))
                and os.path.isfile(os.path.join(src, "mongo-c-driver", "CMakeLists.txt")))

    def generate(self):
        tc = CMakeToolchain(self)
        # CMakeToolchain 不写 CMAKE_SYSTEM_NAME，CMake 就用 uname -s 的 "HarmonyOS" 当系统名，
        # 而 Modules/Platform/ 里只有 OHOS.cmake（内容是 include(Platform/Linux)），没有
        # HarmonyOS.cmake → 平台语义整体不加载（"System is unknown to cmake"，退出码仍为 0），
        # 其中 CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG 为空，build-tree 可执行文件就不写 RPATH，
        # 上游 ctest 里链了本库 .so 的用例全部 "Error loading shared library"。显式给 OHOS 拼法。
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        # 源码来自 tarball, 上游用 git describe 推版本, 这里必须显式给。
        tc.variables["BUILD_VERSION"] = self.version
        tc.variables["ENABLE_STATIC"] = True
        tc.variables["BUILD_TESTING"] = True
        tc.variables["ENABLE_ONLINE_TESTS"] = False
        # 上游 vendored 的 IntelRDFPMathLib20U2 在 architecture.h 里没有 OHOS/aarch64 分支
        # （#error "Architecture must be specified"），只能关掉 Decimal128 扩展支持。
        tc.variables["MONGOCRYPT_ENABLE_DECIMAL128"] = False
        tc.variables["MONGOCRYPT_MONGOC_DIR"] = _u(os.path.join(self.source_folder, "mongo-c-driver"))
        ossl = _u(self.dependencies["openssl"].package_folder)
        # CMakeLists.txt 用 include (FindOpenSSL) 模块而非 config 包, 只认 OPENSSL_ROOT_DIR。
        tc.variables["OPENSSL_ROOT_DIR"] = ossl
        tc.generate()

    def build(self):
        if not self._sources_ready():
            # conan create 在 cache 已有 s/ 时偶发跳过 source(), 补一次避免空树。
            self.source()
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游官方套件：ctest 跑 test-mongocrypt（347 个 INSTALL_TEST 用例）+ mlib/dec128 + kms。
        # 再显式把构建目录交给动态链接器：CMake 写的 RUNPATH 只覆盖同一 build 目录，
        # 而 conan 的 build 目录会被复用/搬迁，给出绝对路径可保证 ctest 不依赖 CMake 的 RPATH 行为。
        libdir = _u(self.build_folder)
        self.run('LD_LIBRARY_PATH="%s" ctest --output-on-failure' % libdir,
                 cwd=self.build_folder, env="conanbuild")

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        src = os.path.join(self.source_folder, "src")
        gen = os.path.join(self.build_folder, "src")
        for header in ("mongocrypt.h", "mongocrypt-compat.h"):
            copy(self, header, src, os.path.join(self.package_folder, "include"))
        # mongocrypt-config.h / mongocrypt-export.h 是 CMake configure_file /
        # generate_export_header 的产物, 不在 tarball 里。
        for header in ("mongocrypt-config.h", "mongocrypt-export.h"):
            copy(self, header, gen, os.path.join(self.package_folder, "include"))
        libdir = os.path.join(self.package_folder, "lib")
        # mongocrypt_static 需要同一次构建里的 libbson/kms_message 静态库才能被链接,
        # 这两者是上游 add_subdirectory 出来的构建产物, 不单独成包。
        # conan 的 copy() 用 fnmatch 匹配「相对 src 的完整相对路径」，子目录里的产物必须写成
        # */名字，只写文件名会静默漏拷（CMakeDeps 之后报 Library '...' not found in package）。
        copy(self, "libmongocrypt-static.a", self.build_folder, libdir, keep_path=False)
        copy(self, "libmongocrypt.so*", self.build_folder, libdir, keep_path=False)
        copy(self, "*/libbson-static-for-libmongocrypt.a", self.build_folder, libdir, keep_path=False)
        copy(self, "*/libkms_message-static.a", self.build_folder, libdir, keep_path=False)

    def package_info(self):
        static_libs = ["mongocrypt-static", "bson-static-for-libmongocrypt", "kms_message-static"]
        if self.options.shared:
            self.cpp_info.libs = ["mongocrypt"]
        else:
            self.cpp_info.libs = static_libs
            self.cpp_info.defines = ["MONGOCRYPT_STATIC_DEFINE"]
        self.cpp_info.requires = ["openssl::openssl"]
        if self.settings.os in ("Linux", "OHOS", "Android"):
            self.cpp_info.system_libs = ["dl", "pthread", "m"]
