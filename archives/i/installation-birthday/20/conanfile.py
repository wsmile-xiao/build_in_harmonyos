#!/usr/bin/env python3
"""Conan recipe for installation-birthday 20 (pure script package).

installation-birthday: "Receive congratulations on system installation
anniversaries" — a single-file Python 3 CLI by Chris Lamb (Debian
Developer, lamby@debian.org). It detects the system installation date
(preferring the oldest mtime across ext 文件系统创建时间 via tune2fs 与
/var/log/installer、/etc/hostname 等候选文件) and prints an ASCII-art
birthday cake on the anniversary; Debian wires it into cron.daily to
"send a message to the local system administrator".

Upstream is a Debian *native* source package (no upstream/distinction —
salsa.debian.org/lamby/installation-birthday, tag 20, GPL-3+, released
2024-12-31; v20 adds /etc/hostname to the candidate-timestamp list).
Version 20 = Debian sid version, taken from the task card. The recipe
pins the official Debian pool source tarball (sha256 与 .dsc 记录的
Checksums-Sha256 一致); 备源为清华 TUNA Debian 镜像同文件。

纯脚本包：无编译、无链接（kicad-demos/inform6-library/ldraw-parts 纯
数据包范式）。载荷 = 脚本本体（bin/） + GPL-3 全文 COPYING（doc/）。
debian/ 打包目录（cron.daily 集成、autopkgtest、manpage 生成规则）属
Debian 发行集成，不进入 conan 包。

运行前提（消费者侧）：python3 ≥ 3.11（脚本使用 datetime.UTC）+ 可选
python3-distro（打印蛋糕时取发行版名）；tune2fs/e2fsprogs 缺失时脚本
自动降级到候选文件 mtime 路径。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get


class InstallationBirthdayConan(ConanFile):
    name = "installation-birthday"
    version = "20"
    description = ("Receive congratulations on system installation "
                   "anniversaries (single-file Python 3 CLI)")
    license = "GPL-3.0-or-later"
    author = "Chris Lamb <lamby@debian.org>"
    homepage = "https://chris-lamb.co.uk/projects/installation-birthday"
    url = ""  # CI fills this
    package_type = "unknown"

    # 纯脚本/资源包：无编译、无链接，但保留 settings 以满足 CI L0 门禁的
    # 显式 settings 声明要求（与 kicad-demos/fabric-completion 先例同款）。
    settings = "os", "compiler", "build_type", "arch"

    _script = "installation-birthday"
    _doc_dir = os.path.join("share", "doc", "installation-birthday")

    # 上游 tarball（Debian pool v20）静态清单：载荷 2 文件 + 全树 17 文件
    # （含 debian/ 打包目录、setup.py/pyproject.toml、.travis.yml）。
    _files = ("installation-birthday", "COPYING")
    _expected_total = 17

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # 配方自足：源码与数据全部经 conandata sources（get）下载，
        # 除 conanfile.py/conandata.yml 外无本地文件需要随配方导出。
        pass

    def build(self):
        apply_conandata_patches(self)  # patches=[] 时为空操作，预留补丁入口
        # 纯脚本包无编译步骤。构建期校验上游文件清单，防止下载内容或
        # 目录结构静默漂移（kicad-demos 先例范式）。
        missing = [f for f in self._files
                   if not os.path.isfile(os.path.join(self.source_folder, f))]
        if missing:
            raise ConanInvalidConfiguration(
                "installation-birthday 20 inventory drift: missing files "
                + ", ".join(missing)
            )
        # 真机 G2 首验实录：conan 2 在 build() 前向 source folder 注入
        # 聚合环境文件（conanbuild.sh/conanrun.sh/conanbuildenv-*.sh/
        # conanrunenv-*.sh/deactivate_conanbuild.sh/deactivate_conanrun.sh
        # 共 6 个）及簿记文件，计数时排除（fabric-completion 先例同款
        # .sh 排除口径 + 簿记排除）。
        total = sum(1 for _, _, files in os.walk(self.source_folder)
                    for f in files
                    if not f.endswith(".sh")
                    and f not in ("conaninfo.txt", "conanmanifest.txt"))
        if total != self._expected_total:
            raise ConanInvalidConfiguration(
                f"installation-birthday 20 total file count {total} "
                f"!= {self._expected_total}"
            )

    def package(self):
        # 载荷仅脚本 + COPYING，显式复制（fabric-completion 同款范式：
        # 文件少时逐文件复制比 copy("*")+excludes 更稳）。
        copy(self, self._script, src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        os.chmod(os.path.join(self.package_folder, "bin", self._script), 0o755)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, self._doc_dir),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = [self._doc_dir]
        self.cpp_info.libs = []
        # 无 runenv：CLI 工具，消费者直接调 bin/installation-birthday；
        # 上游无环境变量接口（仅 --verbosity/-p/--force 命令行参数）。

    def package_id(self):
        self.info.clear()
