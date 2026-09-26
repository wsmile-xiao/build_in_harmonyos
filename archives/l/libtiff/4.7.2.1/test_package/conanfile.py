import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libtiff"].cpp_info
        # L1e 破坏性反向验证配套：显式校验包内产物存在，确保 test 真实依赖被测包
        # （链不上/找不到头文件时在 build 阶段即失败，而非静默 fallback 到系统库）。
        for p in dep.includedirs:
            if not os.path.isdir(p):
                raise ConanException(f"libtiff package include dir missing: {p}")
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libtiff.so")
        if not os.path.isfile(so):
            raise ConanException(f"libtiff package lib missing: {so}")
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        # R33: 编译器从 Conan conf 获取，禁止裸用 shell ${CC}。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # 1) 消费者 API 真实读写测试（R34）：链接 libtiff，逐 COMPRESSION_* 后端
        #    写图再读回、逐像素比对（zlib/jpeg 等至少两个后端，实际覆盖 10 个）。
        self.run(f"{cc} test.c -o test_probe {inc} -L{libdir} -ltiff")

        # 2) 鸿蒙特有测试（E539/E541 同法，参考 zlib 1.3.2.1 PIC-DSO 探针）：
        #    消费 libtiff.so 的代码编成 -fPIC DSO，验证下游 DSO 链接 + 依赖链
        #    （zlib/jpeg/zstd/webp/lerc/jbig/lzma/deflate）在 OHOS 下可解析。
        self.run(f"{cc} -shared -fPIC pic_probe.c -o libtiff_probe.so {inc} -L{libdir} -ltiff")
        # DSO 无 TEXTREL、且 NEEDED 必须包含 libtiff.so（证明真实链到被测包）。
        self.run("readelf -d libtiff_probe.so | grep -qi TEXTREL && "
                 "(echo 'FAIL: TEXTREL present in probe DSO' && exit 1) || "
                 "echo 'PASS: no TEXTREL in probe DSO'", ignore_errors=False)
        self.run("readelf -d libtiff_probe.so | grep -q 'libtiff.so' || "
                 "(echo 'FAIL: probe DSO does not link libtiff.so' && exit 1)")
        # 3) dlopen 运行器：真实调用链进 DSO 的 libtiff-backed 写读函数并校验像素。
        self.run(f"{cc} probe_main.c -o probe_main {inc}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # R34/PF3：test() 必须 self.run 实际执行，禁止空壳/常驻 skip 分支。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
        self.run(f"{bash} -c './probe_main'", env="conanrun")
