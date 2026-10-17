#!/usr/bin/env python3
"""Conan recipe for file-sharedir-install 0.14 — File::ShareDir::Install (纯 Perl).

File::ShareDir::Install 让 `Makefile.PL` 能声明并安装「共享数据文件」
（dist 级 `share/` 与模块级 share），由 `install_share` / `delete_share`
登记、`postamble` 注入 Makefile 规则，安装到 `auto/share/{dist,module}/...`。
纯 Perl（lib/File/ShareDir/Install.pm 单模块），无 XS、无 C/C++ 产物。

构建系统：上游**自带 Makefile.PL**（由 Dist::Zilla::Plugin::MakeMaker 生成，
直接 use ExtUtils::MakeMaker）——与 future / metrics-any / test-refcount 不同，
**无需生成替代构建脚本**，也不需要 Module::Build。故 build() 直接
`perl Makefile.PL INSTALLDIRS=site` → `make` → `make test` → `make install`。

⚠️ 上游测试有一个必须注意的陷阱：t/10_makefile.t、t/11_dotfile.t、
t/12_delete.t 都以 `plan skip_all if not -f 'Makefile'` 开头，且内部会
**递归调用 `make`** 校验安装结果。因此：
  - 必须走 `make test`（Makefile 已生成 → 4 文件 39 用例真跑），
    **不能**用 `prove -Ilib t/` 替代（Makefile 不存在 → 三个文件静默 skip，
    只剩 1 个用例，"全绿"是假象）。本配方把 `make test` 放进 build()。
  - 这三个文件会真实执行 make/install 到临时目录（tlib-$$/troot-$$），
    需要可写的构建目录（conan 的 build_folder 满足）。

package_type="python-require"：纯 Perl 模块无二进制产物，沿用
perl-uri / metrics-any / test-refcount 先例；不产生 bindirs → 无需
commands.json（R38）。

R51：上游 t/ 测试套件（4 个 .t 文件）在 build() 内真实运行（make test），
实测 Files=4, Tests=39, Result: PASS。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class FileSharedirInstallConan(ConanFile):
    name = "file-sharedir-install"
    version = "0.14"
    description = ("File::ShareDir::Install — declare and install shared data "
                   "files from a Makefile.PL (pure Perl)")
    # 上游 META.json 的 license 为 perl_5（同 Perl 自身条款）
    license = "perl_5"
    homepage = "https://metacpan.org/pod/File::ShareDir::Install"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯 Perl 模块：无 C/C++ 二进制产物，沿用 perl-uri/metrics-any 先例
    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)  # 无补丁时空操作

    def _perl(self):
        """定位 perl 解释器：优先 OHOS 预装 hnp perl，回退 PATH。

        与 metrics-any / test-refcount 口径一致（hnp perl 5.42.0 的 Errno
        导出完整，设备 perl 5.42.2 缺别名常量，统一用 hnp perl 规避同类假失败）。
        """
        hnp = "/data/service/hnp/bin/perl"
        if os.path.isfile(hnp):
            return hnp
        found = shutil.which("perl")
        if not found:
            raise ConanException("perl interpreter not found")
        return found

    def build(self):
        # 上游自带 Makefile.PL（ExtUtils::MakeMaker），无需生成替代脚本；
        # 若上游某版本缺少则报错而非静默降级。
        if not os.path.isfile(os.path.join(self.source_folder, "Makefile.PL")):
            raise ConanException(
                "upstream Makefile.PL not found — this recipe expects the "
                "upstream MakeMaker build script (no substitution is applied)")

        perl = self._perl()
        self.run(f"{perl} Makefile.PL INSTALLDIRS=site", cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)
        # R51：上游 t/ 套件真实运行。必须用 make test —— t/10_makefile.t 等
        # 三个文件以「存在 Makefile」为前提，用裸 prove 会静默 skip 掉它们。
        self.run("make test", cwd=self.source_folder)
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
        if not self._site_dir():
            raise ConanException("File/ShareDir/Install.pm not found in package")

    # 模块安装后的相对路径（用于定位 site 根：去掉该后缀即得 site）
    MODULE_REL = os.path.join("File", "ShareDir", "Install.pm")

    def _site_dir(self):
        """返回包含 File/ShareDir/Install.pm 的 perl lib 根目录（site 目录）。

        安装前缀随 perl 构建而异，不可硬编码。模块位于
        <site>/File/ShareDir/Install.pm —— 需去掉 MODULE_REL 后缀（回溯多级），
        而不是返回末级目录（否则 PERL5LIB/-I 指向错误层级，消费者报
        missing packaged module）。
        """
        for root, _dirs, files in os.walk(self.package_folder):
            if "Install.pm" in files and root.endswith(
                    os.path.join("File", "ShareDir")):
                # root = <site>/File/ShareDir → 上溯到 site
                return os.path.dirname(os.path.dirname(root))
        return None

    def package_info(self):
        # 纯 Perl 模块：无 C/C++ 库可链接（R26 静态链接不适用）
        self.cpp_info.libs = []
        site = self._site_dir()
        if site:
            self.output.info(f"PERL5LIB={site}")
            # 消费者 perl 脚本可直接 use File::ShareDir::Install
            self.runenv_info.define_path("PERL5LIB", site)
