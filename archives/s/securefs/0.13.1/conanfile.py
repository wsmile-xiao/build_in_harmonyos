import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

required_conan_version = ">=2.0"


class SecurefsConan(ConanFile):
    name = "securefs"
    version = "0.13.1"
    description = (
        "A FUSE filesystem that transparently performs authenticated encryption "
        "of every file it stores (AES-GCM content encryption, Argon2id key derivation)"
    )
    license = "MIT"
    url = "https://github.com/netheril96/securefs"
    homepage = "https://github.com/netheril96/securefs"
    topics = ("fuse", "filesystem", "encryption", "cryptography")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)
        # OHOS 缺 POSIX 线程取消符号（知识库 E085），静态 libfuse.a 需要 no-op stub
        copy(self, "stubs/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # R32：OHOS 是独立的 os 枚举值，Linux 语义判断必须写成 in ("Linux", "OHOS")
        if self.settings.os in ("Linux", "OHOS"):
            # 上游固定 -DFUSE_USE_VERSION=28，即 FUSE 2.x 接口；
            # libfuse/2.9.9 已在制品仓，静态提供 libfuse.a + libulockmgr.a 与 fuse.h
            self.requires("libfuse/2.9.9")

    def source(self):
        get(self, url=self.conan_data["sources"]["url"],
            sha256=self.conan_data["sources"]["sha256"], strip_root=True)
        # 上游 release archive 不含子模块内容（gitlink），按固定 commit 补齐
        for entry in self.conan_data.get("submodules", {}).values():
            get(self, url=entry["url"], sha256=entry["sha256"],
                destination=os.path.join(self.source_folder, entry["destination"]),
                strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 4.0 不再兼容 cmake_minimum_required(<3.5)：上游自带的
        # CMakeLists 由 patches/0001 修复，但 vendored 子模块（external/argon2、
        # external/utf8proc）仍声明旧最低版本，这里统一放行（CMake < 4 忽略该变量）。
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if self.settings.os in ("Linux", "OHOS"):
            # 依赖路径一律取包私有前缀（Conan 依赖包目录），不碰共享的 /usr/local：
            # 上游的 FUSE 探测是 find_path/find_library(FUSE_INCLUDE_DIR/FUSE_LIBRARIES)，
            # 预先注入同名缓存变量即可命中，无需任何写死路径。
            dep = self.dependencies["libfuse"]
            info = dep.cpp_info.aggregated_components()
            tc.variables["FUSE_INCLUDE_DIR"] = info.includedirs[0]
            # OHOS 的 libc 未实现 POSIX 线程取消（E085），而静态 libfuse.a 的
            # fuse.o 与 fuse_loop_mt.o（nm 实测）引用 pthread_cancel /
            # pthread_setcancelstate → 链接期 undefined symbol。
            # 补一个 no-op stub 静态库参与链接（语义代价见 notes.md）。
            libs = self._libfuse_archives(info)
            libs.append(self._build_pthread_stub())
            tc.variables["FUSE_LIBRARIES"] = ";".join(libs)
        tc.generate()

    @staticmethod
    def _libfuse_archives(info):
        libs = []
        for libdir in info.libdirs:
            for name in info.libs:
                static_lib = os.path.join(libdir, "lib{}.a".format(name))
                if os.path.exists(static_lib):
                    libs.append(static_lib)
                    continue
                shared = sorted(glob.glob(os.path.join(libdir, "lib{}.so*".format(name))))
                if shared:
                    libs.append(shared[0])
        return libs

    def _build_pthread_stub(self):
        """编译 no-op 线程取消 stub（仅 OHOS 需要），返回静态库路径。

        编译器从 profile 的 tools.build:compiler_executables 取，不用裸 ${CC}
        /${AR} shell 变量（release worker 上为空 —— R33）。
        """
        stub_dir = os.path.join(self.source_folder, "stubs")
        src = os.path.join(stub_dir, "stub-pthread.c")
        obj = os.path.join(self.generators_folder, "stub-pthread.o")
        lib = os.path.join(self.generators_folder, "libohos_pthread_stub.a")
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c") or "clang"
        ar = compilers.get("ar") or "ar"
        self.run('"{}" -fPIC -c "{}" -I"{}" -o "{}"'.format(cc, src, stub_dir, obj))
        self.run('"{}" rcs "{}" "{}"'.format(ar, lib, obj))
        return lib

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not self.conf.get("tools.build:skip_test", default=False, check_type=bool):
            if can_run(self):
                # 直接调用 ctest：Conan 的 cmake.test(cli_args=...) 会把参数追加给
                # `cmake --build`（而不是 ctest），cmake 报 "Unknown argument -E"。
                # simple_test 需要真正挂载 FUSE 文件系统（/dev/fuse + 内核支持），
                # OHOS PC 上不可用 → 排除；余下 sec_test / cryptest / argon2_test
                # 三个上游测试实测通过（证据见 reports/test-report.md）。
                self.run(
                    'ctest --test-dir "{}" -E simple_test --output-on-failure --no-tests=error'.format(
                        self.build_folder
                    )
                )

    def package(self):
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.frameworkdirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
