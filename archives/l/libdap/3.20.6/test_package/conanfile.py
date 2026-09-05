#!/usr/bin/env python3
"""Conan test_package for libdap 3.20.6 (R34: 实质调用被测包 API)。

消费者视角验证:
  1. 编译链接: 用被测包的头文件 + 三个库 (dap/dapclient/dapserver) 编译
     一个真实调用 libdap DAP2 数据模型 API 的程序
     (BaseTypeFactory/DDS/Int32/Str/Array/AttrTable/DAS + value round-trip)
  2. 运行断言: 程序内做 set_value/value 往返校验 + DDS.print 序列化,
     失败返回非 0
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class LibdapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # libdap 头在 include/libdap/ 子目录 (pkgincludedir), 上游头文件
        # 内部用 angled include 引 dods-datatypes.h 等同目录头 — 两个
        # include 根都注入; 传递依赖 (libxml2/libtirpc/uuid) 也要
        incs = []
        libdirs = []
        libs = []
        for _ref, _d in self.dependencies.items():
            pf = getattr(_d, "package_folder", None) or ""
            for p in _d.cpp_info.includedirs:
                incs.append(p if (os.path.isabs(p) or not pf) else os.path.join(pf, p))
                # pkginclude 子目录 (include/libdap) 同样注入 — 上游头
                # 之间 angled include 需要
                _sub = os.path.join(p, "libdap") if os.path.isabs(p) else os.path.join(pf, p, "libdap")
                if os.path.isdir(_sub):
                    incs.append(_sub)
            for p in _d.cpp_info.libdirs:
                libdirs.append(p if (os.path.isabs(p) or not pf) else os.path.join(pf, p))
            libs.extend(_d.cpp_info.libs)
        inc = " ".join(dict.fromkeys("-I" + i for i in incs))
        libdir_flags = " ".join(dict.fromkeys("-L" + l for l in libdirs if l))
        lib_flags = " ".join("-l" + l for l in libs if l)
        cxx = os.environ.get("CXX") or "clang++"
        # OHOS loader 无默认共享库搜索路径, conftest/运行需要 LD_LIBRARY_PATH
        # (conanbuild/conanrun env 提供)
        self.run(
            f"{cxx} test_package.cpp -o libdap_test {inc} {libdir_flags} {lib_flags} "
            f"-ltirpc -luuid -lpthread --std=c++11 -stdlib=libc++",
            env="conanbuild",
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: 只验编译+链接")
            return
        # OHOS musl loader 无默认共享库搜索路径: libc++_shared.so 在
        # /system/lib64, libxml2 等依赖在 conan 包 lib — 显式拼
        # LD_LIBRARY_PATH (conanrun 只含被测包自身 lib)
        _ldp = ["/system/lib64"]
        for _ref, _d in self.dependencies.items():
            pf = getattr(_d, "package_folder", None) or ""
            for p in _d.cpp_info.libdirs:
                _ldp.append(p if (os.path.isabs(p) or not pf) else os.path.join(pf, p))
        _ld_path = ":".join(dict.fromkeys(_ldp))
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(
            f"{bash} -c 'LD_LIBRARY_PATH={_ld_path} ./libdap_test && echo LIBDAP_TEST_PASS'",
            env="conanrun",
        )
