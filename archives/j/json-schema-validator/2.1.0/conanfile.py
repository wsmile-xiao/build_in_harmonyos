#!/usr/bin/env python3
"""Conan recipe — json-schema-validator 2.1.0 (CMake).

JSON Schema validator for JSON for Modern C++ (nlohmann/json), draft-7.
CMake project producing library nlohmann_json_schema_validator plus the
json-schema-validate example executable.  Upstream ships a Conan 1.x recipe
(`from conans import ...`); this is the Conan 2.x port for OHOS.

Build uses bare cmake + OHOS SDK toolchain self-discovery (same pattern as
nlohmann_json / zstd / libxml2 recipes): os=OHOS makes CMakeToolchain map
CMAKE_SYSTEM_NAME to a value upstream cmake cannot consume, so we configure
directly with -DCMAKE_TOOLCHAIN_FILE=ohos.toolchain.cmake -DOHOS_ARCH=arm64-v8a.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class JsonSchemaValidatorConan(ConanFile):
    name = "json-schema-validator"
    version = "2.1.0"
    description = "JSON Schema validator for JSON for Modern C++ (nlohmann/json), draft-7"
    license = "MIT"
    homepage = "https://github.com/pboettch/json-schema-validator"
    url = ""
    topics = ("json", "schema", "validation", "draft7", "nlohmann-json")

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    exports_sources = "patches/*"

    def requirements(self):
        # R01 实证：ohpcd 可消费版本为 3.1.1 / 3.12.0，且 R01 已用 3.12.0 完成实际编译与
        # 行为验证（smoke test + 上游 JSON-Suite 36/36）。上游配方锁定的 3.7.3 未发布，禁止使用。
        self.requires("nlohmann_json/3.12.0")

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（① profile [conf] user_toolchain
        # ② 环境 OHOS_NDK_HOME ③ glob 设备/CI 的 SDK 布局），不依赖 CI profile host 段。
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for _c in list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else []):
            if _c and os.path.isfile(_c):
                return _c
        _g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def _llvm_ranlib(self, toolchain):
        # OHOS SDK llvm/bin 下只有 llvm-ar 没有 llvm-ranlib，而 ohos.toolchain.cmake 仍把
        # CMAKE_RANLIB 指过去；cmake 造静态库是 `<AR> qc ... && <RANLIB> <lib>`，.o 全编得动、
        # 一造 .a 就 ENOENT。返回 "" 表示不覆盖（SDK 自带就用它的）。
        import shutil
        sdk_bin = os.path.join(toolchain, "..", "..", "..", "llvm", "bin")
        cand = os.path.normpath(os.path.join(sdk_bin, "llvm-ranlib"))
        if os.path.isfile(cand):
            return ""
        return shutil.which("llvm-ranlib") or ""

    def _find_deps_preload(self):
        # 让依赖能被 find_package 找到。ohos.toolchain 用普通 set()（非 CACHE）设了
        # FIND_ROOT_PATH_MODE_PACKAGE=ONLY，命令行 cache 变量盖不住；CMAKE_PROJECT_TOP_LEVEL_INCLUDES
        # 在 toolchain 之后、project() 之后、第一个 find_package 之前执行，这时改才压得住。
        deps = [d.package_folder for _r, d in self.dependencies.items() if d.package_folder]
        if not deps:
            return ""
        path = os.path.join(self.build_folder, "ohos-find-deps.cmake")
        with open(path, "w", encoding="utf-8") as f:
            for d in deps:
                p = d.replace("\\", "/")
                f.write('list(APPEND CMAKE_FIND_ROOT_PATH "%s")\n' % p)
                f.write('list(APPEND CMAKE_PREFIX_PATH "%s")\n' % p)
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)\n")
        return path

    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        src = os.path.join(self.source_folder, "")
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",   # ohos.toolchain 64 位默认装 lib64/，须改回 lib
            # configure 期就给 INSTALL_PREFIX（GNUInstallDirs 在 configure 期把 FULL_* 算成绝对路径）
            '-DCMAKE_INSTALL_PREFIX="{}"'.format(self.package_folder),
            # 上游 cmake_minimum_required(VERSION 3.2) 与 CMake 4.x 不兼容（<3.5 已移除），
            # R01 已实测用该策略变量绕行，固化进配方
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            *(["-DBUILD_SHARED_LIBS={}".format(
                "ON" if self.options.get_safe("shared") else "OFF")]
              if self.options.get_safe("shared") is not None else []),
            # 库包：不装示例可执行，也不在配方内跑测试（上游测试在本地验证阶段独立执行）
            "-DBUILD_EXAMPLES=OFF",
            "-DBUILD_TESTS=OFF",
        ]
        _rl = self._llvm_ranlib(toolchain)
        if _rl:
            defs.append('-DCMAKE_RANLIB="{}"'.format(_rl))
        _pre = self._find_deps_preload()
        if _pre:
            defs.append('-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="{}"'.format(_pre))
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        self.run('cmake --build "{}"'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))

    def package_info(self):
        self.cpp_info.libs = ["nlohmann_json_schema_validator"]
        # 声明对 nlohmann_json 的 CMake 目标级依赖：上游公共头 json-schema.hpp 会
        # #include <nlohmann/json.hpp>，消费端必须拿到该依赖的 include 目录。
        # 缺此声明时 CMakeDeps 不会在 json-schema-validator 的 config 里 find_dependency
        # (nlohmann_json)，test_package 编译会 fatal error: 'nlohmann/json.hpp' not found。
        self.cpp_info.requires = ["nlohmann_json::nlohmann_json"]
        # 与上游自带的 CMake 导出一致（nlohmann_json_schema_validatorConfig.cmake /
        # 目标 nlohmann_json_schema_validator），下游 find_package(nlohmann_json_schema_validator)
        # 后可直接 target_link_libraries(... nlohmann_json_schema_validator::nlohmann_json_schema_validator)
        self.cpp_info.set_property("cmake_file_name", "nlohmann_json_schema_validator")
        self.cpp_info.set_property("cmake_target_name", "nlohmann_json_schema_validator::nlohmann_json_schema_validator")
        self.cpp_info.bindirs = []
