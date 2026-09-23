import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class LuaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _link_env(self):
        env = Environment()
        if self.settings.os == "OHOS":
            sdk_root = "/data/service/hnp/ohos-sdk.org"
            if os.path.isdir(sdk_root):
                for entry in sorted(os.listdir(sdk_root), reverse=True):
                    llvm_lib = os.path.join(sdk_root, entry, "ohos", "native", "llvm", "lib")
                    if os.path.isdir(llvm_lib):
                        env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
                        break
        return env

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        lua = self.dependencies["lua"]
        include_flags = " ".join(shlex.quote(f"-I{path}") for path in lua.cpp_info.includedirs)
        lib_flags = " ".join(shlex.quote(f"-L{path}") for path in lua.cpp_info.libdirs)
        libs = " ".join(f"-l{lib}" for lib in lua.cpp_info.libs)
        system_libs = " ".join(f"-l{lib}" for lib in lua.cpp_info.system_libs)
        test_src = os.path.join(self.source_folder, "test_lua51.c")
        test_bin = os.path.join(self.build_folder, "test_lua51")
        with self._link_env().vars(self).apply():
            self.run(
                f'{shlex.quote(cc)} {include_flags} {shlex.quote(test_src)} '
                f'{lib_flags} {libs} {system_libs} -o {shlex.quote(test_bin)}'
            )

    def test(self):
        if can_run(self):
            test_bin = os.path.join(self.build_folder, "test_lua51")
            self.run(f'"{test_bin}"', env="conanrun")
