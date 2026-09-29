import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import copy


# OHOS SDK clang：与 ci/conan/profiles/ohos-aarch64 的
# tools.build:compiler_executables 一致，作为 conf 读不到时的兜底绝对路径。
OHOS_SDK_CLANG = "/data/service/hnp/bin/clang"


class KamailioUnixodbcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _c_compiler(self):
        """定位 e2e 用例的 C 编译器。

        构建/CI harness 会把 CC 导出为裸名字（本机实测 CC=clang），而 test() 内
        subprocess 继承的是 conan 进程环境，不保证 PATH 里有 OHOS SDK bin ——
        构建 #61886 即因此报 FileNotFoundError: 'clang'。故按
        「profile conf（绝对路径）→ OHOS SDK 兜底 → CC/cc/gcc（which 解析）」
        顺序选取，全部不可用才报错。
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
        """被测包及其传递依赖（如 unixodbc）提供的 libdir 列表。"""
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
        # R34 实质验证：对打包产物 db_unixodbc.so 做真实检查
        # （ELF 架构 / unixODBC 动态依赖 / 模块 API 符号 / 许可证文件）
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        module = os.path.join(package_folder, "lib", "kamailio", "modules", "db_unixodbc.so")
        assert os.path.isfile(module), f"db_unixodbc.so not found at {module}"
        self.output.info(f"db_unixodbc.so found: {module}")

        checker = os.path.join(self.source_folder, "check_db_unixodbc.py")
        env = Environment()
        env.define("DB_UNIXODBC_MODULE", module)
        env.define("DB_UNIXODBC_PACKAGE_FOLDER", package_folder)
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')

        # rule12 鸿蒙特有端到端消费者用例：真实走通
        # dlopen(db_unixodbc.so) -> dlsym(db_bind_api) -> 绑定 db_func_t
        # -> use_table/init 调用链（模拟 kamailio core 的 loadmodule 消费路径），
        # 而非仅产物结构断言。编译器由 _c_compiler() 解析（不依赖裸 CC）。
        #
        # 模块是 core 插件（引用 db_use_table/db_do_init/_pkg_root 等 core 符号），而
        # OHOS/musl 的加载器不做惰性绑定——dlopen 时全部未定义符号都要解析完，故必须把
        # kamailio_core_stub.c（最小 core 符号层）一并编译进测试可执行文件，并用
        # -Wl,--export-dynamic 导出其符号供 dlopen 解析。
        e2e_src = os.path.join(self.source_folder, "test_db_unixodbc_e2e.c")
        stub_src = os.path.join(self.source_folder, "kamailio_core_stub.c")
        e2e_bin = os.path.join(self.build_folder, "test_db_unixodbc_e2e")
        cc = self._c_compiler()
        self.output.info(f"e2e compiler: {cc}")
        inc = os.path.join(package_folder, "include")
        cmd = [cc, "-std=c11", e2e_src, stub_src, "-o", e2e_bin,
               "-I", self.source_folder, "-Wl,--export-dynamic", "-ldl"]
        if os.path.isdir(inc):
            cmd += ["-I", inc]
        subprocess.run(cmd, check=True)

        # 运行时库搜索路径：模块目录 + 依赖 libdir。db_unixodbc.so 的 NEEDED 含
        # libodbc.so.2（unixodbc 包提供），只给模块目录时 dlopen 会失败
        # （本地 conan test 实测 "Error loading shared library libodbc.so.2"）。
        lib_dirs = []
        for cand in [os.path.join(package_folder, "lib")] + self._dep_lib_dirs():
            if cand and os.path.isdir(cand) and cand not in lib_dirs:
                lib_dirs.append(cand)
        self.output.info(f"e2e LD_LIBRARY_PATH entries: {lib_dirs}")

        e2e_env = Environment()
        e2e_env.define("DB_UNIXODBC_MODULE", module)
        for lib_dir in lib_dirs:
            e2e_env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        with e2e_env.vars(self).apply():
            self.run(f'"{e2e_bin}" "{module}"')
