import os

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式声明，确保 test() 里一定能从依赖图取到 python（lxml 6.1.1 同款）
        self.requires("python/3.12.9")

    def test(self):
        if not can_run(self):
            return
        # R34: 必须实质依赖被测包
        pkg = self.dependencies["cython"].package_folder
        test_script = os.path.join(self.source_folder, "test_cython.py")

        # 解释器用 **conan python 制品**的，且 LD_LIBRARY_PATH 必须**内联 export**：
        #
        # 1) 原实现硬编码 `/data/service/hnp/bin/python3`（沙箱 PATH 无 python3）。
        #    该解释器在 CI 上自身就以 NEEDED 依赖 libpython3.12.so.1.0，而该库
        #    不在它的默认搜索路径里，于是**解释器还没启动**就退出：
        #      Error loading shared library libpython3.12.so.1.0: (needed by
        #        /data/service/hnp/bin/python3)
        #      Error relocating /data/service/hnp/bin/python3:
        #        Py_BytesMain: symbol not found
        #      ConanException: Error 127
        #    本机无该路径（CI 专有），故本地测试曾走 sys.executable 回退而通过
        #    ——典型的「本地绿、CI 红」。
        # 2) 不能依赖 `env="conanrun"` 来注入 LD_LIBRARY_PATH：本平台实测
        #    self.run(env=...) 不真正传递变量（详见 conanfile.py 同款说明），
        #    而 conanrun 脚本本身是能导出的。故照 lxml 6.1.1 / gpgmepy 2.0.0 的
        #    做法**在命令串里显式 export**，把 conan python 包（及全部依赖）的
        #    lib 目录喂给动态 loader。
        py_pkg = self.dependencies["python"].package_folder
        py_bin = os.path.join(py_pkg, "bin", "python3.12")
        lib_dirs = [os.path.join(py_pkg, "lib")]
        for dep in self.dependencies.values():
            if dep.package_folder:
                lib_dirs.append(os.path.join(dep.package_folder, "lib"))
        ld_path = os.pathsep.join([d for d in lib_dirs if os.path.isdir(d)])
        self.run(f'export LD_LIBRARY_PATH="{ld_path}:$LD_LIBRARY_PATH" && '
                 f'"{py_bin}" "{test_script}" "{pkg}"')
