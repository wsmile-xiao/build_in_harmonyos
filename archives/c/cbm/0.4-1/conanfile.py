"""Conan recipe — cbm 0.4-1 (Color Bandwidth Meter, C++ autotools + ncurses)"""
import os
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.gnu import Autotools


class CbmConan(ConanFile):
    name = "cbm"
    version = "0.4-1"
    package_type = "application"
    license = "GPL-2.0"
    description = "Color Bandwidth Meter: display network traffic speed in real time"
    homepage = "https://github.com/resurrecting-open-source-projects/cbm"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("ncurses/6.4")

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("autoconf/2.72")
        self.tool_requires("libtool/2.5.4")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Direct compilation bypassing autotools (OHOS perl incompatible)
        cc_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = cc_execs.get("cpp", "g++")
        ncurses_pf = self.dependencies["ncurses"].package_folder
        ncurses_inc = os.path.join(ncurses_pf, "include")
        ncurses_lib = os.path.join(ncurses_pf, "lib")
        src_dir = os.path.join(self.source_folder, "src")
        # Generate minimal config.h
        with open(os.path.join(src_dir, "config.h"), "w") as f:
            f.write("#define HAVE_CURSES_H 1\n")
            f.write("#define PACKAGE \"cbm\"\n")
            f.write("#define PACKAGE_BUGREPORT \"https://github.com/resurrecting-open-source-projects/cbm/issues\"\n")
            f.write("#define PACKAGE_NAME \"cbm\"\n")
            f.write("#define PACKAGE_STRING \"cbm 0.4\"\n")
            f.write("#define PACKAGE_TARNAME \"cbm\"\n")
            f.write("#define PACKAGE_URL \"\"\n")
            f.write("#define PACKAGE_VERSION \"0.4\"\n")
            f.write("#define VERSION \"0.4\"\n")
            f.write("#define STDC_HEADERS 1\n")
        # Compile source files
        srcs = []
        for cpp in ["cbm.cpp", "statistics.cpp",
                     "widgets/Bar.cpp", "widgets/Screen.cpp",
                     "widgets/VerticalTable.cpp", "widgets/Window.cpp"]:
            obj = cpp.replace(".cpp", ".o")
            self.run(
                f"{cxx} -c -O2 -fPIC -I{ncurses_inc} -I{src_dir} -o {obj} {cpp}",
                cwd=src_dir)
            srcs.append(obj)
        # Link
        self.run(
            f"{cxx} {' '.join(srcs)} -o cbm -L{ncurses_lib} -lncursesw",
            cwd=src_dir)

    def package(self):
        copy(self, "cbm", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
