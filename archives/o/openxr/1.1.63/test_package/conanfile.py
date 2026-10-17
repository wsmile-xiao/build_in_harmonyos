#!/usr/bin/env python3
"""Compile and run an openxr consumer against the OHOS package.

三类验证：

1. **产物可被真实消费** —— 用 CMake 的 ``find_package(OpenXR)`` 找到本包安装的
   ``lib/cmake/openxr/OpenXRConfig.cmake``，链接 ``OpenXR::openxr_loader`` 并
   真的运行。这同时验了：loader 的 version script（openxr-loader.map）没把
   导出符号裁掉、pkg-config/CMake 包配置可用。
2. **无运行时时的确定性行为** —— ``XR_RUNTIME_JSON``/XDG 都指向空目录时，
   ``xrCreateInstance`` 必须返回 ``XR_ERROR_RUNTIME_UNAVAILABLE``。这条只在
   manifest_file.cpp 的 ``#elif defined(XR_OS_LINUX)`` 分支被编译出来时才可能
   成立，也就是补丁 0002 真的生效了。
3. **鸿蒙特有：loader 能不能在 OHOS 上 dlopen 一个运行时** —— 这是本适配的
   核心（补丁把 HarmonyOS 拉进 Linux 分支，为的就是 dlopen/dlsym 那一套）。
   test_package 自己编一个 stub 运行时 .so，导出
   ``xrNegotiateLoaderRuntimeInterface``；被测程序把 ``XR_RUNTIME_JSON`` 指向
   一份合法的运行时清单，断言 stub 在被 dlopen 后**真的被调用**（stub 落一个
   哨兵文件，文件出现 = dlopen + dlsym + 调用链全通）。

   注意 loader 会把运行时的 negotiate 失败统一归一化成
   ``XR_ERROR_RUNTIME_UNAVAILABLE``（runtime_interface.cpp 的
   ``LoadRuntime`` 末尾），所以**退出码本身分不出**"没找到运行时"和
   "找到了但 negotiate 失败" —— 哨兵文件是这里唯一可靠的判据。
"""
import glob
import json
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OpenXrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 不吃 CMakeDeps：本包安装的是上游自己的 OpenXRConfig.cmake，把它所在
        # 的包根目录交给 find_package 即可（Conan 默认不会把依赖包目录塞进
        # CMAKE_PREFIX_PATH，除非用 CMakeDeps 生成 config）。
        openxr = self.dependencies["openxr"]
        if openxr.package_folder:
            tc.variables["CMAKE_PREFIX_PATH"] = openxr.package_folder
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        openxr = self.dependencies["openxr"]
        exe = self._find_one("test_openxr")
        stub = self._find_one("libstub_runtime.so")
        lib_dir = os.path.join(openxr.package_folder, "lib")

        if not can_run(self):
            self.output.info("cross-build detected: skipping the run step")
            return

        scratch = os.path.join(self.build_folder, "openxr-scratch")
        empty_xdg = os.path.join(scratch, "empty-xdg")
        os.makedirs(empty_xdg, exist_ok=True)
        marker = os.path.join(scratch, "stub-negotiated.txt")
        if os.path.exists(marker):
            os.remove(marker)

        runtime_json = os.path.join(scratch, "stub_runtime.json")
        with open(runtime_json, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "file_format_version": "1.0.0",
                    "runtime": {
                        "library_path": stub,
                        "name": "OHOS conan test stub runtime",
                    },
                },
                fh,
                indent=2,
            )

        prior = {
            key: os.environ.get(key)
            for key in ("LD_LIBRARY_PATH", "XR_RUNTIME_JSON")
        }
        lib_paths = [lib_dir] + [d for d in self._toolchain_libdirs() if os.path.isdir(d)]
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            lib_paths + ([prior["LD_LIBRARY_PATH"]] if prior["LD_LIBRARY_PATH"] else [])
        )
        # 故意留空：被测程序自己按场景 setenv，这里只保证继承来的值不会干扰
        os.environ.pop("XR_RUNTIME_JSON", None)
        try:
            self.run(
                '"{}" "{}" "{}" "{}"'.format(
                    exe, runtime_json, marker, empty_xdg
                ),
                env="conanrun",
            )
        finally:
            for key, value in prior.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    # ------------------------------------------------------------------ 工具

    def _find_one(self, basename):
        matches = [
            path
            for path in glob.glob(
                os.path.join(self.build_folder, "**", basename), recursive=True
            )
            if os.path.isfile(path)
        ]
        if not matches:
            raise FileNotFoundError(
                "no build artifact named {} under {}".format(basename, self.build_folder)
            )
        return matches[0]

    def _toolchain_libdirs(self):
        # libc++_shared.so 由工具链提供；OHOS 加载器没有兜底搜索路径
        return [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        ]
