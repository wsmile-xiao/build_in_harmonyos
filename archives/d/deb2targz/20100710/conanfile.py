#!/usr/bin/env python3
"""Conan recipe — deb2targz 20100710（单文件 Perl 脚本，无构建步骤）。

上游形态特殊：**不是归档，而是作者站点上的单个 Perl 脚本**
（https://www.miketaylor.org.uk/tech/deb/deb2targz，1947 字节）。
上游自身**不带版本号**；Gentoo（app-arch/deb2targz-1-r3）与 FreeBSD
（archivers/deb2targz）均以日期 `20100710` 作为发行版本号，本配方沿用。

OHOS 适配要点：
1. 裸文件下载须用 `download()` 而非 `get()`（`get()` 会尝试解压）。
2. **shebang 两处问题**（本仓库既有草稿 DRAFT-ohos-perl-script-package-conan-adaptation
   已覆盖该模式）：
   - 上游为 `#!/usr/bin/perl -w`，而 **OHOS 无 `/usr/bin/perl`**（perl 由 ohpcd 的
     perl 包提供，位于包内 `bin/`）→ 改为 `#!/usr/bin/env perl` 由 PATH 解析；
   - **必须同时去掉 `-w`** —— `#!/usr/bin/env perl -w` 是错误写法：内核只把 shebang
     首个空白之后的全部内容作为**一个参数**传给解释器，`env` 会把 `"perl -w"` 当作
     **单个程序名**去查找而失败（实测 `env: exec perl -w: No such file or directory`）。
     脚本内已有 `use strict;`，功能无损失。
3. 运行期依赖 `perl/5.42.2`（ohpcd 已发布）；脚本仅用核心模块 `strict` + `IO::File`。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, chmod, download, replace_in_file, mkdir
from conan.tools.layout import basic_layout

SRC_NAME = "deb2targz"


class Deb2TargzConan(ConanFile):
    name = "deb2targz"
    version = "20100710"
    description = ("deb2targz — convert a Debian .deb package into a .tar.gz "
                   "(single-file Perl script)")
    license = "GPL-2.0-or-later"
    homepage = "https://www.miketaylor.org.uk/tech/deb/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def source(self):
        # 上游是裸文件（非归档）→ 用 download()，不能用 get()（后者会尝试解压）
        info = self.conan_data["sources"][SRC_NAME]
        download(self, info["url"], filename=SRC_NAME, sha256=info["sha256"])
        path = os.path.join(self.source_folder, SRC_NAME)
        if not os.path.isfile(path):
            raise ConanException(f"deb2targz: 上游文件未取到: {path}")

        # shebang ①：改用 env perl（OHOS 无 /usr/bin/perl）
        # shebang ②：**同时去掉 -w** —— `env perl -w` 会让 env 把 "perl -w" 当单个
        #            程序名查找而失败；脚本内已有 use strict，无功能损失
        src = open(path, encoding="utf-8", errors="replace").read()
        if not src.startswith("#!"):
            raise ConanException("deb2targz: 文件未以 shebang 开头，补丁假设失效")
        first, _, rest = src.partition("\n")
        if "perl" not in first:
            raise ConanException(f"deb2targz: shebang 非 perl，无法按预期改写: {first!r}")
        open(path, "w", encoding="utf-8", newline="\n").write(
            "#!/usr/bin/env perl\n" + rest)

        # 自校：确认改写真的生效（避免补丁静默失效后装出不可执行的脚本）
        head = open(path, encoding="utf-8", errors="replace").readline().strip()
        if head != "#!/usr/bin/env perl":
            raise ConanException(f"deb2targz: shebang 改写未生效: {head!r}")
        if "-w" in head:
            raise ConanException("deb2targz: shebang 仍含 -w（env 会解析失败）")

    def requirements(self):
        # 运行期依赖：shebang 为 `/usr/bin/env perl`，消费者需能解析到 perl
        self.requires("perl/5.42.2", transitive_headers=False, transitive_libs=False)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mkdir(self, bindir)
        copy(self, SRC_NAME, src=self.source_folder, dst=bindir)
        chmod(self, os.path.join(bindir, SRC_NAME), execute=True)
        # README 类无（上游仅单文件）；许可证按上游站点声明为 GPL
        copy(self, "COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
