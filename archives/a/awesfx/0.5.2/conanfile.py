from conan import ConanFile
import os
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches, copy
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class AwesfxConan(ConanFile):
    name = "awesfx"
    version = "0.5.2"
    description = "AWE32 Sound Driver utility programs"
    homepage = "https://github.com/tiwai/awesfx"
    license = "GPL-2.0-or-later"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        os.makedirs(os.path.join(self.build_folder, "bin"), exist_ok=True)
        config_h = os.path.join(self.source_folder, "awelib", "config.h")
        with open(config_h, "w") as f:
            f.write("#define HAVE_STDINT_H 1\n#define SIZEOF_UNSIGNED_LONG 8\n"
                    "#define DEFAULT_SF_PATH \"/system/etc/sounds\"\n")
        version_h = os.path.join(self.source_folder, "include", "awe_version.h")
        with open(version_h, "w") as f:
            f.write('#define VERSION_STR "0.5.2"\n'
                    '#define COPYRIGHT_STR "copyright (c) 1996-2003 by Takashi Iwai"\n'
                    '#define VERSION_NOTE "   ver." VERSION_STR "  " COPYRIGHT_STR "\\n"\n')
        executables = self.conf.get("tools.build:compiler_executables", default={})
        cc = os.environ.get("CC", executables.get("c", "cc"))
        cflags = os.environ.get("CFLAGS", "")
        core = [os.path.join(self.source_folder, "awelib", name)
                for name in os.listdir(os.path.join(self.source_folder, "awelib"))
                if name.endswith(".c")]
        for tool in ("sf2text", "text2sf"):
            source = os.path.join(self.source_folder, tool + ".c")
            output = os.path.join(self.build_folder, "bin", tool)
            inputs = " ".join(f'"{path}"' for path in core + [source])
            self.run(f'{cc} {cflags} -I"{self.source_folder}/include" -I"{self.source_folder}/awelib" {inputs} -o "{output}"')

    def package(self):
        copy(self, "*", src=os.path.join(self.build_folder, "bin"), dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
