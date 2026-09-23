#!/usr/bin/env python3
"""Conan recipe — ColPack 1.0.10 (graph coloring for sparse Jacobian/Hessian recovery).

上游 https://github.com/CSCsw/ColPack tag v1.0.10（LGPL-3.0-or-later）。
GitHub archive 不含预生成 configure，build() 内先 autoreconf 自举再配置。
"""
import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ColpackConan(ConanFile):
    name = "colpack"
    version = "1.0.10"
    description = "ColPack: A Graph Coloring Algorithm Package for sparse Jacobian and Hessian recovery"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/CSCsw/ColPack"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # 上游 GitHub archive 无预生成 configure（上游 autoconf.sh 用 autoreconf
        # 自举）。CI 沙箱只有 autoconf 家族、没有 automake/libtool，与
        # abiword-plugin-docbook 3.0.8 同法作为 tool_requires 拉入（制品仓已发布）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # 默认静态链接（消费端零运行时 .so 依赖）；shared=True 时交给 libtool 动态
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # 鸿蒙 uname 不被 config.guess 识别（E007），显式传三元组跳过猜测；
        # automake 1.18 的 config.sub 已接受 ohos-linux 三元组（实测）
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        # 1) autoreconf 自举：从 configure.ac 生成 configure/Makefile.in/config.guess 等
        self.run("autoreconf --force --install", cwd=self.source_folder, env="conanbuild")

        # 1b) E490：HMDFS 适配路径可能丢失 autotools 辅助脚本执行位，
        #     chmod +x 兜底（HMDFS 上为 no-op，CI 上恢复执行位）
        self.run(
            "chmod +x configure config.guess config.sub install-sh missing compile depcomp "
            "ltmain.sh test-driver ar-lib aclocal.m4 2>/dev/null || true",
            cwd=self.source_folder,
            env="conanbuild",
        )

        # 2) E011/E114：HMDFS 上 config.status 的 mktemp 临时目录（umask 077 +
        #    setgid，drwx--S---）对当前进程不可写，报 "can't create
        #    ./conf*/subs1.awk: Permission denied"。与 abiword-plugin-docbook
        #    3.0.8 同法：预建可写目录，TMPDIR 指向它，configure 内嵌 ac_tmp
        #    改指该目录，并去掉 trap 的 rm -fr（防 config.status 退出时删目录）。
        if self.settings.os == "OHOS":
            fixed_tmp = os.path.join(tempfile.gettempdir(), "colpack-ac-tmp")
            os.makedirs(fixed_tmp, exist_ok=True)
            os.environ["TMPDIR"] = fixed_tmp
            _cfg_path = os.path.join(self.source_folder, "configure")
            with open(_cfg_path, "r", encoding="utf-8") as _f:
                _cfg = _f.read()
            if "ac_tmp=$tmp" not in _cfg:
                raise ConanException(
                    "E114: ac_tmp=$tmp pattern not found in configure; "
                    "autoconf may have changed the template")
            _cfg = _cfg.replace("ac_tmp=$tmp", "ac_tmp={}".format(fixed_tmp))
            _old_trap = '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status'
            if _old_trap in _cfg:
                _cfg = _cfg.replace(_old_trap, "exit $exit_status")
            with open(_cfg_path, "w", encoding="utf-8") as _f:
                _f.write(_cfg)
            os.chmod(_cfg_path, 0o755)
            self.output.info(
                "  [ok] Patched configure: ac_tmp -> {} + TMPDIR (HMDFS E011/E114)".format(fixed_tmp))

        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # TESTS 示例程序安装目录与 libtool .la 不属于库包交付物
        _examples = os.path.join(self.package_folder, "examples")
        if os.path.isdir(_examples):
            shutil.rmtree(_examples)
        for _root, _dirs, _files in os.walk(self.package_folder):
            for _f in _files:
                if _f.endswith(".la"):
                    os.remove(os.path.join(_root, _f))

    def package_info(self):
        self.cpp_info.libs = ["ColPack"]
