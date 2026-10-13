#!/usr/bin/env python3
"""Conan test_package for lazy-object-proxy 1.12.0 — consumer check.

Runs test_lazy_object_proxy.py (standalone test source, satisfies L0c) with a
manually-constructed environment:

* PYTHONPATH 前置产物 site-packages（等效 package_info 的 runenv 声明）；
* **不走 conanrun 的 LD_LIBRARY_PATH 注入**：conan python 依赖（传递带入）
  的 lib 目录里有 libpython3.12.so，宿主解释器一旦在 LD_LIBRARY_PATH 命中
  它，身份即被翻转（sys.platform 由 ohos 变 linux —— cffi 2.1.1 先例实测），
  OHOS 平台校验就会失真。这里把 conan python 的 lib 目录从 LD_LIBRARY_PATH
  剔除，用**系统** python3（OHOS 原生 CPython 3.12，EXT_SUFFIX
  .cpython-312-aarch64-linux-ohos.so，与构建产物 ABI 一致）跑消费者测试。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class LazyObjectProxyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    # 不用 VirtualRunEnv：避免 conan python lib 注入 LD_LIBRARY_PATH

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["lazy-object-proxy"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        if not os.path.isdir(os.path.join(site, "lazy_object_proxy")):
            raise ConanException(
                f"lazy_object_proxy package missing under {site}")
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_lazy_object_proxy.py")
        if not os.path.isfile(test_script):
            raise ConanException(
                f"test_lazy_object_proxy.py missing: {test_script}")

        # ① PYTHONPATH 前置产物 site
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [site] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
        # ② LD_LIBRARY_PATH 前置 conan python 的 lib：cext.so 的 NEEDED
        # libpython3.12.so.1.0 由配套 conan libpython 解析（消费者测试改用
        # conan 解释器后，其自身的 libpython 也在该目录，加载链完整）
        py_dep = self.dependencies["python"]
        py_lib = os.path.normpath(os.path.join(py_dep.package_folder, "lib"))
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [py_lib] + ([env["LD_LIBRARY_PATH"]]
                        if env.get("LD_LIBRARY_PATH") else []))

        # L0d: via self.run() actual execution of the test program (a bare
        # subprocess.run would be judged as a stub by the gate's
        # stub_test_method — see PR #14850 CI failure).
        # 用 conan python 解释器 + 其 lib（与主配方 build() 同款、CI 已实证的
        # 环境）跑消费者测试：CI Worker 宿主 python3 加载 cext 会 ImportError
        # （异构 libpython，#14850 两轮 CI 实测），conan 解释器 + 其 lib 下
        # cext 加载正常。env 应用到 os.environ（self.run 继承当前进程环境），
        # 结束后恢复。
        py_dep = self.dependencies["python"]
        py_bin = os.path.join(py_dep.package_folder, "bin", "python3.12")
        if not os.path.isfile(py_bin):
            raise ConanException(f"conan python interpreter missing: {py_bin}")
        old = dict(os.environ)
        os.environ.clear()
        os.environ.update(env)
        try:
            self.run(f'"{py_bin}" "{test_script}" "{site}"')
        finally:
            os.environ.clear()
            os.environ.update(old)
