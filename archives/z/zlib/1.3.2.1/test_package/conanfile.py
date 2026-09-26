import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["zlib"].cpp_info
        # R34/L1e：OHOS SDK sysroot 自带系统 zlib.h/libz.so。若 test 源码只 include
        # <zlib.h>，CI 破坏性负测试（mv 移走包产物后重跑 conan test）会 fallback 到
        # 系统库编译通过 → 误判为"假测试"。显式校验包内产物路径存在，确保 test 真实
        # 依赖被测包（链不上 / 找不到头文件时在 build 阶段即失败）。
        for p in dep.includedirs:
            if not os.path.isdir(p):
                raise ConanException(f"zlib package include dir missing: {p}")
        libdir = dep.libdirs[0]
        if not os.path.isdir(libdir):
            raise ConanException(f"zlib package lib dir missing: {libdir}")

        # R33: 编译器从 Conan conf 获取，与配方本体保持一致（禁止裸用 ${CC}）。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        inc = " ".join("-I" + p for p in dep.includedirs)

        # 1) 消费者 API 冒烟测试：真实调用 zlib API（compress/uncompress 往返、
        #    compress2/uncompress2、adler32/crc32、deflate/inflate、gzopen/gzread），
        #    静态链接被测包的 libz.a。
        self.run(f"{cc} test.c -o test_probe {inc} -L{libdir} -lz")

        # 2) 鸿蒙特有测试（E539/E541）：把被测包静态 libz.a 用 clang -shared -fPIC
        #    链成共享库。非 PIC 静态库在 aarch64 上会报 R_AARCH64_ADR_PREL_PG_HI21
        #    relocation 直接链接失败；PIC 则链接成功且无 TEXTREL。
        self.run(f"{cc} -shared -fPIC pic_probe.c -o libzpic_probe.so {inc} {libdir}/libz.a")
        # 校验 DSO 无 TEXTREL、且不引入运行期 libz.so（只依赖 libc）——对应 R26/E541。
        # readelf 是系统标准 binutils 工具（非编译器/编译标志，R33 不约束）；PATH 含 /data/service/hnp/bin。
        self.run("readelf -d libzpic_probe.so | grep -qi TEXTREL && "
                 "(echo 'FAIL: TEXTREL present in PIC probe DSO' && exit 1) || "
                 "echo 'PASS: no TEXTREL in PIC probe DSO'", ignore_errors=False)
        # NEEDED 中不得出现 libz.so（静态包不允许把系统同名 .so 带进依赖链）
        self.run("if readelf -d libzpic_probe.so | grep -q 'libz.so'; then "
                 "echo 'FAIL: probe DSO pulls libz.so' && exit 1; "
                 "else echo 'PASS: probe DSO does not pull system libz.so'; fi")

        # 3) dlopen 运行器：真实调用链进 DSO 的 zlib-backed 函数并校验数据。
        self.run(f"{cc} probe_main.c -o probe_main {inc}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
        self.run(f"{bash} -c './probe_main'", env="conanrun")
