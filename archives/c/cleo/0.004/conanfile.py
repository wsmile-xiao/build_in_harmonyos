#!/usr/bin/env python3
"""Conan recipe for cleo (App::Cleo) 0.004 — Perl CLI diff viewer.

cleo 是 Perl CLI 库（App::Cleo），走 ExtUtils::MakeMaker 构建系统
（Makefile.PL → make → make install），非 C/C++ CMake/Meson。
依赖 5 个 Perl 模块（Term::ReadKey/Term::ANSIColor/File::Slurp/Time::HiRes/
ExtUtils::MakeMaker），通过系统 perl 预装提供（CI 预装 perl + 模块）。
"""
import os

from conan import ConanFile
from conan.tools.files import copy
from conan.tools.layout import basic_layout


class CleoConan(ConanFile):
    name = "cleo"
    version = "0.004"
    # aireview P3: cleo 是 CLI 工具（产出 bin/cleo），非链接型 lib
    # 缺 package_type 致 Conan 2.x 默认按 library 处理，部署器/生成器路径布局错
    package_type = "application"
    settings = "os", "build_type", "arch"
    # Perl 模块无 compiler 设置（不编译 C/C++）

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # CI 真根因: ERROR: Package 'perl-Term-ReadKey/2.38' not resolved: error:invalid name
        # 5 个 perl 模块全不在 registry（perl-Term-ReadKey/perl-Term-ANSIColor/perl-File-Slurp/perl-Time-HiRes/perl-ExtUtils-MakeMaker）
        # 删依赖声明改用系统 perl（CI 预装 perl + 模块）+ build() 段删 self.dependencies 查改系统 PERL5LIB
        pass  # 无 Conan 依赖（perl 模块走系统 perl）

    def source(self):
        # CI 真根因: Conan get() 默认按 zip 解包，codeload tar.gz 返真 tar 格式 → BadZipFile 炸
        # Conan 2.x get() 不接 format/extension 参数 → 显式 get() download only + tarfile 手动解包
        import tarfile as _tar
        sources = dict(self.conan_data["sources"][self.version])
        # get() 下载到 self.source_folder 但不自动解包（避 zip 解包炸）
        # Conan get() 无 download_only 参数 → 用 curl 下载 + tarfile 手动解包
        self.run(
            f'curl -fsSL --connect-timeout 60 -o "{self.source_folder}/cleo.tar.gz" "{sources["url"]}"',
            cwd=self.source_folder, shell=True
        )
        with _tar.open(os.path.join(self.source_folder, "cleo.tar.gz"), "r:gz") as tf:
            tf.extractall(self.source_folder)
        os.remove(os.path.join(self.source_folder, "cleo.tar.gz"))
        # aireview P0: 删 apply_conandata_patches(self) 调用 — cleo 无补丁，误调致 NameError
        # conandata.yml 无 patches 字段、manifest patches_applied: []，无补丁应用步骤

    def export_sources(self):
        # Conan 2.x G1 门禁要求 export_sources() 声明；cleo 无补丁
        # aireview P3: 误调 apply_conandata_patches（该函数属 build() 非 export_sources）
        pass

    def generate(self):
        # Perl 构建无 toolchain 需生成
        pass

    def _src_dir(self):
        # tarfile 解包保留了顶层目录名 App-Cleo-3e22...（无 strip_root）
        # Conan 2.x basic_layout build_folder 在 build() 阶段指向 b/build-release，
        # 源码在 b/App-Cleo-*（build_folder 的上级目录的 App-Cleo-* 子目录）
        import glob as _g
        bf = getattr(self, "build_folder", "")
        for base in (os.path.join(bf, ".."), os.path.join(bf, "..", ".."), bf):
            subs = _g.glob(os.path.join(base, "App-Cleo-*"))
            if subs:
                return os.path.normpath(subs[0])
        return self.source_folder

    def build(self):
        # Perl 构建系统：Makefile.PL → make
        # CI 真根因: 删 perl 依赖后 build() 段 self.dependencies[dep] 查会 KeyError
        # 改用系统 perl 模块路径（CI 预装 perl + 模块在 /usr/share/perl5 或 vendor 路径）
        # PERL5LIB 注入系统 perl 模块路径（不依赖 Conan perl 包）
        perl5lib = os.environ.get("PERL5LIB", "")
        # aireview P1: env=["PERL5LIB=..."] 列表形式激活 Conan VirtualBuildEnv
        # Conan 2.x run() 要 env 是 list 非 dict（dict 致 AssertionError）
        env = [f"PERL5LIB={perl5lib}"] if perl5lib else None
        src_dir = self._src_dir()
        # 1. perl Makefile.PL PREFIX=$package_folder
        self.run(f'perl Makefile.PL INSTALL_BASE={os.path.join(self.build_folder, "staging")}',
                 cwd=src_dir, env=env)
        # 2. make
        self.run("make", cwd=src_dir, env=env)

    def package(self):
        # make install 安装到 staging
        # aireview P1: env list 格式（Conan 2.x run() 要 list 非 dict）
        src_dir = self._src_dir()
        self.run("make install", cwd=src_dir, env=None)
        # copy staging 到 package_folder
        copy(self, "*", src=os.path.join(self.build_folder, "staging"),
             dst=self.package_folder)

    def package_info(self):
        # cleo 是 Perl CLI 脚本（bin/cleo），非链接型 lib
        self.cpp_info.libs = []
        # CI 真根因: 删 perl 依赖后 self.dependencies[dep] 查会 KeyError
        # 消费者/测试用系统 perl 模块（CI 预装），不再通过 Conan perl 包注入 PERL5LIB
        # aireview P1: 补 cleo 自身模块路径（lib/perl5/.../App/Cleo.pm）
        # 消费者 perl -c bin/cleo 需通过 PERL5LIB 找到 App::Cleo 模块，缺自身路径致 "Can't locate App/Cleo.pm in @INC"
        self.runenv_info.append_path("PERL5LIB", os.path.join(self.package_folder, "lib", "perl5"))
