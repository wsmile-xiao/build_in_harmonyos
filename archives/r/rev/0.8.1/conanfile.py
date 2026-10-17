from conan import ConanFile
from conan.tools.files import copy, get
import os

required_conan_version = ">=2.0"


class RevPluginsConan(ConanFile):
    name = "rev"
    version = "0.8.1"
    description = "REV LADSPA plugins: stereo reverb based on greverb, by Fons Adriaensen"
    license = "GPL-2.0-or-later"
    url = "https://kokkinizita.linuxaudio.org/linuxaudio/"
    homepage = "https://kokkinizita.linuxaudio.org/linuxaudio/"
    topics = ("ladspa", "audio", "reverb", "plugin")

    settings = "os", "arch", "compiler", "build_type"
    requires = "ladspa-sdk/1.17"
    no_copy_source = True

    def export_sources(self):
        # Self-written build driver (recipe asset, not an upstream modification):
        # upstream ships a host-only Makefile that hardcodes /usr/lib/ladspa,
        # unsuitable for cross builds, so build() drives the compiler directly.
        pass

    def apply_conandata_patches(self):
        # No upstream patches for 0.8.1 (patches: [] in conandata.yml).
        pass

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)

    def build(self):
        src = os.path.join(self.source_folder, "source")
        ladspa_include = self.dependencies["ladspa-sdk"].cpp_info.includedirs[0]
        cc = self.conf.get("tools.build:compiler_executables", {}).get(
            "cpp") or "c++"
        objs = []
        for f in ("revplugins.cc", "reverbs.cc", "zreverb.cc", "pareq.cc"):
            obj = os.path.join(self.build_folder, f + ".o")
            self.run(f'{cc} -I{src} -I{ladspa_include} -fPIC -D_REENTRANT '
                     f'-O2 -c {os.path.join(src, f)} -o {obj}')
            objs.append(obj)
        so = os.path.join(self.build_folder, "zita-reverbs.so")
        self.run(f"{cc} -shared -o {so} " + " ".join(objs))

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.so", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib", "ladspa"))

    def package_info(self):
        self.cpp_info.libdirs = ["lib/ladspa"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
