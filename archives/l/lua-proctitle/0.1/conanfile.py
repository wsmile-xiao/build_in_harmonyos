import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LuaProctitleConan(ConanFile):
    name = "lua-proctitle"
    version = "0.1"
    description = "Lua C module for changing the current process name"
    license = "MIT"
    homepage = "https://github.com/hoelzro/lua-proctitle"
    url = ""
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("lua/5.4.8")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        lua = self.dependencies["lua"]
        include_dir = lua.cpp_info.includedirs[0]
        lib_dir = lua.cpp_info.libdirs[0]
        self.run(
            f'"{cc}" -fPIC -shared -O2 -Wall -Wextra '
            f'-I"{include_dir}" proctitle.c '
            f'-L"{lib_dir}" -llua -ldl -lm -o proctitle.so',
            cwd=self.source_folder,
        )

    def package(self):
        copy(
            self,
            "proctitle.so",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib", "lua", "5.4"),
        )
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        module_dir = os.path.join(self.package_folder, "lib", "lua", "5.4")
        self.runenv_info.prepend_path("LUA_CPATH", os.path.join(module_dir, "?.so"))
