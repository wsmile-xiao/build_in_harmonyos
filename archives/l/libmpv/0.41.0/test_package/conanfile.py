import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibmpvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        variables = {}
        if str(self.settings.os) == "OHOS":
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            compiler = compilers.get("cpp") or compilers.get("cxx")
            if compiler:
                compiler_dir = os.path.dirname(os.path.realpath(compiler))
                variables["OHOS_CXX_RUNTIME_DIR"] = os.path.join(
                    compiler_dir, "..", "lib", "aarch64-linux-ohos"
                )
        cmake.configure(variables=variables)
        cmake.build()

    def test(self):
        dep = self.dependencies["libmpv"]
        libdir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        test_bin = os.path.join(self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".", "test_libmpv")
        # libmpv.so 动态链接 libass/ffmpeg/libplacebo 等，
        # 运行时需收集全部依赖（含传递依赖）的 lib 目录；
        # 组件模式依赖（如 ffmpeg）顶层 cpp_info.libdirs 为空，需回退默认 "lib"
        library_paths = [libdir]
        for d in self.dependencies.values():
            # 跳过无 package_folder 的依赖（如 tool_requires/build 上下文依赖）
            if d.package_folder is None:
                continue
            libdirs = d.cpp_info.libdirs or ["lib"]
            pkg_lib = os.path.join(d.package_folder, libdirs[0])
            if os.path.isdir(pkg_lib):
                library_paths.append(pkg_lib)
        existing_ld = os.environ.get("LD_LIBRARY_PATH")
        if existing_ld:
            library_paths.append(existing_ld)
        ld_path = ":".join(library_paths)
        self.run(
            f'LD_LIBRARY_PATH="{ld_path}" "{test_bin}"',
            ignore_errors=False
        )
