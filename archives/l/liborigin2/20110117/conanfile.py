#!/usr/bin/env python3
"""Conan recipe for liborigin2 20110117.

liborigin2 是一个纯 C++ 库，用于读取 OriginLab Origin 4.1 – 8.5.1 的 .opj 工程文件。
上游只提供 qmake 工程（liborigin2.pro）且**不使用任何 Qt 库**（.pro 里
`QT -= gui core`，源码零 Qt 引用）—— qmake 只是它的构建工具。OHOS 上没有
Qt5 base/qmake，因此本配方用 `files/CMakeLists.txt`（源文件清单与 .pro 一一对应）
复刻其构建语义；源码侧只做现代工具链/新版 Boost 必需的最小修补，见 patches/。

上游 20110117 tarball 不含 tree.hh，而 OriginParser.h:33 直接 include 它，
所以 tree.hh 作为 Conan 依赖（tree-hh/3.18）提供，不 vendoring 到本仓库。
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir


class Liborigin2Conan(ConanFile):
    name = "liborigin2"
    version = "20110117"
    description = "Library for reading OriginLab Origin 4.1 - 8.5.1 project files"
    license = "GPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/liborigin/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("origin", "opj", "file-format", "scientific")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        # 注意：一旦定义了 export_sources() 方法，类属性 exports_sources 就不会
        # 再生效（实测：只写属性 + 方法会让 files/ 静默丢失，构建时才报
        # "does not appear to contain CMakeLists.txt"）。因此这里显式导出。
        copy(self, "CMakeLists.txt", src=os.path.join(self.recipe_folder, "files"),
             dst=self.export_sources_folder)
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # boost 只作头文件使用：链接期零 boost 符号（见 notes.md 的三重证据）。
        # 必须 >= 1.90：1.90 起上游 boost/core/detail/sp_thread_sleep.hpp 才有
        # `!defined(__OHOS__)` 守卫；1.84 依赖包内的
        # BOOST_SP_NO_PTHREAD_SETCANCELSTATE 宏，而本配方不走 CMakeDeps 之外的
        # 传递路径，直接用带守卫的版本更干净。
        self.requires("boost/1.90.0.4.1")
        # 上游 20110117 tarball 缺 tree.hh（OriginParser.h 直接 include 它）。
        self.requires("tree-hh/3.18")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 上游只有 qmake 工程，注入配方自带的等价 CMake 构建描述。
        # 位置说明：files/ 经 export_sources() 落在「导出源目录」，而
        # get() 解包到 self.source_folder（cmake_layout 的 src/ 子目录），
        # 两者不是同一个目录，必须显式搬一次。
        copy(self, "CMakeLists.txt", src=self.export_sources_folder,
             dst=self.source_folder)
        if not os.path.isfile(os.path.join(self.source_folder, "CMakeLists.txt")):
            raise ConanException(
                "injected CMakeLists.txt not found in source folder %s"
                % self.source_folder)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def _fix_ohos_shared_lib(self, path):
        """OHOS 上动态库必须带平台自签段，否则 XPM 拒绝加载（EACCES / rc 126）。

        另外 OHOS 的 CMake 产物**没有 DT_SONAME**（也不会生成 libfoo.so.X 实体）。
        缺 SONAME 的后果不在本包而在下游：CMake 会按完整路径链接，把构建机
        conan cache 的绝对路径写进下游的 DT_NEEDED，换机器即无法加载 —— 仓库里
        已有三个制品因此损坏（fontconfig / poppler / tbb，见 libogg 的说明）。
        本包产物本来就只有一个无版本名实体 liborigin2.so，把 SONAME 设成文件名
        本身即与上游本意一致，因此直接用 patchelf 补，而不是改构建方式。

        顺序必须是 patchelf → 剥旧签名段 → 自签（改 ELF 会破坏链接器自签）。
        """
        tools = {}
        for name in ("patchelf", "llvm-objcopy", "binary-sign-tool"):
            found = shutil.which(name) or os.path.join("/data/service/hnp/bin", name)
            if not os.path.isfile(found):
                raise ConanException(f"Required OHOS tool is missing: {name}")
            tools[name] = found
        soname = os.path.basename(path)
        subprocess.run([tools["patchelf"], "--set-soname", soname, path],
                       check=True, timeout=60)
        subprocess.run([tools["llvm-objcopy"], "--remove-section", ".codesign", path],
                       capture_output=True, timeout=30)
        temporary = path + ".liborigin2-signed"
        subprocess.run([tools["binary-sign-tool"], "sign", "-inFile", path,
                        "-outFile", temporary, "-selfSign", "1"],
                       check=True, timeout=60)
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)

    def package(self):
        copy(self, "copying", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        if str(self.settings.os) == "OHOS" and self.options.shared:
            # OHOS 的 CMake 只产出无版本名的 liborigin2.so，这里按实际文件名
            # 定位（不硬编码 .so.1.0.0），避免在真机上找不到文件而失败。
            libdir = os.path.join(self.package_folder, "lib")
            shared_libs = [p for p in glob.glob(os.path.join(libdir, "liborigin2.so*"))
                           if not os.path.islink(p)]
            if not shared_libs:
                raise ConanException(
                    "OHOS shared build produced no liborigin2.so under %s" % libdir)
            for lib in shared_libs:
                self._fix_ohos_shared_lib(lib)

    def package_info(self):
        self.cpp_info.libs = ["origin2"]
        # 公共头安装在 include/liborigin2/ 下，头文件之间用裸名互相 include
        # （与 Debian 的 /usr/include/liborigin2/ 布局一致）。
        self.cpp_info.includedirs = ["include/liborigin2"]
        self.cpp_info.set_property("cmake_file_name", "liborigin2")
        self.cpp_info.set_property("cmake_target_name", "liborigin2::liborigin2")
        # 公共头（OriginObj.h / OriginParser.h）直接 include boost 与 tree.hh，
        # 二者因此是接口依赖，必须向消费者传递包含路径。
        # 这里必须写 boost 的 **components["headers"]**（→ "boost::headers"）而不是
        # 包级 "boost::boost"：boost 配方声明了 components 之后，包级目标的
        # 包含目录为空（CMakeDeps 生成的 boost_INCLUDE_DIRS_RELEASE 是空串），
        # 只有 Boost::headers 组件带 include。实测：用 boost::boost 时消费者的
        # `#include "boost/variant.hpp"` 直接找不到头文件。
        self.cpp_info.requires = ["boost::headers", "tree-hh::tree-hh"]
