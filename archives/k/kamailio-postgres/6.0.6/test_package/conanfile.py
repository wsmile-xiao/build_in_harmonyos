import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


# OHOS SDK clang：与 ci/conan/profiles/ohos-aarch64 的
# tools.build:compiler_executables 一致，作为 conf 读不到时的兜底绝对路径。
OHOS_SDK_CLANG = "/data/service/hnp/bin/clang"


class KamailioPostgresTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # e2e 二进制与 conan 生成的 env 脚本必须落在 test_package 内的 build/ 子目录，
        # 而不是 test_package 源目录本身（否则 conan create 会在源码归档里留下产物）。
        basic_layout(self)
        self.folders.build = "build"


    def _c_compiler(self):
        """定位 e2e 用例的 C 编译器。

        构建/CI harness 可能把 CC 导出为裸名字，而 test() 内 subprocess 继承的是 conan
        进程环境，不保证 PATH 里有 OHOS SDK bin；故按「profile conf（绝对路径）→
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

    def _dep_lib_dirs(self):
        """被测包及其传递依赖（如 libpq）提供的 libdir 列表。"""
        dirs = []
        try:
            tested = self.dependencies[self.tested_reference_str]
        except Exception:
            return dirs
        for dep in [tested] + list(tested.dependencies.values()):
            try:
                candidates = list(dep.cpp_info.aggregated_components().libdirs)
            except Exception:
                candidates = list(dep.cpp_info.libdirs)
            for cand in candidates:
                if not cand:
                    continue
                path = cand if os.path.isabs(cand) else os.path.join(dep.package_folder, cand)
                if os.path.isdir(path) and path not in dirs:
                    dirs.append(path)
        return dirs

    def test(self):
        # R34 实质验证：对打包产物 db_postgres.so 做真实检查
        # （ELF 结构 / libpq 动态依赖 / BIND_NOW / 模块 API 符号 / 许可证文件）
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        module = os.path.join(package_folder, "lib", "kamailio", "modules", "db_postgres.so")
        assert os.path.isfile(module), f"db_postgres.so not found at {module}"
        self.output.info(f"db_postgres.so found: {module}")

        checker = os.path.join(self.source_folder, "check_db_postgres.py")
        env = Environment()
        env.define("DB_POSTGRES_MODULE", module)
        env.define("DB_POSTGRES_PACKAGE_FOLDER", package_folder)
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')

        # 鸿蒙特有端到端消费者用例：真实走通
        # dlopen(db_postgres.so) -> dlsym(db_postgres_bind_api) -> 绑定 db_func_t
        # -> use_table 调用链（模拟 kamailio core 的 loadmodule 消费路径）。
        # 模块是 core 插件（引用 db_use_table/db_do_init/db_do_init2/_pkg_root 等 core 符号），
        # 且 OHOS/musl 的加载器不做惰性绑定（模块自身亦为 BIND_NOW），故必须把
        # kamailio_core_stub.c（最小 core 符号层）一并编译进测试可执行文件，并用
        # -Wl,--export-dynamic 导出其符号供 dlopen 解析。
        e2e_src = os.path.join(self.source_folder, "test_db_postgres_e2e.c")
        stub_src = os.path.join(self.source_folder, "kamailio_core_stub.c")
        e2e_bin = os.path.join(self.build_folder, "test_db_postgres_e2e")
        cc = self._c_compiler()
        self.output.info(f"e2e compiler: {cc}")
        cmd = [cc, "-std=c11", e2e_src, stub_src, "-o", e2e_bin,
               "-I", self.source_folder, "-Wl,--export-dynamic", "-ldl"]
        subprocess.run(cmd, check=True)

        # 运行时库搜索路径：模块目录 + 依赖 libdir（db_postgres.so 的 NEEDED 含
        # libpq.so.5，由 libpq 包提供；只给模块目录时 dlopen 会失败）。
        lib_dirs = []
        for cand in [os.path.join(package_folder, "lib")] + self._dep_lib_dirs():
            if cand and os.path.isdir(cand) and cand not in lib_dirs:
                lib_dirs.append(cand)
        self.output.info(f"e2e LD_LIBRARY_PATH entries: {lib_dirs}")

        e2e_env = Environment()
        e2e_env.define("DB_POSTGRES_MODULE", module)
        for lib_dir in lib_dirs:
            e2e_env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        with e2e_env.vars(self).apply():
            self.run(f'"{e2e_bin}" "{module}"')

        # 鸿蒙特有端到端消费者用例 2（加载消费链）：扮演 kamailio core 的模块加载器，
        # 按 loadmodule 的真实次序消费模块 —— dlopen(RTLD_NOW) → 解析 kam_exports
        # (module_exports) → 遍历注册 cmds/params → 经注册表调用 db_bind_api →
        # 驱动 db_func_t（use_table 正例 + 负例）。命令表函数指针与模块 ELF 符号
        # db_postgres_bind_api 做独立交叉校验；未建立连接（无 core 连接池/PG 服务端）
        # 时 init 走 SKIP 分支并打印原因。
        consumer_src = os.path.join(self.source_folder, "test_db_postgres_consumer.c")
        consumer_bin = os.path.join(self.build_folder, "test_db_postgres_consumer")
        consumer_cmd = [cc, "-std=c11", consumer_src, stub_src, "-o", consumer_bin,
                        "-I", self.source_folder, "-Wl,--export-dynamic", "-ldl"]
        subprocess.run(consumer_cmd, check=True)
        with e2e_env.vars(self).apply():
            self.run(f'"{consumer_bin}" "{module}"')
