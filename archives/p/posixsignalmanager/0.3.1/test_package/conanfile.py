import os
from conan import ConanFile
from conan.tools.cmake import cmake_layout

class PosixsignalmanagerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt/5.15.19")

    def layout(self):
        cmake_layout(self)

    def _get_flags(self):
        cflags = []
        libs = []
        for dep in self.dependencies.values():
            cpp = dep.cpp_info
            root = getattr(cpp, 'rootpath', dep.package_folder)
            dep_name = str(getattr(dep, 'ref', getattr(dep, 'name', '')))
            for inc in getattr(cpp, 'includedirs', []):
                inc_path = inc if os.path.isabs(inc) else os.path.join(root, inc)
                cflags.append(f"-I{inc_path}")
                if "qt" in dep_name.lower() and os.path.isdir(os.path.join(inc_path, "QtCore")):
                    cflags.append(f"-I{os.path.join(inc_path, 'QtCore')}")
            for lib in getattr(cpp, 'libdirs', []):
                lib_path = lib if os.path.isabs(lib) else os.path.join(root, lib)
                libs.append(f"-L{lib_path}")
            for lib_name in getattr(cpp, 'libs', []):
                libs.append(f"-l{lib_name}")
        return " ".join(cflags), " ".join(libs)

    def build(self):
        src = os.path.join(self.source_folder, "test_posixsignalmanager.cpp")
        out = os.path.join(self.build_folder, "test_posixsignalmanager")
        cflags, libs = self._get_flags()
        self.run(
            f"/data/service/hnp/bin/clang++ -std=c++17 -stdlib=libc++ "
            f"{cflags} {libs} -o {out} {src}",
            env="conanbuild",
        )

    def test(self):
        self.run(os.path.join(self.build_folder, "test_posixsignalmanager"), env="conanrun")
