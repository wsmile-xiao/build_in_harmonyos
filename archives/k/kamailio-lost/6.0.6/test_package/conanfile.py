import os
import sys

from conan import ConanFile
from conan.tools.env import Environment


class KamailioLostTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 层 1 产物结构检查（ELF 架构 / 动态依赖含 libxml2+libcurl / loadmodule 入口符号 / 许可证）
        # + 层 2 消费者 E2E（以最小 kamailio 核心桩 dlopen 产物，真实执行 HELD 全链路）
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        module = os.path.join(package_folder, "lib", "kamailio", "modules", "lost.so")
        assert os.path.isfile(module), f"lost.so not found at {module}"
        self.output.info(f"lost.so found: {module}")

        # 层 2 需要：交叉编译器、E2E 宿主源码、依赖库目录
        # （lost.so 的 DT_NEEDED 含 libxml2.so.16 与 libcurl.so，分别由 libxml2 / curl
        #   包的 lib 目录经 LD_LIBRARY_PATH 解析——两个依赖都必须列进来）
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or compilers.get("cpp") or "clang"

        libdirs = []
        for dep in self.dependencies.values():
            dep_pkg = dep.package_folder
            if not dep_pkg:
                continue
            libdir = os.path.join(dep_pkg, "lib")
            if os.path.isdir(libdir):
                libdirs.append(libdir)

        e2e_src = os.path.join(self.source_folder, "e2e_consumer.c")
        assert os.path.isfile(e2e_src), f"E2E consumer source not found at {e2e_src}"

        checker = os.path.join(self.source_folder, "check_lost.py")
        env = Environment()
        env.define("LOST_MODULE", module)
        env.define("LOST_PACKAGE_FOLDER", package_folder)
        env.define("LOST_E2E_SRC", e2e_src)
        env.define("LOST_CC", cc)
        env.define("LOST_DEP_LIBDIRS", os.pathsep.join(libdirs))
        env.define("LOST_BUILD_DIR", os.path.join(self.build_folder, "e2e"))
        self.output.info(f"E2E compiler: {cc}")
        self.output.info(f"E2E dependency libdirs: {libdirs}")
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')