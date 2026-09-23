import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class GtkSourceView3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cannot run test binary in this environment")
            return
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_gtksourceview")
        # OHOS 运行环境补充：
        # - harfbuzz（gtk 传递依赖）NEEDED libc++_shared.so，conan 依赖图
        #   不携带该库，由系统 /system/lib64 提供（glade test 同款）
        # - 测试本身不打开 display（gtk_init_check + 纯逻辑 API）
        run_env = Environment()
        if self.settings.os == "OHOS":
            run_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        run_env.vars(self).save_script("gsv_test_env")
        self.run(bin_path, env=["conanrun", "gsv_test_env"],
                 cwd=self.build_folder)
