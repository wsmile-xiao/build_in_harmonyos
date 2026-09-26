import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # VirtualRunEnv / VirtualBuildEnv 必须显式写：只写 PkgConfigDeps 会替换掉
    # conan 默认 generator 集，缺 VirtualRunEnv 时 test() 拿不到 LD_LIBRARY_PATH。
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # libgcobol 无对外头文件，只需 -L 与 -lgcobol。
        dep = self.dependencies["libgcobol"].cpp_info
        libdirs = list(dep.libdirs)
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-lgcobol"]
                        + ["-Wl,-rpath," + p for p in libdirs])
        # OHOS 只有 LLVM 工具链，且 clang++ 不在默认 PATH，用绝对路径兜底。
        cxx = os.environ.get("CXX") or "/data/service/hnp/bin/clang++"
        std_flag = ""
        _std = self.settings.get_safe("compiler.cppstd")
        if _std:
            std_flag = "-std=c++%s" % str(_std).replace("gnu", "")
        self.run("%s %s test.cpp -o test_probe %s" % (cxx, std_flag, link),
                 env="conanbuild")

    def _resolve_gcobol(self):
        """探测 GCOBOL 前端：环境变量 GCOBOL → 真机 build tree（本机适配结果）→ PATH。"""
        cands = [
            os.environ.get("GCOBOL", ""),
            "/storage/Users/currentUser/gcobol-obj/gcc/gcobol",
        ]
        for c in cands:
            if c and os.path.isfile(c) and os.access(c, os.X_OK):
                return c
        return shutil.which("gcobol") or ""

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # 被测包 libgcobol 的 libdir（端到端链接/加载被测库用）
        dep = self.dependencies["libgcobol"].cpp_info
        libgcobol_libdirs = list(dep.libdirs)
        # ABI 探针运行需要 libgcobol 及其传递依赖（libxml2）的 libdir
        ldpath = os.pathsep.join(dict.fromkeys(
            [p for _ref, _d in self.dependencies.items() for p in _d.cpp_info.libdirs]))
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # 1) ABI 探针：链接被测 libgcobol 的 __gg__power_of_ten，做真实计算断言
        self.run(
            "%s -c 'export LD_LIBRARY_PATH=\"%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\"; ./test_probe'"
            % (bash, ldpath),
            env="conanrun",
        )
        # 2) 端到端 COBOL 程序（需 GCOBOL 前端）：前端不可用则如实 [SKIP]，绝不伪造通过。
        #    前端可用时把被测包 libdir 与前端路径传给 test.sh，消费被测包做端到端验证。
        gcobol = self._resolve_gcobol()
        if not gcobol:
            self.output.info(
                "[SKIP] GCOBOL 前端不可用（gcobol/16.1.0 尚未作为 Conan 制品发布），"
                "端到端 COBOL 程序测试未执行；本包已消费被测包完成 ABI 探针验证。"
                "端到端验证由 feat/gcobol-16.1.0 承担（cobol.dg 464 项 + COMPUTE 消费者断言）。"
            )
            return
        self.run(
            'LIBGCOBOL_LIBDIR="%s" GCOBOL="%s" sh test.sh' % (libgcobol_libdirs[0], gcobol),
            env="conanrun",
        )
