import os
import re

from conan import ConanFile
from conan.tools.files import copy, download
from conan.tools.layout import basic_layout


class ConsoleSetupConan(ConanFile):
    name = "console-setup"
    version = "1.248"
    description = ("console-setup - configure text console font and keyboard "
                   "(setupcon(8) + ckbcomp(1) + 744 console fonts, pure "
                   "shell/perl, no C sources)")
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/console-setup"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # 需 shebang 适配的 perl 脚本（tarball 首行 #!/usr/bin/perl 权威清单，
    # setupcon/ckbcomp-mini 为 #!/bin/sh 保留）
    _PERL_SCRIPTS = (
        "Fonts/bdf2psf",
        "Fonts/fbsdmap",
        "Fonts/fontcodesets",
        "Fonts/test_ncurses.pl",
        "Keyboard/KeyboardNames.pl",
        "Keyboard/ckbcomp",
        "Keyboard/compose_translator",
        "Keyboard/dkey_bsd",
        "Keyboard/kbdcompiler",
        "Keyboard/kbdnames-maker",
        "Keyboard/make_charmap_functions",
        "Keyboard/xmlreader",
        "describe_unicodes",
    )

    def requirements(self):
        # 运行期外部命令消费关系（setupcon/ckbcomp 全文核对）：
        #   setupcon → loadkeys/setfont/kbd_mode（kbd 包）
        # gzip/zcat 由 OHOS 基础系统提供（/usr/bin/zcat 实测存在），不声明
        # 注意：tempfile 在 setupcon L64 是 shell 内建函数（非 debianutils
        # 外部命令）；dpkg 未被 setupcon/ckbcomp 消费——与 console-common
        # 不同，本包不声明 dpkg/debianutils
        self.requires("kbd/2.9.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        import hashlib
        tgz = "console-setup_1.248.tar.xz"
        sha256 = self.conan_data["sources"]["sha256"]
        tgz_path = os.path.join(self.source_folder, tgz)
        # 幂等：已存在且 sha256 命中则跳过下载（本地复验网络受限场景；
        # CI 源目录为空走正常下载路径）
        if os.path.isfile(tgz_path):
            with open(tgz_path, "rb") as f:
                digest = hashlib.sha256(f.read()).hexdigest()
            if digest == sha256:
                self.output.info(f"{tgz} 已存在且 sha256 命中，跳过下载")
            else:
                self.output.warning(f"{tgz} sha256 不符（{digest}），重新下载")
                os.remove(tgz_path)
        if not os.path.isfile(tgz_path):
            download(self, self.conan_data["sources"]["url"], tgz,
                     sha256=sha256)
        # get() 在 CI 沙箱 PermissionError（console-common/dpkg 先例）——手动解压
        self.run("tar -xJf console-setup_1.248.tar.xz --no-same-owner || true")
        self.run("cp -a console-setup-1.248/. . && rm -rf console-setup-1.248")

    def _fix_shebang(self, path):
        # shebang 适配：OHOS 无 /usr/bin/perl（perl 由 hnp 提供
        # /data/service/hnp/bin/perl）——house perl shebang 先例。
        # 上游 shebang 带尾随空格（`#!/usr/bin/perl \n`，od 复核 16 字节），
        # 必须用正则容忍行尾空白，精确字符串替换会静默不命中
        with open(path, "r", encoding="utf-8", newline="\n") as f:
            content = f.read()
        content = re.sub(r"^#!\s*/usr/bin/perl[ \t]*\n",
                         "#!/usr/bin/env perl\n", content, count=1,
                         flags=re.MULTILINE)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        os.chmod(path, 0o755)

    def build(self):
        # perl shebang 批量适配（13 文件）
        for rel in self._PERL_SCRIPTS:
            self._fix_shebang(os.path.join(self.source_folder, rel))

        # 上游构建三步（均包内 perl 脚本驱动，零外部 perl 模块依赖）：
        # 1. gzipped-acmfiles：acm/*.acm → acm/*.acm.gz（27 个 charmap 定义，
        #    make 规则 %.gz : %，gzip 来自基础系统）
        # 2. compose-files + dkey-files：compose_translator/dkey_bsd 读 acm
        #    生成 27+27 个 Keyboard/compose.*.inc / dkey.*.inc（~7s）
        # 3. Fonts/gzipped-linux-fonts：bdf2psf 转换 193 个 BDF → 744 个
        #    psf.gz（-j4 ~3min；make -j jobserver 在 OHOS 不可用但 -j4
        #    进程并行实测正常）
        # ekmaps 不预生成：kbdcompiler 单模型 >5min 超时（5 模型 >25min
        # 超 CI 预算），ckbcomp 运行期 -I<ckb> 0.68s/布局等价生成（见 notes）
        self.run("make gzipped-acmfiles", cwd=self.source_folder)
        self.run("make compose-files dkey-files", cwd=self.source_folder)
        self.run("make -C Fonts gzipped-linux-fonts -j4",
                 cwd=self.source_folder)

    def package(self):
        pf = self.package_folder
        # 包布局 = 上游 /usr 前缀映射到 $pkg（setupcon L389-394 与 ckbcomp
        # L42-50 的 installdir 推导在 $pkg/bin 运行时都解析到 $pkg）：
        #   bin/setupcon、bin/ckbcomp
        #   share/consolefonts/（744 psf.gz，findfile share/consolefonts）
        #   share/consoletrans/（acm 原始文件，ckbcomp -charmap 读）
        #   share/console-setup/ckb/（ckbcomp @xdirs 数据）
        #   etc/console-setup/（compose/dkey/remap，ckbcomp L4822-4844 读）
        #   etc/default/（keyboard/console-setup 配置，setupcon L411-418 读）
        for d in ("bin", "share/consolefonts", "share/consoletrans",
                  "share/console-setup", "etc/console-setup", "etc/default",
                  "licenses"):
            os.makedirs(os.path.join(pf, d), exist_ok=True)

        # setupcon：上游 bootprefix/bin（= /bin）→ house bin/（0755，
        # #!/bin/sh 保留）
        copy(self, "setupcon", src=self.source_folder,
             dst=os.path.join(pf, "bin"), keep_path=False)
        os.chmod(os.path.join(pf, "bin", "setupcon"), 0o755)

        # ckbcomp：上游 prefix/bin → bin/（0755，env perl shebang）
        copy(self, "ckbcomp", src=os.path.join(self.source_folder, "Keyboard"),
             dst=os.path.join(pf, "bin"), keep_path=False)
        os.chmod(os.path.join(pf, "bin", "ckbcomp"), 0o755)

        # 744 控制台字体（构建产物 Fonts/*.psf.gz）
        copy(self, "*.psf.gz", src=os.path.join(self.source_folder, "Fonts"),
             dst=os.path.join(pf, "share", "consolefonts"), keep_path=False)

        # acm charmap 原始文件（ckbcomp 搜索顺序第 3 项 .acm 直接读，
        # zcat 路径依赖 .gz——原始文件零运行时工具依赖）
        copy(self, "*.acm", src=os.path.join(self.source_folder, "acm"),
             dst=os.path.join(pf, "share", "consoletrans"), keep_path=False)

        # ckb 数据 → $pkg/etc/console-setup/ckb（上游 Debian 原生安装位置：
        # ckbcomp @xdirs[0]="/etc/console-setup/ckb"、[1]="$installdir/etc/
        # console-setup/ckb"——包布局 $pkg=/usr 时两路径重合，实测 ckbcomp
        # us RC=0；share 路径不在 @xdirs 中）。conan copy() 的 pattern 不匹配
        # 目录内容，用 shutil.copytree 整树复制
        import shutil
        ckb_src = os.path.join(self.source_folder, "Keyboard", "ckb")
        ckb_dst = os.path.join(pf, "etc", "console-setup", "ckb")
        shutil.copytree(ckb_src, ckb_dst)

        # compose/dkey 翻译结果 + remap.inc（ckbcomp -compose 消费）
        copy(self, "compose.*.inc",
             src=os.path.join(self.source_folder, "Keyboard"),
             dst=os.path.join(pf, "etc", "console-setup"), keep_path=False)
        copy(self, "dkey.*.inc",
             src=os.path.join(self.source_folder, "Keyboard"),
             dst=os.path.join(pf, "etc", "console-setup"), keep_path=False)
        copy(self, "remap.inc",
             src=os.path.join(self.source_folder, "Keyboard"),
             dst=os.path.join(pf, "etc", "console-setup"), keep_path=False)

        # 默认配置（setupcon MAIN_CONFIG/MAIN_CONFIG2 的 installdir 回退路径）
        copy(self, "keyboard", src=os.path.join(self.source_folder, "config"),
             dst=os.path.join(pf, "etc", "default"), keep_path=False)
        copy(self, "console-setup",
             src=os.path.join(self.source_folder, "config"),
             dst=os.path.join(pf, "etc", "default"), keep_path=False)

        # man 页（上游 tarball 已含预渲染 .1/.5，无需 groff）
        for sub in ("man1", "man5"):
            os.makedirs(os.path.join(pf, "man", sub), exist_ok=True)
        copy(self, "setupcon.1 ckbcomp.1",
             src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(pf, "man", "man1"), keep_path=False)
        copy(self, "keyboard.5 console-setup.5",
             src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(pf, "man", "man5"), keep_path=False)

        copy(self, "GPL-2", src=self.source_folder,
             dst=os.path.join(pf, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share", "etc"]
