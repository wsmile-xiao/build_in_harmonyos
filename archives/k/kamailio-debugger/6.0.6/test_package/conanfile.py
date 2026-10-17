import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


# OHOS SDK clang：与 ci/conan/profiles/ohos-aarch64 的
# tools.build:compiler_executables 一致，作为 conf 读不到时的兜底绝对路径。
OHOS_SDK_CLANG = "/data/service/hnp/bin/clang"


class KamailioDebuggerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _c_compiler(self):
        """定位 e2e 用例的 C 编译器。

        构建/CI harness 会把 CC 导出为裸名字，而 test() 内 subprocess 继承的是 conan
        进程环境，不保证 PATH 里有 OHOS SDK bin（同族先例 kamailio-unixodbc 构建
        #61886 即因此报 FileNotFoundError: 'clang'）。故按「profile conf（绝对路径）→
        OHOS SDK 兜底 → CC/cc/gcc（which 解析）」顺序选取，全部不可用才报错。
        """
        exes = {}
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:  # conf 跨上下文不可读时退化为路径探测
            pass
        tried = []
        for cand in (exes.get("c"), OHOS_SDK_CLANG, os.environ.get("CC"),
                     "clang", "cc", "gcc"):
            if not cand:
                continue
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
            found = shutil.which(cand)
            if found:
                return found
            tried.append(cand)
        raise ConanException(f"e2e: no usable C compiler (tried: {', '.join(tried)})")

    def test(self):
        # R34 实质验证：对打包产物 debugger.so 做真实检查
        # （ELF 架构 / 动态依赖 / core 插件 API 导出 / 许可证文件）
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        module = os.path.join(package_folder, "lib", "kamailio", "modules", "debugger.so")
        assert os.path.isfile(module), f"debugger.so not found at {module}"
        self.output.info(f"debugger.so found: {module}")

        checker = os.path.join(self.source_folder, "check_debugger.py")
        env = Environment()
        env.define("DEBUGGER_MODULE", module)
        env.define("DEBUGGER_PACKAGE_FOLDER", package_folder)
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')

        # 消费者端到端用例：真实走通
        #   dlopen(debugger.so) -> dlsym(exports) -> 重放 core 的描述符/参数表加载
        #   -> dbg_init_rpc() 注册 8 个 RPC 方法 -> 按描述符调用命令处理函数与 fixup
        #   （含非法参数负例）-> destroy_mod_f 生命周期闭环 -> dlclose
        # 而非仅产物结构断言。
        #
        # 模块是 core 插件（引用 core 的 dprint/cfg/rpc/pv 等符号），而 OHOS/musl 的加载器
        # 不做惰性绑定——dlopen(RTLD_LAZY) 等价于 RTLD_NOW，库内所有未定义符号必须在加载时
        # 解析完，故必须把 kamailio_core_stub.c（最小 core 符号层）一并编译进测试可执行文件，
        # 并用 -Wl,--export-dynamic 导出其符号供 dlopen 解析。
        e2e_src = os.path.join(self.source_folder, "test_debugger_e2e.c")
        stub_src = os.path.join(self.source_folder, "kamailio_core_stub.c")
        e2e_bin = os.path.join(self.build_folder, "test_debugger_e2e")
        cc = self._c_compiler()
        self.output.info(f"e2e compiler: {cc}")
        cmd = [cc, "-std=c11", e2e_src, stub_src, "-o", e2e_bin,
               "-I", self.source_folder, "-Wl,--export-dynamic", "-ldl"]
        subprocess.run(cmd, check=True)

        # 运行时库搜索路径：模块目录（debugger.so 的 NEEDED 仅 libc，此处置入是防御性配置）
        lib_dir = os.path.join(package_folder, "lib", "kamailio", "modules")
        e2e_env = Environment()
        if os.path.isdir(lib_dir):
            e2e_env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        with e2e_env.vars(self).apply():
            self.run(f'"{e2e_bin}" "{module}"')
