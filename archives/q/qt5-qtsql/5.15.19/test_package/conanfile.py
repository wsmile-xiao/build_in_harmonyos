import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Qt5QtsqlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5/5.15.19")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 运行期环境：扫描全部依赖包的真实目录（含 .so 的 lib 才收，
        # 规避空缓存包）——qt5 主包/本包/传递闭包全覆盖
        libdirs = []
        for _, dep in self.dependencies.items():
            if not dep.package_folder:
                continue
            for sub in ("lib", "lib64", "bin"):
                d = os.path.join(dep.package_folder, sub)
                if os.path.isdir(d) and any(f.endswith(".so") or ".so." in f for f in os.listdir(d)):
                    libdirs.append(d)
        # QT_PLUGIN_PATH 须指向 plugins 根（Qt 自拼 sqldrivers 子路径）
        plugin_dir = None
        for _, dep in self.dependencies.items():
            if not dep.package_folder:
                continue
            cand = os.path.join(dep.package_folder, "plugins")
            if os.path.isdir(os.path.join(cand, "sqldrivers")):
                plugin_dir = cand
                break
        exe = os.path.join(self.cpp.build.bindirs[0], "test_qtsql")
        ld = ":".join(dict.fromkeys(libdirs))
        # L0d：self.run 真实执行（export 内联环境最可靠）
        self.run(
            f'export LD_LIBRARY_PATH="{ld}" && '
            f'export QT_PLUGIN_PATH="{plugin_dir or ""}" && '
            f'"{exe}"')
        print("Qt5Sql + QSQLITE :memory: test: PASS")
