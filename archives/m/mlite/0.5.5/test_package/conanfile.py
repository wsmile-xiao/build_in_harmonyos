import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MliteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 上游 src/src.pro:17 `QT = core dbus`：测试程序需要 Qt5Core/Qt5DBus 头与库
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def _ohos_runtime_dir(self):
        """OHOS 工具链运行库目录（libc++_shared.so 等）：<clang>/../lib/aarch64-linux-ohos"""
        if str(self.settings.os) != "OHOS":
            return None
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = compilers.get("cpp") or compilers.get("cxx")
        if not compiler:
            return None
        compiler_dir = os.path.dirname(os.path.realpath(compiler))
        runtime_dir = os.path.join(compiler_dir, "..", "lib", "aarch64-linux-ohos")
        return runtime_dir if os.path.isdir(runtime_dir) else None

    def build(self):
        cmake = CMake(self)
        variables = {}
        runtime_dir = self._ohos_runtime_dir()
        if runtime_dir:
            variables["OHOS_CXX_RUNTIME_DIR"] = runtime_dir
        cmake.configure(variables=variables)
        cmake.build()

    def test(self):
        # 运行期库搜索路径：被测包 + 全部依赖（Qt5 等）+ OHOS 工具链运行库
        lib_dirs = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                if not libdir:
                    continue
                candidate = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(candidate):
                    lib_dirs.append(candidate)
        runtime_dir = self._ohos_runtime_dir()
        if runtime_dir:
            lib_dirs.append(runtime_dir)
        lib_dirs.append(os.environ.get("LD_LIBRARY_PATH", ""))
        os.environ["LD_LIBRARY_PATH"] = ":".join(path for path in lib_dirs if path)
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        bindir = self.cpp.build.bindirs[0] if self.cpp.build.bindirs else "."
        test_bin = os.path.join(bindir, "test_mlite")
        self.run(test_bin, ignore_errors=False)
