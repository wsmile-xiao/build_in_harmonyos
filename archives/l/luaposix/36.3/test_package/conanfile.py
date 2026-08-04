#!/usr/bin/env python3
"""test_package for luaposix — verifies POSIX binding."""
import os
from conan import ConanFile
from conan.tools.build import cross_building

class LuaposixTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # test.sh invokes `lua`; pin the matching Lua 5.5 runtime so the
        # built .so (compiled for 5.5) is loadable instead of system 5.4.
        self.requires("lua/5.5.0")

    def generate(self):
        # Ensure conanrun PATH resolves `lua` to the 5.5 runtime from the
        # dependency, not a system 5.4 interpreter.
        import os
        if self.dependencies.get("lua"):
            lua_bin = os.path.join(self.dependencies["lua"].package_folder, "bin")
            if os.path.isdir(lua_bin):
                self.runenv_info.append_path("PATH", lua_bin)

    def test(self):
        if cross_building(self):
            return
        import os
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        # Prepend lua/5.5.0 bin to PATH so test.sh's `lua` resolves to the
        # matching 5.5 runtime (system has 5.4 which can't load 5.5 .so).
        lua_bin = os.path.join(self.dependencies["lua"].package_folder, "bin")
        self.run(f"export PATH={lua_bin}:$PATH && {bash} test.sh", env="conanrun")
