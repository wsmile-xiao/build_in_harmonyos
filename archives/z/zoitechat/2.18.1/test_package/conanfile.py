import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment


class ZoitechatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # 被测包为 application 类型：Conan 不为其生成 CMake interface target，
    # 因此直接编译消费者测试源码，显式使用被测包安装的头文件与产物。
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 被测包 package_type = "application"，其 requires 不会传递给消费者，
        # 因此 test_package 顶层图中缺少部分运行时依赖（实测缺 openssl/
        # libarchive/lua），导致运行被测程序报 libarchive.so.13 缺失（127）。
        # test_package 允许额外声明依赖；这里显式补齐承载共享库的直接依赖，
        # 使运行环境（LD_LIBRARY_PATH）完整、确定性可复现。
        for ref in ("openssl/3.5.6", "libarchive/3.8.7", "lua/5.4.8"):
            self.requires(ref)

    def _dep(self):
        return self.dependencies[self.tested_reference_str]

    def _cc(self):
        # test_package 上下文的 conf 通常为空，直接从 PATH 解析（与 profile
        # 的 [buildenv] PATH 一致），拿不到再回退 profile 里的编译器 conf。
        for cand in ("clang", "cc", "gcc"):
            found = shutil.which(cand)
            if found:
                return found
        return self.conf.get(
            "tools.build:compiler_executables:c",
            default="clang",
            check_type=str,
        )

    # 被测包名（本 test_package 专属常量）。
    TESTED_NAME = "zoitechat"

    def _runtime_nodes(self):
        """返回被测程序的完整依赖节点集合。

        被测包 package_type = "application"，Conan 不会把它的依赖传递给消费者，
        因此 test_package 顶层 self.dependencies.host 缺少部分直接依赖
        （实测缺 openssl/libarchive/lua/libepoxy 等），直接运行被测程序会报
        `Error loading shared library libarchive.so.13`（退出码 127）。
        正确做法：在顶层图中按 ref.name 找到被测包节点，再用该节点的
        .dependencies.host 取完整子树（实测可得到全部 28 个依赖）。
        """
        nodes = list(self.dependencies.host.values())
        target = None
        for dep in nodes:
            ref = getattr(dep, "ref", None)
            if ref is not None and getattr(ref, "name", None) == self.TESTED_NAME:
                target = dep
                break
        if target is not None:
            try:
                nodes.extend(target.dependencies.host.values())
            except Exception:  # noqa: BLE001 - 老版本 Conan 无该 API 时退回顶层图
                pass
        return nodes

    def _runtime_env(self):
        """构造被测程序运行所需的动态库搜索路径（prepend 语义）。

        用 Environment 的 prepend 语义（保留 profile 注入的原有
        LD_LIBRARY_PATH），直接整体赋值会清空系统库路径。
        """
        env = Environment()
        seen = set()
        for dep in self._runtime_nodes():
            pkg = dep.package_folder
            if not pkg:
                continue
            for sub in ("lib", "lib64", "bin"):
                cand = os.path.join(pkg, sub)
                if os.path.isdir(cand) and cand not in seen:
                    seen.add(cand)
                    if sub == "bin":
                        env.prepend_path("PATH", cand)
                    else:
                        env.prepend_path("LD_LIBRARY_PATH", cand)
        return env

    def build(self):
        dep = self._dep()
        include_dir = os.path.join(dep.package_folder, "include")
        source = os.path.join(self.source_folder, "test.c")
        output = os.path.join(self.build_folder, "test_zoitechat")
        self.run(
            f'"{self._cc()}" -std=c17 -O2 -o "{output}" "{source}" '
            f'-I"{include_dir}" -ldl'
        )

    def test(self):
        dep = self._dep()
        consumer = os.path.join(self.build_folder, "test_zoitechat")
        plugin_dir = os.path.join(dep.package_folder, "lib", "zoitechat", "plugins")
        binary = os.path.join(dep.package_folder, "bin", "zoitechat")

        with self._runtime_env().vars(self).apply():
            # 1) 消费者程序：使用被测包头文件 + 校验包内插件产物
            self.run(f'"{consumer}" "{plugin_dir}"')
            # 2) 真实执行被测程序本体（R34：必须执行被测包二进制）
            self.run(f'"{binary}" --version')
