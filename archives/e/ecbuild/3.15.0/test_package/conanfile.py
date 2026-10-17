import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # ecbuild 既无库也无头，只有 CMake 模块 —— 传统的「编个 test.cpp 链一下」不适用。
        # 真正要验的是：**下游 find_package(ecbuild) 能不能找到并用起来**。
        # 这正是 eckit 的第一行硬依赖（find_package(ecbuild 3.7 REQUIRED)），
        # 装不出 config 文件的话 eckit 连 configure 都进不去。
        import os, textwrap
        pkg = self.dependencies["ecbuild"].package_folder
        d = self.build_folder
        with open(os.path.join(d, "CMakeLists.txt"), "w", encoding="utf-8") as f:
            f.write(textwrap.dedent("""
                cmake_minimum_required(VERSION 3.18)
                # ⚠️ find_package(ecbuild) 必须在 project() **之前**。
                # ecbuild 的机制是**重定义 CMake 的 project() 命令**
                # （cmake/ecbuild_project.cmake: `macro( project _project_name )`），
                # 在那个宏体里才 include(ecbuild_system)，进而加载 ecbuild_add_option 等全部宏。
                # 写在 project() 之后的话 find_package 会成功、宏却一个都没有——
                # 这正是本探针第一版踩的坑（find_package 通过但 ecbuild_add_option 不可用）。
                find_package(ecbuild 3.7 REQUIRED)
                # ecbuild 重定义的 project() **要求带 VERSION**，不给会 ecbuild_critical
                #   「CRITICAL - Please specify a version for project ...」
                project(ecbuild_probe VERSION 0.0.1 LANGUAGES CXX)
                if(NOT COMMAND ecbuild_add_option)
                  message(FATAL_ERROR "project() 之后 ecbuild_add_option 仍不可用——宏链没加载")
                endif()
                if(NOT COMMAND ecbuild_add_library)
                  message(FATAL_ERROR "ecbuild_add_library 不可用——宏链只加载了一半")
                endif()
                message(STATUS "ecbuild probe OK: version=${ecbuild_VERSION}")
            """).strip() + "\n")
        b = os.path.join(d, "probe-build")
        # -DDISABLE_OS_CHECK=ON：ecbuild 有 OS 白名单，HarmonyOS 不在里面，
        # 会 ecbuild_critical「ecBuild is untested for this operating system: [HarmonyOS]
        # -- refusing to continue」。上游自己在报错里给出了这个开关。
        self.run('cmake -S "%s" -B "%s" -DCMAKE_PREFIX_PATH="%s" -DDISABLE_OS_CHECK=ON'
                 % (d, b, pkg))

    def test(self):
        # configure 成功即证明 find_package(ecbuild) 与命令注入都正常。
        # 没有可执行产物要跑——这是构建期依赖，不是运行期库。
        self.output.info("ecbuild: find_package + ecbuild_add_option 可用（见上方 configure 输出）")
