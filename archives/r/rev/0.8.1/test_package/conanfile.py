import os

from conan import ConanFile


class RevTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # test_rev.cpp includes ladspa.h directly (LADSPA descriptor API)
        self.requires("ladspa-sdk/1.17")

    def build(self):
        cc = self.conf.get("tools.build:compiler_executables", {}).get(
            "cpp") or "c++"
        inc = self.dependencies["ladspa-sdk"].cpp_info.includedirs[0]
        src = os.path.join(self.source_folder, "test_rev.cpp")
        exe = os.path.join(self.build_folder, "test_rev")
        self.run(f"{cc} -std=c++17 -I{inc} {src} -o {exe} -ldl")

    def test(self):
        so = os.path.join(self.dependencies["rev"].cpp_info.libdirs[0],
                          "zita-reverbs.so")
        self.run(f'REV_PLUGIN_SO="{so}" '
                 f'"{os.path.join(self.build_folder, "test_rev")}"')
