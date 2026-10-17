#!/usr/bin/env python3
"""Conan recipe — munin-c 0.0.13 (Munin node in C, Autotools).

Munin 采集节点的 C 实现：munin-node-c（节点守护进程）、munin-inetd-c
（inetd 方式节点）、munin-plugins-c（多合一插件，按 argv0 basename 分发
cpu/df/entropy 等子命令），以及 t/ 下的测试辅助程序 ok_plugin / nb_env
（上游自带的插件协议模拟器，随 sbin_PROGRAMS 安装）。

构建系统 Autotools；GitHub tag 压缩包不含生成的 configure，需在 build()
先 autoreconf -fi。configure.ac 用 AM_MAINTAINER_MODE([enable])，向
configure 传 --disable-maintainer-mode 关闭自动再生成规则。

E386 shell 路由：profile [buildenv] 的 CONFIG_SHELL/SHELL 指向 hnp bash
（HMDFS 上 getcwd 挂，configure 第一步报 working directory cannot be
determined）；工具链 env 会被 profile buildenv 覆盖，唯一可靠位置是
build() 内联 env 前缀。候选 shell 实跑探测（禁 os.access X_OK，E524），
优先 tool_requires 的 bash/5.3（CI worker PATH 无 harmonybrew bash），
回退 /bin/sh。

上游测试清点（R51）：全仓无 TESTS/check-* 注册（t/Makefile.am 仅把
ok_plugin/nb_env 作为 sbin_PROGRAMS 构建），`make check` 无实际测试集，
N_static = 0；验证由 test_package 消费者测试承载——复用上游自己的
ok_plugin 协议模拟器 + 多合一插件 argv0 分发做真实行为断言。
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class MuninCConan(ConanFile):
    name = "munin-c"
    version = "0.0.13"
    description = "Munin monitoring node and plugins in C (munin-node-c/munin-plugins-c)"
    license = "GPL-2.0-or-later OR GPL-3.0-only"
    homepage = "https://github.com/munin-monitoring/munin-c"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # E386：CI worker PATH 上没有可用 bash（harmonybrew 不存在），
        # 制品仓已发布的 bash/5.3 作为构建期 shell（configure 探针/重执行需要）
        self.tool_requires("bash/5.3")
        # CI worker 只有 autoconf 家族没有 automake（aclocal 缺失致裸
        # autoreconf 失败，PR #10692 首轮 CI 实证）。同 abiword-plugin-docbook
        # 先例：tool_requires(automake) 经 buildenv 注入 $ACLOCAL/$AUTOMAKE
        # 绝对路径，build() 内用变量形式调用，不依赖 PATH。
        self.tool_requires("automake/1.18")

    def validate(self):
        # R32: 平台判断用 in，不用 == "Linux"
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration(
                f"munin-c not validated for {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-maintainer-mode")
        tc.generate()

    def _probe_shell(self):
        """E386/E524：实跑探测 getcwd 可用的 shell（HMDFS 下 hnp bash 必挂）。"""
        candidates = []
        try:
            bash = self.dependencies.build["bash"]
            candidates.append(os.path.join(bash.package_folder, "bin", "bash"))
        except KeyError:
            pass
        candidates.append("/bin/sh")
        for sh in candidates:
            if not os.path.isfile(sh):
                continue
            try:
                probe = subprocess.run(
                    [sh, "-c", "pwd"],
                    cwd=self.build_folder, capture_output=True,
                    text=True, timeout=30,
                )
                if probe.returncode == 0 and not (probe.stderr or "").strip():
                    return sh
            except (OSError, subprocess.TimeoutExpired):
                continue
        raise ConanInvalidConfiguration(
            "E386: no working shell found (hnp bash getcwd broken on HMDFS)"
        )

    def build(self):
        apply_conandata_patches(self)
        # GitHub tag 压缩包不含生成的 configure/aclocal.m4/Makefile.in；
        # 绕 autoreconf 链（HMDFS 上 autoconf.m4f 加载冲突 + CI worker 无
        # automake），按 abiword-plugin-docbook 先例直跑三段链：aclocal →
        # automake → autoconf（${ACLOCAL}/${AUTOMAKE} 为 tool_requires 注入的
        # 绝对路径，CI 干净 PATH 可用）
        # AC_CONFIG_AUX_DIR([build])：辅助脚本目录须先存在，否则 automake
        # --add-missing --copy 静默失败，configure 报 cannot find required
        # auxiliary files
        self.run("mkdir -p build m4", cwd=self.source_folder, env="conanbuild")
        self.run(
            '${ACLOCAL:-aclocal} --force -I m4',
            cwd=self.source_folder, env="conanbuild", ignore_errors=True,
        )
        self.run(
            '${AUTOMAKE:-automake} --add-missing --copy --foreign -f',
            cwd=self.source_folder, env="conanbuild", ignore_errors=True,
        )
        self.run(
            "autoconf -o configure configure.ac",
            cwd=self.source_folder, env="conanbuild", ignore_errors=True,
        )
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            raise ConanInvalidConfiguration(
                "autoconf failed to generate configure"
            )
        # E011/E114：autoconf 模板以 umask 077 建 config.status 临时目录，
        # HMDFS 上随后读取被拒（subs1.awk Permission denied）→ 放宽 umask。
        # 版本改由补丁 0002 固化为 0.0.13（getversion 目录名回退在 conan
        # source 缓存里失效，报 unknown）。
        self.run("sed -i 's/umask 077/umask 022/' configure", cwd=self.source_folder, env="conanbuild")
        # E386：CONFIG_SHELL/SHELL 只能在 run 命令的内联 env 前缀覆盖
        # （profile buildenv 在 conanbuild.sh 里 source 顺序靠后会赢），
        # 因此 configure/make 手动调用而非 Autotools helper。
        sh = self._probe_shell()
        inline = 'CONFIG_SHELL="%s" SHELL="%s" "%s"' % (sh, sh, sh)
        self.run(
            inline + ' ../configure --prefix="%s" --disable-maintainer-mode'
            % self.package_folder,
            cwd=self.build_folder, env="conanbuild",
        )
        # make 不经 CONFIG_SHELL（GNU make 自用 /bin/sh，且 hnp make 在
        # 探针 bash 下 exec 失败 E524 家族）；编译规则直接 exec，无 getcwd 依赖
        self.run("make -j2", cwd=self.build_folder, env="conanbuild")
        # 上游无 TESTS 注册（见文件头清点），无 make check 测试集可执行

    def package(self):
        # configure --prefix 已指向 package_folder，make install 落位
        self.run("make install -j2", cwd=self.build_folder, env="conanbuild")

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # autotools sbin_PROGRAMS → <prefix>/sbin
        self.cpp_info.bindirs = ["sbin"]
        sbin_path = os.path.join(self.package_folder, "sbin")
        if os.path.isdir(sbin_path):
            self.runenv_info.append_path("PATH", sbin_path)
