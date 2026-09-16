#!/usr/bin/env python3
"""Conan recipe — cron-apt 0.13.0.1 (纯 POSIX shell 脚本包，无编译).

cron-apt = Debian 工具：通过 cron 自动执行 apt 更新（`apt-get update` /
`dist-upgrade`）。上游是 Debian 原生包（无独立 GitHub 仓库），源码取自
Debian pool。

OHOS 适配说明：
- **纯脚本包，无编译**：上游 `Makefile` 只做 `install -m644/755`。但 OHOS
  无 coreutils `install`（仅 busybox 有 install applet），故本配方**不调用
  `make install`**，改用 conan 的文件工具按 FHS 布局直接落盘。
- **SHAREDIR 自定位**：上游硬编码 `SHAREDIR="/usr/share/cron-apt"` 并
  `. $SHAREDIR/functions`。conan 包无法写系统路径，故 patch 为**脚本自定位**
  （`dirname $0` 的上一级 + `share/cron-apt`），并支持 `CRON_APT_SHAREDIR`
  环境变量覆盖。这与仓库既有纯脚本包（bork）的处理思路一致。
- **运行时依赖 apt**：cron-apt 的实际功能需要 `apt`/`apt-get`（代码中 40 处
  引用）。OHOS 上暂无 apt 适配——**这不影响出包与脚本自身运行**（`--help`
  实测 rc=0），但包不执行时无法真正驱动包更新，manifest 已如实声明。
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get


class CronAptConan(ConanFile):
    name = "cron-apt"
    version = "0.13.0.1"
    description = ("cron-apt — automatic update of packages using apt-get "
                   "(Debian tool, pure POSIX shell)")
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/cron-apt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._patch_sharedir()

    def _patch_sharedir(self):
        """把硬编码的 SHAREDIR=/usr/share/cron-apt 改为脚本自定位。

        上游 src/cron-apt 第 195 行 `SHAREDIR="/usr/share/cron-apt"`，随后
        `. $SHAREDIR/functions` 加载辅助函数。包内布局为
        `<pkg>/bin/cron-apt` + `<pkg>/share/cron-apt/functions`，
        故按 `dirname $0` 的上一级推导，并允许 CRON_APT_SHAREDIR 覆盖。
        """
        p = os.path.join(self.source_folder, "src", "cron-apt")
        if not os.path.isfile(p):
            return
        t = open(p, encoding="utf-8", errors="ignore").read()
        old = 'SHAREDIR="/usr/share/cron-apt"'
        if old not in t:
            return
        new = (
            '# OHOS 适配：脚本自定位（包内 ../share/cron-apt），'
            '支持 CRON_APT_SHAREDIR 覆盖\n'
            'if [ -n "${CRON_APT_SHAREDIR:-}" ] ; then\n'
            '    SHAREDIR="$CRON_APT_SHAREDIR"\n'
            'else\n'
            '    SHAREDIR="$(cd "$(dirname "$0")/../share/cron-apt" 2>/dev/null '
            '&& pwd -P)"\n'
            '    if [ ! -d "$SHAREDIR" ] ; then\n'
            '        SHAREDIR="/usr/share/cron-apt"\n'
            '    fi\n'
            'fi'
        )
        t = t.replace(old, new, 1)
        open(p, "w", encoding="utf-8").write(t)
        self.output.info("patched src/cron-apt: SHAREDIR 自定位 + CRON_APT_SHAREDIR 覆盖")

    def package(self):
        sf = self.source_folder
        pf = self.package_folder
        # 主程序（可执行）
        copy(self, "cron-apt", src=os.path.join(sf, "src"),
             dst=os.path.join(pf, "bin"), keep_path=False)
        # 辅助函数（cron-apt 运行时 source）
        copy(self, "functions", src=os.path.join(sf, "src"),
             dst=os.path.join(pf, "share", "cron-apt"), keep_path=False)
        # cron.d / logrotate 配置
        copy(self, "cron.d", src=os.path.join(sf, "src"),
             dst=os.path.join(pf, "etc", "cron.d"), keep_path=False)
        copy(self, "logrotate", src=os.path.join(sf, "src"),
             dst=os.path.join(pf, "etc", "logrotate.d"), keep_path=False)
        # 配置与动作脚本
        copy(self, "config", src=os.path.join(sf, "conf"),
             dst=os.path.join(pf, "etc", "cron-apt"), keep_path=False)
        for pat in ("0-update", "3-download", "9-notify"):
            copy(self, pat, src=os.path.join(sf, "conf"),
                 dst=os.path.join(pf, "etc", "cron-apt", "action.d"),
                 keep_path=False)
        # man 手册（上游 conf/man 已生成 .gz；缺失则从 man/ 取）
        copy(self, "*.1", src=os.path.join(sf, "man"),
             dst=os.path.join(pf, "share", "man", "man1"), keep_path=False)
        copy(self, "*.8*", src=os.path.join(sf, "man"),
             dst=os.path.join(pf, "share", "man", "man8"), keep_path=False)
        # 文档示例
        copy(self, "README", src=sf, dst=os.path.join(pf, "share", "doc", "cron-apt"),
             keep_path=False)
        copy(self, "COPYING", src=sf, dst=os.path.join(pf, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # 运行时数据目录（cron-apt 通过 SHAREDIR 找 functions；包内自定位即可，
        # 此处同时暴露给消费者便于显式设置 CRON_APT_SHAREDIR）
        self.cpp_info.resdirs = ["share"]
        self.output.info("cron-apt: 纯 shell 脚本包；实际更新功能依赖 apt（OHOS 暂无）")
