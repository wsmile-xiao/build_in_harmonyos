import os
import shlex

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class AcfLibLua51TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("lua/5.1")

    def layout(self):
        basic_layout(self)

    def _link_env(self):
        env = Environment()
        if self.settings.os == "OHOS":
            sdk_root = "/data/service/hnp/ohos-sdk.org"
            if os.path.isdir(sdk_root):
                for entry in sorted(os.listdir(sdk_root), reverse=True):
                    llvm_lib = os.path.join(
                        sdk_root, entry, "ohos", "native", "llvm", "lib"
                    )
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
        include_flags = " ".join(
            shlex.quote(f"-I{path}") for path in lua.cpp_info.includedirs
        )
        lib_flags = " ".join(
            shlex.quote(f"-L{path}") for path in lua.cpp_info.libdirs
        )
        libs = " ".join(f"-l{lib}" for lib in lua.cpp_info.libs)
        system_libs = " ".join(f"-l{lib}" for lib in lua.cpp_info.system_libs)
        source = os.path.join(self.source_folder, "mini_lua.c")
        output = os.path.join(self.build_folder, "lua-runner")
        with self._link_env().vars(self).apply():
            self.run(
                f"{shlex.quote(cc)} -std=c99 {include_flags} "
                f"{shlex.quote(source)} {lib_flags} {libs} {system_libs} "
                f"-o {shlex.quote(output)}",
                env="conanbuild",
            )

    def test(self):
        package = self.dependencies["acf-lib-lua5.1"].package_folder
        runner = os.path.join(self.build_folder, "lua-runner")
        for script in ("test_acf_lib.lua", "upstream_acf_db_test.lua"):
            script_path = os.path.join(self.source_folder, script)
            self.run(
                f"{shlex.quote(runner)} {shlex.quote(script_path)} "
                f"{shlex.quote(package)} {shlex.quote(self.source_folder)}",
                env="conanrun",
            )
