#!/usr/bin/env python3
"""Conan recipe for file-sharedir 1.118 — File::ShareDir (CPAN, 纯 Perl).

File::ShareDir 提供「按发行版/按模块定位共享数据文件」的能力：库作者把数据
文件装在 `auto/share/dist/<Dist>/` 或 `auto/share/module/<Module>/` 下，运行时
用 `dist_dir` / `dist_file` / `module_dir` / `module_file` 定位。纯 Perl
（lib/File/ShareDir.pm 单模块），无 XS、无 C/C++ 产物。

构建系统：上游**自带 Makefile.PL**（ExtUtils::MakeMaker），并在 `inc/` 中捆绑
了 `File::ShareDir::Install` 与 `inc::latest` 以自举 `install_share`。故
build() 无需生成替代构建脚本，直接 `perl Makefile.PL` → `make` → `make test`
→ `make install DESTDIR=<staging>`（先例：file-sharedir-install 0.14）。

依赖（META.json prereqs，逐项对齐）:
  runtime   requires  Class::Inspector >= 1.12   → ohpcd 已发布 1.36
  runtime   requires  Carp / File::Spec / warnings → perl 核心，hnp perl 自带
  configure requires  File::ShareDir::Install >= 0.13 → ohpcd 已发布 0.14
  build     requires  File::ShareDir::Install 0.13    → 同上
  test      requires  File::Path >= 2.08 / Test::More >= 0.90 → hnp perl 自带

⚠️ 依赖注入（关键，实测）: 上游 t/00_prereqs.t 会 `require` 自身 META.json 声明的
**全部 requires**（含 configure/build 段的 File::ShareDir::Install），因此跑
`make test` 时必须让这些模块在 `@INC` 中。而依赖包的 package_info() 只声明了
runenv_info（无 buildenv_info），其 PERL5LIB 不会进入本包的 build 上下文 ——
故 build() 内遍历依赖定位各自的 perl lib 根并显式注入 PERL5LIB
（见 DRAFT-perl-buildenv-info-missing-dependency-injection）。
实测：不注入 → t/00_prereqs.t 的 `require File::ShareDir::Install` 失败
（1/91）；注入后全绿。

package_type="python-require"：纯 Perl 模块无二进制产物（沿用
file-sharedir-install / metrics-any / perl-uri 先例）；不产生 bindirs →
无需 commands.json（R38）。

R51：上游 t/ 测试套件（7 个 .t 文件）在 build() 内真实运行（make test）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout

# 本包模块在 perl lib 树中的相对路径（用于定位 site 根）
MODULE_REL = os.path.join("File", "ShareDir.pm")

# 需要在 build 上下文可见的依赖模块（各自的 site 根将被注入 PERL5LIB）
DEP_MODULES = {
    "class-inspector": os.path.join("Class", "Inspector.pm"),
    "file-sharedir-install": os.path.join("File", "ShareDir", "Install.pm"),
}


class FileSharedirConan(ConanFile):
    name = "file-sharedir"
    version = "1.118"
    description = ("File::ShareDir — locate per-dist and per-module shared "
                   "files (pure Perl)")
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/pod/File::ShareDir"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯 Perl 模块：无 C/C++ 二进制产物，沿用 file-sharedir-install / perl-uri 先例
    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 运行时依赖：File::ShareDir 用 Class::Inspector 解析模块的安装位置
        # （META.json runtime requires Class::Inspector >= 1.12）。ohpcd 已发布 1.36。
        self.requires("class-inspector/1.36")
        # configure/build 依赖：上游 Makefile.PL 的 install_share 由
        # File::ShareDir::Install 提供（>= 0.13）；且 t/00_prereqs.t 会 require 它。
        # ohpcd 已发布 0.14（main 上亦有）。
        self.requires("file-sharedir-install/0.14")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)  # 无补丁时空操作

    def _perl(self):
        """定位 perl 解释器：优先 OHOS 预装 hnp perl，回退 PATH。

        与 file-sharedir-install / metrics-any 先例一致（hnp perl 5.42.0 的
        Errno 导出完整，设备 perl 5.42.2 缺别名常量，统一用 hnp perl 规避同类假失败）。
        """
        hnp = "/data/service/hnp/bin/perl"
        if os.path.isfile(hnp):
            return hnp
        found = shutil.which("perl")
        if not found:
            raise ConanException("perl interpreter not found")
        return found

    def _find_site(self, base, rel):
        """在 base 下查找包含相对模块路径 rel 的目录（即 perl lib 根）。

        安装前缀随 perl 构建而异，不可硬编码；返回的是**包含该模块路径的根**。
        """
        for root, _dirs, _files in os.walk(base):
            if os.path.isfile(os.path.join(root, rel)):
                return root
        return None

    def _dep_perl5lib(self):
        """收集依赖的 perl lib 根（build() 内跑测试/配置时需注入 PERL5LIB）。

        Perl 依赖包的 package_info() 通常只声明 runenv_info（无 buildenv_info），
        故其 PERL5LIB 不会自动进入 build 上下文 —— 必须在此显式定位。
        """
        sites = []
        for dep_name, rel in DEP_MODULES.items():
            dep = self.dependencies.get(dep_name)
            if dep is None or not dep.package_folder:
                raise ConanException(
                    f"dependency '{dep_name}' is required to build this package "
                    "but has no package folder")
            site = self._find_site(dep.package_folder, rel)
            if not site:
                raise ConanException(
                    f"{rel} not found in dependency '{dep_name}': "
                    f"{dep.package_folder}")
            sites.append(site)
        return sites

    def build(self):
        # 上游自带 Makefile.PL（ExtUtils::MakeMaker + inc/ 自举 install_share）；
        # 若某版本缺失则显式报错而非静默降级。
        if not os.path.isfile(os.path.join(self.source_folder, "Makefile.PL")):
            raise ConanException(
                "upstream Makefile.PL not found — this recipe expects the "
                "upstream MakeMaker build script (no substitution is applied)")

        perl = self._perl()
        # 依赖模块需在 @INC 中：上游 Makefile.PL 的 install_share 需要
        # File::ShareDir::Install，且 t/00_prereqs.t 会 require 全部 requires。
        dep_sites = self._dep_perl5lib()
        env_prefix = 'export PERL5LIB="' + os.pathsep.join(dep_sites) + ':$PERL5LIB" && '
        self.output.info(f"injected PERL5LIB: {dep_sites}")

        self.run(env_prefix + f"{perl} Makefile.PL INSTALLDIRS=site",
                 cwd=self.source_folder)
        self.run(env_prefix + "make", cwd=self.source_folder)
        # R51：上游 t/ 套件真实运行（7 文件；含 prereqs/compile/main/
        # extensions/fail/class/old）
        self.run(env_prefix + "make test", cwd=self.source_folder)

        staging = os.path.join(self.build_folder, "perl-stage")
        self.run(f'make install DESTDIR="{staging}"', cwd=self.source_folder)

    def package(self):
        staging = os.path.join(self.build_folder, "perl-stage")
        if not os.path.isdir(staging):
            raise ConanException(f"perl staging missing: {staging}")
        for root, _dirs, files in os.walk(staging):
            for f in files:
                src = os.path.join(root, f)
                rel = os.path.relpath(src, staging)
                dst = os.path.join(self.package_folder, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
        site = self._find_site(self.package_folder, MODULE_REL)
        if not site:
            raise ConanException("File/ShareDir.pm not found in package")
        # 本包的核心产物之一是数据文件（auto/share/{dist,module}/...），
        # 缺失则 dist_dir/module_dir 在消费方会失败 → 显式校验。
        if not os.path.isdir(os.path.join(site, "auto", "share")):
            raise ConanException(
                f"auto/share data files missing under {site} — File::ShareDir "
                "cannot locate dist/module data without them")

    def package_info(self):
        # 纯 Perl 模块：无 C/C++ 库可链接（R26 静态链接不适用）
        self.cpp_info.libs = []
        site = self._find_site(self.package_folder, MODULE_REL)
        if site:
            self.output.info(f"PERL5LIB={site}")
            # 用 prepend_path 而非 define_path：本包与依赖都声明 PERL5LIB，
            # prepend 保证两者都被消费方拿到而不相互覆盖。
            self.runenv_info.prepend_path("PERL5LIB", site)
