#!/usr/bin/env python3
"""Conan test_package for gadap 2.0 (R34: 实质调用被测包 API)。

编译链接真实消费者程序:
  - gadap 头 (gadap.h) + libgadap.a
  - libdap 静态库三件套 (dap/dapclient/dapserver) + 其依赖
    (libxml2/curl/libtirpc/uuid) — gadap::gadap 的 cpp_info.requires
    传递提供
  - 链接后运行, 断言 gadap API 行为 (见 test.cc)
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class GadapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 收集全链路 include/lib 路径 (gadap + libdap + 传递依赖)
        incs = []
        libdirs = []
        for _ref, _d in self.dependencies.items():
            pf = getattr(_d, "package_folder", None) or ""
            for p in _d.cpp_info.includedirs:
                incs.append(p if (os.path.isabs(p) or not pf) else os.path.join(pf, p))
                # libdap 头在 include/libdap 子目录, 上游头内 angled
                # include 同目录头需要第二个 include 根 (libdap test_package 同法)
                _sub = os.path.join(p, "libdap") if os.path.isabs(p) else os.path.join(pf, p, "libdap")
                if os.path.isdir(_sub):
                    incs.append(_sub)
            for p in _d.cpp_info.libdirs:
                libdirs.append(p if (os.path.isabs(p) or not pf) else os.path.join(pf, p))
        inc = " ".join(dict.fromkeys("-I" + i for i in incs))
        libdir_flags = " ".join(dict.fromkeys("-L" + l for l in libdirs if l))
        # 链接顺序: gadap 依赖 libdap (静态库符号解析顺序敏感)
        cxx = os.environ.get("CXX") or "clang++"
        self.run(
            f"{cxx} test.cc -o gadap_test {inc} {libdir_flags} "
            f"-lgadap -ldap -ldapclient -ldapserver -lxml2 -lcurl -ltirpc -luuid "
            f"-lm -lpthread -stdlib=libc++ -std=c++11",
            env="conanbuild",
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: 只验编译+链接")
            return
        # OHOS musl loader 无默认共享库搜索路径: libc++_shared.so 在
        # /system/lib64, libxml2/libcurl 在 conan 包 lib — 显式拼
        # LD_LIBRARY_PATH (sdk llvm/lib 在前防 lld 遮蔽问题不影响
        # 运行期, 但保持同序无害)
        _ldp = ["/system/lib64"]
        for _ref, _d in self.dependencies.items():
            pf = getattr(_d, "package_folder", None) or ""
            for p in _d.cpp_info.libdirs:
                _lb = p if (os.path.isabs(p) or not pf) else os.path.join(pf, p)
                if _lb:
                    _ldp.append(_lb)
        _ld_path = ":".join(dict.fromkeys(_ldp))
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(
            f"{bash} -c 'LD_LIBRARY_PATH={_ld_path} ./gadap_test && echo GADAP_CONAN_TEST_PASS'",
            env="conanrun",
        )
