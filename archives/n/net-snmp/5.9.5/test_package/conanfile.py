import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # ⚠️ net-snmp 的**公开头**里就 `#include <openssl/ossl_typ.h>`
        # （net-snmp-includes.h -> snmpv3_api.h -> library/scapi.h），
        # 所以兼容 OpenSSL 的消费者必须同时拿到 openssl 的头。
        # 但 test_package 只 require net-snmp 时，openssl 不一定出现在
        # self.dependencies 里 → 头路径拼不出来 → 编译期 fatal error。
        # 这里显式声明 openssl，保证头/库闭包可解析。
        self.requires("openssl/3.5.6")

    def build(self):
        # ⚠️ cpp_info.includedirs / libdirs 给的是**相对路径**（"include" / "lib"）。
        # 在 test_package 里直接 `-Iinclude` 会让编译器到**测试包自己的工作目录**找，
        # net-snmp 的头会把 openssl 传递依赖拉进来
        # （net-snmp-includes.h -> scapi.h -> <openssl/ossl_typ.h>），必然找不到：
        #   fatal error: 'openssl/ossl_typ.h' file not found
        # 注意：aggregated_components() **不会**在这里把相对路径绝对化（那是生成器的活），
        # 所以必须自己用 dependencies[ref].package_folder 拼绝对路径。
        incs = []
        libdirs = []
        for _ref, _dep in self.dependencies.items():
            # ⚠️ 不要 `if not package_folder: continue` —— 依赖在依赖图里可能还没
            # 「解析到本地」而 package_folder 为 None，一跳过就直接漏掉 openssl 的头，
            # 于是 net-snmp 头里的 `<openssl/ossl_typ.h>` 找不到（实测报错位置）。
            # 这里对每个依赖同时尝试 package_folder 与 cpp_info 自带的绝对路径。
            pkg = _dep.package_folder
            for p in _dep.cpp_info.includedirs:
                if os.path.isabs(p):
                    incs.append("-I" + p)
                elif pkg:
                    incs.append("-I" + os.path.join(pkg, p))
            for p in _dep.cpp_info.libdirs:
                if os.path.isabs(p):
                    libdirs.append(p)
                elif pkg:
                    libdirs.append(os.path.join(pkg, p))
        inc = " ".join(incs)
        # openssl 是 net-snmp 的传递依赖：某些情况下不会出现在 self.dependencies 的
        # 直接迭代里，这里显式补一次，保证 scapi.h 的 <openssl/ossl_typ.h> 能找到。
        try:
            _ossl = self.dependencies["openssl"]
            _opkg = _ossl.package_folder
            _odirs = _ossl.cpp_info.includedirs
            for p in _odirs:
                cand = p if os.path.isabs(p) else (os.path.join(_opkg, p) if _opkg else None)
                if cand and ("-I" + cand) not in incs:
                    incs.append("-I" + cand)
            inc = " ".join(incs)
            for p in _ossl.cpp_info.libdirs:
                cand = p if os.path.isabs(p) else (os.path.join(_opkg, p) if _opkg else None)
                if cand and cand not in libdirs:
                    libdirs.append(cand)
        except KeyError:
            pass
        nspkg = self.dependencies["net-snmp"].package_folder
        so = os.path.join(nspkg, "lib", "libnetsnmp.so")
        ns_libs = self.dependencies["net-snmp"].cpp_info.libs
        cc = os.environ.get("CC", "clang")
        # C 测试**不能**收 C++ 标准开关（clang 报 not allowed with 'C'）。
        # musl 上还要用 gnu 方言：严格 ISO 方言不定义 _POSIX_C_SOURCE，
        # POSIX 函数（clock_gettime 等）在 musl 头里就不声明。
        std_flag = "-std=gnu99"
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-l" + l for l in ns_libs]
                        + ["-Wl,-rpath," + p for p in libdirs] + ["-ldl"])
        self.run(f"{cc} {std_flag} test.c -o test_probe {inc} -DTARGET_SO='\"{so}\"' {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        if False:
            self.output.info("skip_test_run：GUI/app 库只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")

        # 消费方 ezsnmp 的 setup.py 靠 `net-snmp-config --version` / `--libs` 拿编译参数。
        # 这个脚本若没装出来、或装出来吐不出东西，ezsnmp **连构建都起不来**——
        # 而 C API 测试全绿也发现不了这一点（它压根不经过这个脚本）。
        cfg = os.path.join(self.dependencies["net-snmp"].package_folder, "bin", "net-snmp-config")
        self.run(f"{bash} -c '{cfg} --version'", env="conanrun")
        self.run(f"{bash} -c '{cfg} --libs'", env="conanrun")
