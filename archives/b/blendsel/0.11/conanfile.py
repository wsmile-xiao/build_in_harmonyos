#!/usr/bin/env python3
"""Conan recipe for blendsel 0.11 — Debian blends installer selector.

blendsel（Debian Pure Blends 安装选择器，tasksel 3.74 的 fork）是纯 Perl
CLI 工具 + po 翻译 + tasks 数据 + debconf 集成脚本的 Debian native 源包：
无 C/C++ 编译，上游 Makefile 只做脚本/数据安装与 pod2man/man 生成。

OHOS 适配要点（蓝本：abcselect/1.5 纯 Perl 脚本包先例）：
- 运行时依赖 conan perl/5.42.2（ohpcd 制品仓有 OHOS arm64 预编译二进制），
  构建期亦以 perl 运行 makedesc.pl 生成 desc 数据。
- 补丁 0001（conandata.yml 声明）三处最小改动：
  1) shebang /usr/bin/perl -> /usr/bin/env perl（OHOS 无 /usr/bin/perl）；
  2) Locale::gettext（Debian 生态 XS 模块 liblocale-gettext-perl，OHOS 无）
     改为可选加载，缺失时回退英文原文（与 C locale 行为等价）；
  3) /usr 硬编码数据路径改为随 $0 前缀推导（Debian /usr 布局不变，
     Conan 自定义 prefix 下 relocation-free）。
- debian-tasks.desc（任务描述数据）构建期由 makedesc.pl 从 tasks/ 生成：
  纯 perl；package lint 依赖 apt-cache dumpavail，无 apt 时自动降级跳过
  （与上游行为一致，doincludes.pl 的 #include 展开本包 tasks 数据未使用）。
- man 页由 perl 制品自带 pod2man 生成并 gzip（制品缺 pod2man 时跳过，
  以 info 记录，不影响功能）。
- 打包布局忠实对齐 Debian 包：bin/blendsel、lib/blendsel/{blendsel-debconf,
  tests/debconf, tests/new-install, packages/list}、share/blendsel/descs、
  share/man/man8。

验证边界：install/remove 执行链与 debconf UI 交互依赖 Debian 的
apt-get/dpkg/debconf 生态（OHOS 无），如实记录 runnable=0；
--task-packages/--task-desc/usage 等纯数据读取链在 OHOS 可完整运行
（test_package 执行，见 test_blendsel.py）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class BlendselConan(ConanFile):
    name = "blendsel"
    version = "0.11"
    description = "Tool for selecting blends for installation on Debian systems"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/installer-team/blendsel"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 纯 Perl 脚本工具，perl 为唯一运行/构建解释器（ohpcd 预编译制品）
        self.requires("perl/5.42.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # 注意：必须用 perl 依赖 package_folder 的绝对路径调用，并保留
        # env="conanbuild" 注入的 PERL5LIB——conanbuild PATH 中系统 perl
        # （/data/service/hnp/bin/perl 5.42.0）可能优先，若以 PATH 解析
        # 解释器会造成 5.42.0 解释器 + 5.42.2 XS 模块错配（symbol not
        # found）。perl 制品按 prefix=/ 编译，@INC 为 //lib/perl5，核心
        # 模块路径同样依赖 PERL5LIB 补足。
        perl_dep = self.dependencies["perl"]
        perl_bin = os.path.join(perl_dep.package_folder, "bin", "perl")
        pod2man = os.path.join(perl_dep.package_folder, "bin", "pod2man")
        # 生成 debian-tasks.desc：上游 make all 的核心产物（makedesc.pl 纯
        # perl 实现；apt-cache 缺失时其 lint 自动降级，与上游同构行为）。
        desc_dst = os.path.join(self.build_folder, "debian-tasks.desc")
        self.run(f'"{perl_bin}" "{os.path.join(src, "makedesc.pl")}" '
                 f'"{os.path.join(src, "tasks")}" "{desc_dst}"',
                 env="conanbuild")
        if not os.path.isfile(desc_dst):
            raise ConanInvalidConfiguration(
                "makedesc.pl produced no debian-tasks.desc")
        self.output.info("debian-tasks.desc generated: %d bytes"
                         % os.path.getsize(desc_dst))
        # man 页：pod2man（perl core 工具，随制品提供）。注意该制品以空前缀
        # 安装，pod2man 脚本 shebang 为 #!//bin/perl（悬空），须以 perl 解释器
        # 显式执行；PERL5LIB 已由 conanbuild env 注入（Pod::Man 模块）。
        man_gz = os.path.join(self.build_folder, "blendsel.8.gz")
        if os.path.isfile(pod2man):
            raw_man = os.path.join(self.build_folder, "blendsel.8.raw")
            self.run(f'"{perl_bin}" "{pod2man}" --section=8 --center '
                     f'"Debian specific manpage" --release {self.version} '
                     f'"{os.path.join(src, "blendsel.pod")}" > "{raw_man}" '
                     f'&& gzip -9c "{raw_man}" > "{man_gz}"',
                     env="conanbuild", ignore_errors=True)
        if os.path.isfile(man_gz) and os.path.getsize(man_gz) > 100:
            self.output.info("blendsel.8.gz generated: %d bytes"
                             % os.path.getsize(man_gz))
        else:
            if os.path.isfile(man_gz):
                os.unlink(man_gz)
            self.output.warning("pod2man unavailable/failed, man page skipped")

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        # bin/blendsel（补丁后主脚本）
        bin_dir = os.path.join(pkg, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(os.path.join(src, "blendsel.pl"),
                     os.path.join(bin_dir, "blendsel"))
        os.chmod(os.path.join(bin_dir, "blendsel"), 0o755)
        # lib/blendsel: debconf helper + tests hooks + packages data
        lib_dir = os.path.join(pkg, "lib", "blendsel")
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(os.path.join(lib_dir, "tests"), exist_ok=True)
        os.makedirs(os.path.join(lib_dir, "packages"), exist_ok=True)
        for rel in ["blendsel-debconf"]:
            shutil.copy2(os.path.join(src, rel), os.path.join(lib_dir, rel))
            os.chmod(os.path.join(lib_dir, rel), 0o755)
        for rel in ["debconf", "new-install"]:
            shutil.copy2(os.path.join(src, "tests", rel),
                         os.path.join(lib_dir, "tests", rel))
            os.chmod(os.path.join(lib_dir, "tests", rel), 0o755)
        shutil.copy2(os.path.join(src, "packages", "list"),
                     os.path.join(lib_dir, "packages", "list"))
        os.chmod(os.path.join(lib_dir, "packages", "list"), 0o755)
        # share/blendsel/descs + man
        share_dir = os.path.join(pkg, "share", "blendsel", "descs")
        os.makedirs(share_dir, exist_ok=True)
        desc_src = os.path.join(self.build_folder, "debian-tasks.desc")
        if os.path.isfile(desc_src):
            shutil.copy2(desc_src, os.path.join(
                share_dir, "debian-tasks.desc"))
        man_gz = os.path.join(self.build_folder, "blendsel.8.gz")
        if os.path.isfile(man_gz):
            man_dir = os.path.join(pkg, "share", "man", "man8")
            os.makedirs(man_dir, exist_ok=True)
            shutil.copy2(man_gz, os.path.join(man_dir, "blendsel.8.gz"))
        # license
        copy(self, "debian/copyright", src=src,
             dst=os.path.join(pkg, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
