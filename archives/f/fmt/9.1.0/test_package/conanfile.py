import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    # CMakeDeps / VirtualRunEnv 自动生成；CMakeToolchain 在 generate() 中定制。
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # ★ os=OHOS 守卫：与 recipe 同理，把 CMAKE_SYSTEM_NAME 设为 "OHOS"
        # （而非 conan 默认的 "HarmonyOS"），对齐 cmake 的 Platform/OHOS.cmake。
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: 只验编译+链接")
            return
        # 显式拼 LD_LIBRARY_PATH：VirtualRunEnv 生成的 conanrunenv 在某些情况下
        # libdirs 为空（8.1.1 已记录），链接期 -Wl,-rpath 也不总起作用。
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        ldpath = os.pathsep.join(dict.fromkeys(libdirs))
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(
            f'{bash} -c \'export LD_LIBRARY_PATH="{ldpath}'
            f'${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"; ./test_probe\'',
            env="conanrun",
        )