#!/usr/bin/env python3
"""Conan recipe for openhmd 0.3.0.1 — Free and Open Source API and drivers for
immersive technology (VR HMDs) — pure C.

上游：https://github.com/OpenHMD/OpenHMD （源码取 tag 0.3.0，适配版本号 0.3.0.1）

OHOS 适配要点（模式：上游 CMake 构建，零源码补丁）：
- 依赖：hidapi/0.14.0（制品仓已发布，libusb 后端，libhidapi-libusb.so）
- 上游 CMakeLists.txt 的 cmake_minimum_required(VERSION 3.1) 与 CI 的 CMake 4.x
  不兼容 —— 通过 CMAKE_POLICY_VERSION_MINIMUM=3.5 传参解决（CMake 官方推荐的
  旧项目兼容开关），无需补丁
- 上游 cmake/FindHIDAPI.cmake 为 module 模式查找（find_library + find_path），
  与 conan CMakeDeps 生成的 config 模式包（hidapi-config.cmake）不互通；实测真正被
  上游 CMakeLists 消费的是复数变量 ${HIDAPI_INCLUDE_DIRS} / ${HIDAPI_LIBRARIES}，
  单数 find_* 结果变量作为兼容兜底一并注入（CMake 会提示其未被使用），由此实现
  零补丁消费 conan hidapi 包
- 驱动源码 #include <hidapi.h> 为平铺路径，conan hidapi 包头文件位于
  include/hidapi/hidapi.h —— 注入的 include 目录自动探测到 .../include/hidapi
- openhmd 非系统同名库，保持上游默认静态库（BUILD_SHARED_LIBS 由 shared
  选项驱动）；上游对静态目标 PUBLIC 添加 -DOHMD_STATIC，本配方透传该默认
- 平台代码 src/platform-posix.c（pthread/clock_gettime）在 OHOS 上原生可用

0.3.0.1 相对 0.3.0 的改进（本版本新增，针对"适配完整性"）：
1. 【上游测试原样执行】build() 末尾在构建树内编译并运行上游
   tests/unittests 的全部 11 个用例（main.c/vec.c/quat.c/highlevel.c
   源码零修改），被测对象是本次刚构建出来的静态库；结果以
   HMBS_UPSTREAM_TEST_RESULT=<json> 上报，未全绿即 build 失败。
   依据：docs/ADAPTATION_GUIDE.md 适配检查清单要求 build() 末尾执行上游测试。
2. 【test_package 消费者用例】consume 侧 7 个用例全部只使用公共头文件
   include/openhmd.h（真实打开 dummy 驱动 HMD 设备，覆盖设备枚举/属性/
   控件元数据/着色器源码/姿态读写回环），不再"手工重声明内部符号 +
   复刻内部断言"——那种做法既不消费打包产物，也无法随上游实现演进。
"""

import json
import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    save,
)

# 上游 tests/unittests 是 autotools 目标（bin_PROGRAMS = unittests），不在
# 上游 CMake 构建图内 —— 用一个独立的小 CMake 工程原样编译这 4 个源文件，
# 链接本次构建出的 openhmd 库。源码零修改，头文件路径与上游 Makefile.am 等价。
UNITTESTS_CMAKELISTS = """\
cmake_minimum_required(VERSION 3.15)
project(openhmd_upstream_unittests C)

# OHMD_SOURCE_DIR: 上游源码树；OPENHMD_LIBRARY/OPENHMD_HIDAPI_LIBRARY: 被测库与依赖
if(NOT OHMD_SOURCE_DIR OR NOT OPENHMD_LIBRARY)
  message(FATAL_ERROR "OHMD_SOURCE_DIR / OPENHMD_LIBRARY 未设置")
endif()

add_executable(openhmd_upstream_unittests
    "${OHMD_SOURCE_DIR}/tests/unittests/main.c"
    "${OHMD_SOURCE_DIR}/tests/unittests/vec.c"
    "${OHMD_SOURCE_DIR}/tests/unittests/quat.c"
    "${OHMD_SOURCE_DIR}/tests/unittests/highlevel.c"
)
target_include_directories(openhmd_upstream_unittests PRIVATE
    "${OHMD_SOURCE_DIR}/include"
    "${OHMD_SOURCE_DIR}/src"
)
# 与上游静态构建一致（CMakeLists.txt 对静态目标 PUBLIC -DOHMD_STATIC）
target_compile_definitions(openhmd_upstream_unittests PRIVATE OHMD_STATIC)
target_link_libraries(openhmd_upstream_unittests PRIVATE
    "${OPENHMD_LIBRARY}"
    "${OPENHMD_HIDAPI_LIBRARY}"
    m pthread
)
"""


class OpenhmdConan(ConanFile):
    name = "openhmd"
    version = "0.3.0.1"
    description = (
        "Free and Open Source API and drivers for immersive technology, "
        "such as head mounted displays with built in head tracking (VR HMD)"
    )
    license = "BSL-1.0"
    homepage = "https://github.com/OpenHMD/OpenHMD"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    languages = "C"
    topics = ("vr", "hmd", "driver", "immersive", "opengl", "hidapi")

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # 上游 0.3.0 tests/unittests 用例数（ovec3f 4 + oquatf 5 + highlevel 2）。
    # 作为覆盖率护栏：上游测试集变化导致用例数不符时显式失败。
    UPSTREAM_TEST_CASES = 11
    UPSTREAM_TEST_SOURCES = ("main.c", "vec.c", "quat.c", "highlevel.c")
    HIDAPI_LIB_NAMES = (
        "libhidapi-libusb.so",
        "libhidapi-libusb.a",
        "libhidapi.so",
        "libhidapi.a",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("hidapi/0.14.0", transitive_headers=False)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32：OHOS 与 Linux 同族，判断必须用 in 而非 ==
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "openhmd 仅适配 Linux/OHOS（含鸿蒙 PC），当前 os=%s"
                % self.settings.os
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def _hidapi_include_dir(self):
        """上游驱动源码平铺 #include <hidapi.h>，需给出 hidapi.h 所在目录。"""
        hidapi = self.dependencies["hidapi"]
        root = hidapi.cpp_info.includedirs[0]
        if os.path.isfile(os.path.join(root, "hidapi.h")):
            return root
        nested = os.path.join(root, "hidapi")
        if os.path.isfile(os.path.join(nested, "hidapi.h")):
            return nested
        raise ConanException(
            "hidapi 包头文件未找到（hidapi.h）：已检查 %s 与 %s" % (root, nested)
        )

    def _find_file(self, root, names, what):
        """在目录树内查找首个匹配文件。"""
        for dirpath, _, filenames in os.walk(root):
            for name in names:
                if name in filenames:
                    return os.path.join(dirpath, name)
        raise ConanException("%s 未找到（在 %s 内查找 %s）" % (what, root, list(names)))

    def _hidapi_library(self):
        hidapi = self.dependencies["hidapi"]
        for libdir in hidapi.cpp_info.libdirs:
            try:
                return self._find_file(libdir, self.HIDAPI_LIB_NAMES, "hidapi 运行库")
            except ConanException:
                continue
        raise ConanException(
            "hidapi 链接库未找到（候选 %s），请检查 hidapi 包内容"
            % (list(self.HIDAPI_LIB_NAMES),)
        )

    def _runtime_libdirs(self):
        """收集依赖图（含传递依赖，如 hidapi→libusb）的库/可执行目录。

        测试可执行文件动态链接 hidapi（→libusb），运行时必须能解析这些
        .so，否则动态链接器报 "Error relocating ... symbol not found"。
        """
        dirs = []

        def walk(dep):
            dirs.extend(dep.cpp_info.libdirs)
            dirs.extend(dep.cpp_info.bindirs)
            for child in dep.dependencies.values():
                walk(child)

        for dep in self.dependencies.values():
            walk(dep)
        # 去重并保持顺序
        seen = set()
        unique = []
        for d in dirs:
            if d and d not in seen:
                seen.add(d)
                unique.append(d)
        return unique

    def build(self):
        apply_conandata_patches(self)
        hid_lib = self._hidapi_library()
        hid_inc = self._hidapi_include_dir()

        cmake = CMake(self)
        cmake.configure(
            variables={
                # 上游 CMake 3.1 最低版本 vs CMake 4.x：官方兼容开关
                "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
                "BUILD_SHARED_LIBS": bool(self.options.shared),
                # 上游 FindHIDAPI 为 module 模式：复数变量被上游 CMakeLists 消费，
                # 单数 find_* 结果变量为兼容兜底（实测 CMake 提示未使用，无副作用）
                "HIDAPI_LIBRARY": hid_lib,
                "HIDAPI_LIBRARIES": hid_lib,
                "HIDAPI_INCLUDE_DIR": hid_inc,
                "HIDAPI_INCLUDE_DIRS": hid_inc,
                # 示例程序需要 SDL/OpenGL，交叉编译环境不构建
                "OPENHMD_EXAMPLE_SIMPLE": False,
                "OPENHMD_EXAMPLE_OPENGL": False,
            }
        )
        cmake.build()
        self._run_upstream_unittests(hid_lib)

    def _run_upstream_unittests(self, hid_lib):
        """在构建树内编译并执行上游 tests/unittests（11 个用例，源码零修改）。

        被测对象是本配方刚构建出的 openhmd 静态库；任一用例失败即抛错，
        使 conan create 失败（CI 与本地 W3 同一咽喉）。
        """
        ut_dir = os.path.join(self.source_folder, "tests", "unittests")
        missing = [
            src
            for src in self.UPSTREAM_TEST_SOURCES
            if not os.path.isfile(os.path.join(ut_dir, src))
        ]
        if missing:
            raise ConanException(
                "上游测试源码缺失 tests/unittests/%s —— 上游版本可能变更，请更新适配"
                % ", ".join(missing)
            )

        openhmd_lib = self._find_file(
            self.build_folder, ("libopenhmd.a", "libopenhmd.so"), "openhmd 静态库"
        )

        proj_dir = os.path.join(self.build_folder, "upstream-unittests")
        build_dir = os.path.join(proj_dir, "build")
        save(self, os.path.join(proj_dir, "CMakeLists.txt"), UNITTESTS_CMAKELISTS)

        configure_args = [
            "-S",
            proj_dir,
            "-B",
            build_dir,
            "-DCMAKE_BUILD_TYPE=%s" % self.settings.build_type,
            "-DOHMD_SOURCE_DIR=%s" % self.source_folder,
            "-DOPENHMD_LIBRARY=%s" % openhmd_lib,
            "-DOPENHMD_HIDAPI_LIBRARY=%s" % hid_lib,
        ]
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.isfile(toolchain):
            configure_args.append("-DCMAKE_TOOLCHAIN_FILE=%s" % toolchain)

        self.run(" ".join(shlex.quote(a) for a in ["cmake"] + configure_args))
        self.run("cmake --build %s" % shlex.quote(build_dir))

        exe = self._find_file(
            build_dir, ("openhmd_upstream_unittests",), "上游测试可执行文件"
        )

        # 运行时依赖（hidapi → libusb 等动态库）需要可被动态链接器解析
        run_env = os.environ.copy()
        runtime_dirs = [os.path.dirname(hid_lib), *self._runtime_libdirs()]
        existing = run_env.get("LD_LIBRARY_PATH", "")
        run_env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [d for d in runtime_dirs + [existing] if d]
        )

        proc = subprocess.run(
            [exe],
            cwd=build_dir,
            env=run_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        output = proc.stdout or ""
        for line in output.splitlines():
            self.output.info("[upstream-tests] %s" % line)

        # 上游 main.c 每个用例打印一行 "<name> ok"，末尾打印 "all a-ok"
        case_lines = [
            line.strip()
            for line in output.splitlines()
            if line.strip().endswith("ok") and "all a-ok" not in line
        ]
        summary = {
            "source": "upstream tests/unittests (verbatim)",
            "total": self.UPSTREAM_TEST_CASES,
            "passed": len(case_lines),
            "failed": 0 if proc.returncode == 0 else 1,
            "exit_code": proc.returncode,
            "cases": case_lines,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(summary, ensure_ascii=False)
        )

        if proc.returncode != 0 or "all a-ok" not in output:
            raise ConanException(
                "上游测试未全部通过（退出码 %s）：\n%s"
                % (proc.returncode, output[-2000:])
            )
        if len(case_lines) != self.UPSTREAM_TEST_CASES:
            raise ConanException(
                "上游用例数不符：期望 %d，实测 %d（上游测试集可能已变更）"
                % (self.UPSTREAM_TEST_CASES, len(case_lines))
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "openhmd")
        self.cpp_info.set_property("cmake_target_name", "openhmd::openhmd")
        self.cpp_info.set_property("pkg_config_name", "openhmd")
        self.cpp_info.libs = ["openhmd"]
        if not self.options.shared:
            self.cpp_info.system_libs = ["m", "pthread"]
        # 上游公口头文件对 hidapi 无暴露，但静态库链接需要 hidapi
        self.cpp_info.requires = ["hidapi::hidapi"]
