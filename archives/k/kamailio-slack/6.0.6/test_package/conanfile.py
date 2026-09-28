import os
import sys

from conan import ConanFile
from conan.tools.env import Environment


class KamailioSlackTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 层 1 产物结构检查（ELF 架构 / 动态依赖 / loadmodule 入口符号 / 许可证）
        # + 层 2 消费者 E2E（以最小 kamailio 核心桩 dlopen 产物，真实执行模块代码路径）
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        module = os.path.join(package_folder, "lib", "kamailio", "modules", "slack.so")
        assert os.path.isfile(module), f"slack.so not found at {module}"
        self.output.info(f"slack.so found: {module}")

        # 层 2 需要：交叉编译器、E2E 宿主源码、依赖库目录（slack.so 的 DT_NEEDED 含
        # libcurl.so，由 curl 包的 lib 目录经 LD_LIBRARY_PATH 解析）
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

        checker = os.path.join(self.source_folder, "check_slack.py")
        env = Environment()
        env.define("SLACK_MODULE", module)
        env.define("SLACK_PACKAGE_FOLDER", package_folder)
        env.define("SLACK_E2E_SRC", e2e_src)
        env.define("SLACK_CC", cc)
        env.define("SLACK_DEP_LIBDIRS", os.pathsep.join(libdirs))
        env.define("SLACK_BUILD_DIR", os.path.join(self.build_folder, "e2e"))
        self.output.info(f"E2E compiler: {cc}")
        self.output.info(f"E2E dependency libdirs: {libdirs}")
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')
