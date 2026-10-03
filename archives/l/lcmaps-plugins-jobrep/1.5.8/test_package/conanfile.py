# test_package/conanfile.py — lcmaps-plugins-jobrep 1.5.8 consumer test
"""L1 test: 编译并链接 liblcmaps_jobrep，真实调用插件入口点
（plugin_initialize / plugin_introspect / plugin_terminate）验证插件可被
消费者正常链接与调用（R34：非空壳测试）。

插件 .so 内的 lcmaps_* / OpenSSL 符号由宿主 LCMAPS 进程提供，上游
Makefile.am 的 LIBADD 被注释；本测试显式链接 lcmaps 与 OpenSSL 依赖以满足
链接器解析。
"""
import os

from conan import ConanFile


class LcmapsPluginsJobrepTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 插件运行期由宿主提供这些符号，上游 LIBADD 为空；消费者测试需显式
        # 链接才能解析 lcmaps_log*/lcmaps_cntArgs 与 OpenSSL 符号。
        # 版本与主配方 requirements() 保持一致。
        self.requires("lcmaps/1.6.7")
        self.requires("unixodbc/2.3.12")
        self.requires("openssl/3.5.6")

    def build(self):
        # TMPDIR 注入：鸿蒙安全框架拦截编译器在默认 /tmp 创建临时文件（R10）
        tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = tmp_dir

        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c") or "clang"
        src = os.path.join(self.source_folder, "test_jobrep.c")
        out = os.path.join(self.build_folder, "test_jobrep")

        inc, ld = [], []
        for dep in self.dependencies.values():
            pkg_folder = dep.package_folder
            if not pkg_folder:
                continue
            inc.append(f"-I{os.path.join(pkg_folder, 'include')}")
            lib_dir = os.path.join(pkg_folder, "lib")
            if os.path.isdir(lib_dir):
                ld.append(f"-L{lib_dir}")
            # 插件安装在 lib/lcmaps/ 子目录（MODULEDIR）
            plugin_dir = os.path.join(pkg_folder, "lib", "lcmaps")
            if os.path.isdir(plugin_dir):
                ld.append(f"-L{plugin_dir}")

        self.run(
            f"{cc} {src} -o {out} {' '.join(inc)} {' '.join(ld)} "
            f"-llcmaps_jobrep -llcmaps_without_gsi -lodbc -lcrypto")

    def test(self):
        exe = os.path.join(self.build_folder, "test_jobrep")
        # LD_LIBRARY_PATH 注入运行时 .so 目录：liblcmaps_jobrep.so 位于
        # lib/lcmaps/，liblcmaps_without_gsi.so.0 / libodbc.so / libcrypto.so
        # 位于各自包的 lib/（同 globus-gsi-openssl-error 4.4 先例）
        libs = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for lib_dir in (os.path.join(dep.package_folder, "lib"),
                            os.path.join(dep.package_folder, "lib", "lcmaps")):
                if os.path.isdir(lib_dir) and lib_dir not in libs:
                    libs.append(lib_dir)
        self.run(f'LD_LIBRARY_PATH="{os.pathsep.join(libs)}" {exe}')
