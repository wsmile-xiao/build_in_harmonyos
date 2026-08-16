import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AcfLibLua51Conan(ConanFile):
    name = "acf-lib-lua5.1"
    version = "0.11.1"
    description = "Alpine Configuration Framework standard Lua libraries for Lua 5.1"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-lib"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # Pure Lua modules form a runtime library; mini_lua is test-only.
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    _lua_root = os.path.join("share", "lua", "5.1")
    _modules = (
        "apk.lua",
        "date.lua",
        "db.lua",
        "format.lua",
        "fs.lua",
        "html.lua",
        "processinfo.lua",
        "validator.lua",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"acf-lib-lua5.1 does not support os={self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        root = Path(self.source_folder)
        actual = sorted(path.name for path in root.glob("*.lua") if path.is_file())
        expected = sorted(self._modules)
        if actual != expected:
            raise ConanInvalidConfiguration(
                f"Unexpected ACF Lua module inventory: expected {expected}, found {actual}"
            )
        for module in self._modules:
            if (root / module).stat().st_size == 0:
                raise ConanInvalidConfiguration(f"Empty upstream Lua module: {module}")

    def package(self):
        lua_root = os.path.join(self.package_folder, self._lua_root)
        copy(
            self,
            "*.lua",
            src=self.source_folder,
            dst=os.path.join(lua_root, "acf"),
            keep_path=False,
        )
        # Upstream creates compatibility links one level above acf/. Copies
        # preserve both module names without relying on HMDFS symlink support.
        copy(
            self,
            "*.lua",
            src=self.source_folder,
            dst=lua_root,
            keep_path=False,
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = [self._lua_root]
        lua_root = os.path.join(self.package_folder, self._lua_root)
        lua_path = ";".join(
            (
                os.path.join(lua_root, "?.lua"),
                os.path.join(lua_root, "?", "init.lua"),
                os.path.join(lua_root, "acf", "?.lua"),
            )
        )
        self.buildenv_info.define("LUA_PATH", lua_path + ";;")
        self.runenv_info.define("LUA_PATH", lua_path + ";;")
