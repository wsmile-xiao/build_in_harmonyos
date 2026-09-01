import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import download, apply_conandata_patches, export_conandata_patches


class SparseMapConan(ConanFile):
    name = "tsl-sparse-map"
    version = "0.6.2"
    package_type = "header-library"
    license = "MIT"
    homepage = "https://github.com/Tessil/sparse-map"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    description = ("sparse-map — C++ fast memory-efficient hash map and "
                   "hash set (sparse hashing, header-only)")
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "sparse-map-0.6.2.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xzf sparse-map-0.6.2.tar.gz --no-same-owner || true")
        self.run("cp -a sparse-map-0.6.2/. . && rm -rf sparse-map-0.6.2")

    def build_requirements(self):
        # 上游测试用 Boost.Test（unit_test_framework）——ohpcd boost 包无该
        # 编译库，改用 header-only 模式（included/unit_test.hpp）编译测试；
        # boost 包仅提供头文件（tool_requires 即可）
        self.tool_requires("boost/1.84.0")

    def build(self):
        # 上游测试（tests/——Boost.Test：main.cpp + custom_allocator_tests +
        # policy_tests + popcount_tests + sparse_map_tests + sparse_set_tests）
        # ——编译并运行，回填真实通过率
        # OHOS 适配（同 hopscotch-map）：
        # 1) ohpcd boost 无 libboost_unit_test_framework 编译库——用 header-only
        #    （included/unit_test.hpp——main.cpp 的 include 替换为 included 版）
        # 2) OHOS libc 缺 pthread_setcancelstate/pthread_cancel（Boost 内部用）
        #    ——写 stub 头 + -include 注入（同 hopscotch-map）
        if can_run(self):
            apply_conandata_patches(self)
            boost_pkg = self.dependencies.build["boost"].package_folder
            boost_inc = os.path.join(boost_pkg, "include")
            main_cpp = os.path.join(self.source_folder, "tests", "main.cpp")
            src = open(main_cpp).read()
            if "included/unit_test.hpp" not in src:
                src = src.replace("#include <boost/test/unit_test.hpp>",
                                  "#include <boost/test/included/unit_test.hpp>")
                open(main_cpp, "w").write(src)
            stub = os.path.join(self.source_folder, "pthread_stub.h")
            with open(stub, "w") as f:
                f.write("#ifndef PTHREAD_STUB_H\n#define PTHREAD_STUB_H\n"
                        "#include <pthread.h>\n"
                        "static inline int pthread_setcancelstate("
                        "int st, int *old) { (void)st; "
                        "if (old) *old = PTHREAD_CANCEL_ENABLE; return 0; }\n"
                        "static inline int pthread_cancel(pthread_t t) "
                        "{ (void)t; return 0; }\n"
                        "static inline int pthread_setcanceltype("
                        "int ty, int *old) { (void)ty; "
                        "if (old) *old = PTHREAD_CANCEL_DEFERRED; return 0; }\n"
                        "#endif\n")
            test_dir = os.path.join(self.source_folder, "tests")
            inc_dir = os.path.join(self.source_folder, "include")
            out = os.path.join(self.source_folder, "unit_tests")
            self.run(
                f"/data/service/hnp/bin/clang++ -std=c++17 "
                f"-I{inc_dir} -I{boost_inc} -include {stub} "
                f"{test_dir}/main.cpp {test_dir}/custom_allocator_tests.cpp "
                f"{test_dir}/policy_tests.cpp {test_dir}/popcount_tests.cpp "
                f"{test_dir}/sparse_map_tests.cpp "
                f"{test_dir}/sparse_set_tests.cpp -o {out} -pthread",
                cwd=self.source_folder)
            # 运行并统计（Boost.Test 输出 'Running N test cases... No errors
            # detected'）
            self.run(f"TMPDIR=/data/storage/el2/base/cache {out}",
                     cwd=self.source_folder)

    def package(self):
        # header-only——安装 include/tsl/ 头文件（4 个）
        inc_dst = os.path.join(self.package_folder, "include")
        shutil.copytree(os.path.join(self.source_folder, "include", "tsl"),
                        os.path.join(inc_dst, "tsl"))

    def package_id(self):
        # header-only——所有 settings 组合产出相同包内容
        self.info.clear()

    def package_info(self):
        # header-only——无可链接库，仅头文件
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        # 镜像上游 CMake 包名/目标名：find_package(tsl-sparse-map) +
        # tsl::sparse_map（上游 CMakeLists 定义了 tsl::sparse_map alias）
        self.cpp_info.set_property("cmake_file_name", "tsl-sparse-map")
        self.cpp_info.set_property("cmake_target_name", "tsl::sparse_map")
        self.cpp_info.set_property("cmake_build_modules", [])
