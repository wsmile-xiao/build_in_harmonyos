#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibPgfConan(ConanFile):
    name = "libpgf"
    version = "7.21.7"
    license = "LGPL-2.1-or-later"
    homepage = "https://libpgf.org"
    url = "https://sourceforge.net/projects/libpgf"
    description = "libPGF: wavelet-based Progressive Graphics File (PGF) image compression library"
    topics = ("image", "compression", "wavelet", "pgf")

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass  # W0 实测：上游 configure.ac 只检查 C++ 编译器，无任何第三方依赖

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # R33：编译器/标志一律来自 Conan（profile conf 或配方内派生），不依赖裸 shell 环境变量。
        # 这里仅生成 conanbuild.sh 合入 profile buildenv（CONFIG_SHELL/PATH 等）。
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # CI 真根因（inotify-tools 4.25.9.0 同类）：CI worker 缺 aclocal，autoreconf -fi 整链死路。
        # libpgf 7.21.7 源码 zip 只有 configure.ac（版本号还停留在 7.15.32），无预生成
        # configure/Makefile.in；且 src/*.cpp、include/*.h 均不引用 config.h（纯 autotools 遗留物）。
        # 故绕开 autoconf/automake，直接用极简 Makefile 编译 src/ 下全部 6 个翻译单元。
        # 上游 Makefile.am 的 lib_LTLIBRARIES=libpgf.la 即同等源文件集合。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp") or "clang++"
        ar = compilers.get("archive") or "llvm-ar"

        src = self.source_folder
        bld = os.path.join(self.build_folder, "ohos-build")
        os.makedirs(bld, exist_ok=True)

        cppstd = self.settings.get_safe("compiler.cppstd")
        std_flag = f"-std=c++{cppstd}" if cppstd else "-std=c++17"
        optimize = {
            "Debug": "-O0 -g",
            "Release": "-O2",
            "RelWithDebInfo": "-O2 -g",
            "MinSizeRel": "-Os",
        }.get(str(self.settings.build_type), "-O2")
        # 上游 OpenMP 由 _OPENMP 宏门控（PGFplatform.h），不传 -fopenmp 即天然禁用
        pic = "-fPIC" if (self.options.shared or self.options.fPIC) else ""
        common_cxx = f"{std_flag} {optimize} {pic} -I{src}/include -I{src}/src"

        lib_objs = " ".join(f"{bld}/{n}.o" for n in (
            "Decoder", "Encoder", "PGFimage", "PGFstream", "Subband", "WaveletTransform"))
        target = "shared" if self.options.shared else "static"

        makefile_path = os.path.join(self.build_folder, "Makefile")
        with open(makefile_path, "w") as f:
            f.write("# Minimal Makefile for libpgf OHOS cross-build (CI lacks aclocal; sources"
                    " do not use config.h)\n")
            f.write(f"CXX = {cxx}\nAR = {ar}\n")
            f.write(f"CXXFLAGS += {common_cxx}\n\n")
            f.write(f"LIB_OBJS = {lib_objs}\n\n")
            f.write(f"{bld}/%.o: {src}/src/%.cpp\n\t$(CXX) $(CXXFLAGS) -c $< -o $@\n\n")
            f.write("static: $(BUILD)/libpgf.a\n")
            f.write("$(BUILD)/libpgf.a: $(LIB_OBJS)\n\t$(AR) rcs $@ $(LIB_OBJS)\n\n")
            f.write("shared: $(BUILD)/libpgf.so\n")
            f.write("$(BUILD)/libpgf.so: $(LIB_OBJS)\n\t$(CXX) -shared -o $@ $(LIB_OBJS)\n")

        env_script = os.path.join(self.generators_folder, "conanbuild.sh")
        jobs = int(self.conf.get("tools.build:jobs", default=2))
        if os.path.exists(env_script):
            make_cmd = f'. "{env_script}" && make -f "{makefile_path}" BUILD={bld} {target} -j{jobs}'
        else:
            make_cmd = f'make -f "{makefile_path}" BUILD={bld} {target} -j{jobs}'
        self.run(make_cmd, cwd=self.source_folder, shell=True)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "PGF*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        if self.options.shared:
            copy(self, "libpgf.so", src=os.path.join(self.build_folder, "ohos-build"),
                 dst=os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libpgf.a", src=os.path.join(self.build_folder, "ohos-build"),
                 dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["pgf"]
        self.cpp_info.includedirs = ["include"]
