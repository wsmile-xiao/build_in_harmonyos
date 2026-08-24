import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class LibZitaResamplerConan(ConanFile):
    name = "libzita-resampler"
    version = "1.11.2"
    package_type = "library"
    description = "C++ library for high-quality real-time sample-rate conversion"
    license = "GPL-3.0-only"
    homepage = "https://kokkinizita.linuxaudio.org/linuxaudio/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libzita-resampler supports Linux and OHOS only")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS validation requires armv8")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def layout(self):
        basic_layout(self)

    def build(self):
        source_dir = os.path.join(self.source_folder, "source")
        cxx = self.conf.get("tools.build:compiler_executables", default={}).get("cpp", "c++")
        cxxflags = "-Wall -fPIC -O2 -ffast-math -D_REENTRANT -D_POSIX_PTHREAD_SEMANTICS"
        cppflags = "-I."
        if str(self.settings.os) == "OHOS":
            cppflags += " -DENABLE_NEON"
        else:
            cppflags += " -DENABLE_SSE2"
        target = "libzita-resampler.so.1.11.2" if self.options.shared else "libzita-resampler.a"
        self.run(
            f'make -C "{source_dir}" CXX="{cxx}" '
            f'CXXFLAGS="{cxxflags}" CPPFLAGS="{cppflags}" '
            f"{target}",
            env="conanbuild",
        )

    def package(self):
        source_dir = os.path.join(self.source_folder, "source")
        include_dir = os.path.join(self.package_folder, "include", "zita-resampler")
        lib_dir = os.path.join(self.package_folder, "lib")
        copy(self, "*.h", os.path.join(source_dir, "zita-resampler"), include_dir)
        artifact = "libzita-resampler.so.1.11.2" if self.options.shared else "libzita-resampler.a"
        copy(self, artifact, source_dir, lib_dir)
        os.makedirs(lib_dir, exist_ok=True)
        if self.options.shared:
            for name in ("libzita-resampler.so", "libzita-resampler.so.1"):
                src = os.path.join(lib_dir, artifact)
                dst = os.path.join(lib_dir, name)
                shutil.copyfile(src, dst)
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        with open(os.path.join(pc_dir, "zita-resampler.pc"), "w", encoding="utf-8") as pc:
            pc.write(
                "prefix=${pcfiledir}/../..\n"
                "exec_prefix=${prefix}\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n\n"
                "Name: zita-resampler\n"
                "Description: High-quality real-time sample-rate conversion\n"
                "Version: 1.11.2\n"
                "Libs: -L${libdir} -lzita-resampler\n"
                "Cflags: -I${includedir}\n"
            )

    def package_info(self):
        self.cpp_info.libs = ["zita-resampler"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libzita-resampler")
        self.cpp_info.set_property("cmake_target_name", "libzita-resampler::libzita-resampler")
        self.cpp_info.set_property("pkg_config_name", "zita-resampler")
