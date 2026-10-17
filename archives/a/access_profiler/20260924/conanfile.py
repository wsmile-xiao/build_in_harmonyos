#!/usr/bin/env python3
"""Conan recipe — access_profiler 20260924 (pure C++ static library)

access_profiler（arvidn）是一个重型的 C++ 类字段访问分析库：让类型继承
access_profiler::instrument_type<T> 后，库通过覆写 operator new/delete、
按页 mprotect(PROT_NONE) + SIGSEGV/SIGBUS 处理 + 单步模式记录每个字段的
访问热区，进程退出时写出 access_profile.out。

上游为 Boost.Build（Jamfile）项目：无 configure、无 make install 目标，
构建产出 libaccess_profiler.a（库）+ test 可执行（上游测试）。

OHOS 适配要点（本地 W3 实测验证）：
1. 直编译：不走 autotools，直接 CXX/AR 调用（编译器由 profile conf 注入，
   R33：不裸用 ${CC}）。仅库形态，无 CLI 产物 -> 不声明 commands.json（R38）。
2. aarch64 平台修正：上游单步路径写 Darwin/x86 专属的
   uc->uc_mcontext->__ss.__rflags/__eflags；OHOS aarch64 改为
   uc_mcontext.pstate 的 SS 位（0x200000）启停单步（补丁随源码进入 PR）。
3. OHOS 装载器修复：上游全部外部链接全局对象（pagemutex/pagemap/typemutex/
   typemap/access/last_page）在 OHOS PIE 装载期触发 SIGSEGV（本地二分实测：
   外部链接全局对象崩溃、static 内部链接正常），全部改为 static 内部链接。
4. 静态库默认（上游本身只有静态形态；shared 选项保留以符合模板，仅静态生效）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AccessProfilerConan(ConanFile):
    name = "access_profiler"
    version = "20260924"
    description = "access_profiler: heavy-weight C++ class field access profiler"
    license = "GPL-3.0"
    homepage = "https://github.com/arvidn/access_profiler"
    url = "https://github.com/arvidn/access_profiler"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # 纯源码就地构建（无 out-of-source 支持）
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("access_profiler is built for Linux/OHOS only")

    def build(self):
        apply_conandata_patches(self)
        cxx = self.conf.get("tools.build:compiler_executables", default={}).get("cpp") or "c++"
        ar = self.conf.get("tools.build:compiler_executables", default={}).get("ar") or "ar"
        cxxflags = "-std=c++17 -O2 -fPIC -fexceptions"
        self.run(f"{cxx} {cxxflags} -c access_profiler.cpp -o access_profiler.o")
        self.run(f"{ar} rcs libaccess_profiler.a access_profiler.o")

    def package(self):
        inc = os.path.join(self.package_folder, "include")
        lib = os.path.join(self.package_folder, "lib")
        copy(self, "access_profiler.hpp", src=".", dst=inc)
        copy(self, "libaccess_profiler.a", src=".", dst=lib)

    def package_info(self):
        self.cpp_info.libs = ["access_profiler"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
