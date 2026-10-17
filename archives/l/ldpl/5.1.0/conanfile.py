import os
import time

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LdplConan(ConanFile):
    name = "ldpl"
    version = "5.1.0"
    description = ("LDPL (Logic Design Programming Language) compiler: translates "
                   ".ldpl sources into C++ and builds them with the system C++ "
                   "front-end")
    license = "Apache-2.0"
    homepage = "https://www.ldpl-lang.org/"
    url = "https://github.com/Lartu/ldpl"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload 的 URL 末段是 tag 名、没有 .tar.gz 后缀，必须显式给 filename，
        # 否则 get() 会按 zip 解包并抛 BadZipFile
        get(self, filename="ldpl-5.1.0.tar.gz",
            **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _cxx(self):
        # R33: 编译器只从 toolchain conf 取，不靠裸 PATH
        exe = self.conf.get("tools.build:compiler_executables", default={}) or {}
        return exe.get("cpp") or exe.get("c") or "clang++"

    def build(self):
        apply_conandata_patches(self)
        cxx = self._cxx()
        # 运行期资源目录 = 包内 lib/ldpl（上游由 -DLDPLLIBLOCATION 烧死；补丁把它
        # 降级成默认值，见 patches/0001 与 notes.md）
        libdir = os.path.join(self.package_folder, "lib", "ldpl").replace("\\", "/")
        out = os.path.join(self.build_folder, "ldpl").replace("\\", "/")
        date = time.strftime("%Y-%m-%d")
        hour = time.strftime("%H:%M:%S")
        # 等价于上游 makefile 的 all 目标，但去掉 LFLAGS 的
        # -static-libgcc -static-libstdc++：OHOS SDK 只提供 libc++，没有可静态链的
        # libstdc++ 归档
        cmd = ('"{cxx}" -std=gnu++11 -Wall -fpermissive'
               ' -DVERSION=\'"5.1.0"\' -DVERSIONNAME=\'"Groovy Gualicho"\''
               ' -DCOMPILEDATE=\'"{date}"\' -DCOMPILEHOUR=\'"{hour}"\''
               ' -DLPMLOCATION=\'"~/ldpl/lpm/"\''
               ' -DLDPLLIBLOCATION=\'"{libdir}"\''
               ' "{src}" -o "{out}"').format(
            cxx=cxx, date=date, hour=hour, libdir=libdir,
            src=os.path.join(self.source_folder, "src", "ldpl.cpp").replace("\\", "/"),
            out=out)
        self.run(cmd)
        if not os.path.isfile(out):
            raise Exception("ldpl binary not produced: " + out)
        # 上游 LDPL-5.1.0 归档内没有测试套件（tests/ 目录是该 tag 之后才引入的，
        # 取数命令与结论见 notes.md），因此 build() 里没有 make check/ctest 可跑；
        # 端到端功能验证全部落在 test_package/test_ldpl.sh（真实调用 ldpl 编译并
        # 运行 .ldpl 程序）。

    def package(self):
        copy(self, "ldpl", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # ldpl 运行期要把 ldpl_lib.cpp 连同 BigInt.hpp 一起塞进生成的 C++，
        # 这两个文件必须随包发布（与上游 make install 的清单一致）
        copy(self, "ldpl_lib.cpp", src=os.path.join(self.source_folder, "src", "ldpl_lib"),
             dst=os.path.join(self.package_folder, "lib", "ldpl"))
        copy(self, "BigInt.hpp", src=os.path.join(self.source_folder, "src", "ldpl_lib"),
             dst=os.path.join(self.package_folder, "lib", "ldpl"))
        copy(self, "ldpl.1", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "res", "man", "man1"))
        binpath = os.path.join(self.package_folder, "bin", "ldpl")
        if os.path.isfile(binpath):
            os.chmod(binpath, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.builddirs = []
        # 让包可重定位：conanrun 里的 LDPL_LIB_LOCATION 指向本机实际安装路径，
        # 覆盖编译期烧进二进制的那个默认值
        self.runenv_info.define_path(
            "LDPL_LIB_LOCATION", os.path.join(self.package_folder, "lib", "ldpl"))
