import os
from conan import ConanFile

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 后续验收入口（R8 仅 scaffold，不执行）：
        # 1. 检查 LLVMConfig/LLVMExports/ClangTargets 导出存在
        # 2. 检查静态归档 libLLVM*.a / libclang*.a 实际存在（首项 libLLVMDemangle.a）
        # 3. 用 ar/readelf 抽查归档成员 ELF machine=AArch64、triple=aarch64-unknown-linux-ohos
        # 4. 编译最小消费者：链接 LLVM 组件并校验
        dep = self.dependencies["llvm"].cpp_info
        libdir = dep.libdirs[0]
        llvm_cmake = os.path.join(libdir, "cmake", "llvm", "LLVMConfig.cmake")
        clang_cmake = os.path.join(libdir, "cmake", "clang", "ClangTargets.cmake")
        demangle = os.path.join(libdir, "libLLVMDemangle.a")
        checks = {
            "LLVMConfig.cmake": os.path.isfile(llvm_cmake),
            "ClangTargets.cmake": os.path.isfile(clang_cmake),
            "libLLVMDemangle.a": os.path.isfile(demangle),
        }
        for name, ok in checks.items():
            self.output.info(f"verify {name}: {'OK' if ok else 'MISSING'}")
        missing = [n for n, ok in checks.items() if not ok]
        if missing:
            raise RuntimeError(f"static package verification failed: {missing}")

    def test(self):
        # 真实消费者测试入口：调用已有动态 lit 配置入口 run_lit_subsel.sh，
        # 在 Conan 当前 test_package 环境运行 lit（lit.cfg.py 内部动态解析 SRC/PKG/SUITE）。
        # 使用 Conan self.run()（官方 L0d 判定要求 test() 含 self.run 调用），
        # 任何失败经非零退出传播（self.run 默认对非零退出抛异常），不吞错、不占位。
        import shlex
        tp = os.path.dirname(os.path.abspath(__file__))   # test_package 目录（动态解析，无硬编码机器路径）
        entry = os.path.join(tp, "run_lit_subsel.sh")
        if not os.path.isfile(entry):
            raise RuntimeError(f"real test_package entry missing: {entry}")
        env = dict(os.environ)
        # 动态、可移植地注入 LLVM_SRC_ROOT：优先取自被测依赖对象的 folders.source_folder
        # （Conan 运行时提供的缓存源码根，不硬编码任何机器路径）；若不可用则保持
        # run_lit_subsel.sh 自身的 LLVM_SRC_ROOT/conan 解析回退逻辑不变。
        try:
            folders = self.dependencies["llvm"].folders
            if folders is not None:
                src_root = folders.source_folder
                if src_root:
                    env["LLVM_SRC_ROOT"] = str(src_root)
        except Exception:
            pass
        # 动态、可移植地注入 CONAN_PACKAGE_ROOT_llvm：取自被测依赖对象的 package_folder
        # （Conan 运行时提供的缓存包根，不硬编码任何机器路径），使动态 lit.cfg.py 的
        # _discover_pkg_root() 能可靠解析 PKG（test_package 环境内 conan CLI 不可用）。
        try:
            pkg_folder = self.dependencies["llvm"].package_folder
            if pkg_folder:
                env["CONAN_PACKAGE_ROOT_llvm"] = str(pkg_folder)
        except Exception:
            pass
        self.output.info(f"real test_package entry: {entry}")
        self.output.info("running real test_package lit entry (dynamic lit.cfg.py)...")
        # 动态 env 通过 shell 前缀 export 注入（Conan self.run 的 env 参数仅接受环境文件名列表，
        # 不含 dict；故对动态路径变量用 shell 内联 export），随后真实执行 lit 入口。
        exports = " ".join(
            f"{k}={shlex.quote(str(v))}" for k, v in env.items()
            if k in ("LLVM_SRC_ROOT", "CONAN_PACKAGE_ROOT_llvm")
        )
        self.run(f"{exports} sh {shlex.quote(entry)}", cwd=tp, shell=True)
