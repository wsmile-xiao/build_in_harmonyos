#!/usr/bin/env python3
"""Conan recipe — cvsweb 3.0.6 (pure Perl CGI application).

FreeBSD cvsweb: WWW CGI script to browse CVS repository trees.
Pure Perl application (no C compilation). Bundles its two non-core
Perl module dependencies (IPC::Run, URI::Escape) since the OHOS
perl build is a slim build without them.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CvswebConan(ConanFile):
    name = "cvsweb"
    version = "3.0.6"
    description = "WWW CGI script to browse CVS repository trees"
    license = "BSD-2-Clause"
    homepage = "https://www.freebsd.org/projects/cvsweb.html"
    url = "https://www.freebsd.org/projects/cvsweb.html"
    package_type = "application"

    settings = "os", "arch"

    # 捆绑的纯 Perl 模块源（OHOS perl 精简构建缺这些模块）
    module_sources = {
        "ipc_run": {
            "url": "https://cpan.metacpan.org/authors/id/T/TO/TODDR/IPC-Run-20220807.0.tar.gz",
            "sha256": "277d781dbbc98af18e979c7ef36f222513d7361742c52507c3348b265f6f5e69",
        },
        "uri": {
            "url": "https://cpan.metacpan.org/authors/id/O/OA/OALDERS/URI-5.28.tar.gz",
            "sha256": "e7985da359b15efd00917fa720292b711c396f2f9f9a7349e4e7dec74aa79765",
        },
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Perl 5.42 兼容性修复（OHOS perl 5.42.2 对旧语法解析更严格）：
        #   1) `for my $v qw(...)` 无括号形式 → `for my $v (qw(...))`
        #   2) `defined @mytz`（Perl 5.22+ 已废弃 defined(@array)）→ `@mytz`
        import io
        _path = os.path.join(self.source_folder, "cvsweb.cgi")
        with io.open(_path, encoding="latin-1") as _f:
            _src = _f.read()
        _fixes = [
            ("for my $v qw(hidecvsroot hidenonreadable) {",
             "for my $v (qw(hidecvsroot hidenonreadable)) {"),
            ("if (defined @mytz) {", "if (@mytz) {"),
        ]
        for _old, _new in _fixes:
            _src = _src.replace(_old, _new)
        with io.open(_path, "w", encoding="latin-1") as _f:
            _f.write(_src)
        # 捆绑纯 Perl 依赖模块：下载并解压到 perl-lib/
        from conan.tools.files import download
        os.makedirs(os.path.join(self.source_folder, "perl-lib"), exist_ok=True)
        for _key, _m in self.module_sources.items():
            _arc = os.path.join(self.source_folder, "mod-%s.tar.gz" % _key)
            download(self, _m["url"], _arc, sha256=_m["sha256"])
            self.run('cd "%s" && cmake -E tar xf %s' % (self.source_folder, os.path.basename(_arc)))
            # 找解压出的 lib/ 目录合并进 perl-lib/
            _extracted = [d for d in os.listdir(self.source_folder)
                          if d.startswith("IPC-Run-") or d.startswith("URI-")]
            for _d in _extracted:
                _lib = os.path.join(self.source_folder, _d, "lib")
                if os.path.isdir(_lib):
                    self.run('cp -r "%s/." "%s"' % (_lib, os.path.join(self.source_folder, "perl-lib")))
            os.remove(_arc)

    def build(self):
        apply_conandata_patches(self)
        # 纯 Perl 脚本，无编译。做语法自检（perl -T -c，-T 匹配 shebang taint 模式）。
        # 注意：taint 模式下 PERL5LIB 环境变量会被 perl 忽略（安全特性），必须用 -I 参数。
        # OHOS perl 位于 /data/service/hnp/bin/perl（不在标准 PATH，atool 先例），CI 需绝对路径。
        perl = os.environ.get("PERL") or "/data/service/hnp/bin/perl"
        moddir = os.path.join(self.source_folder, "perl-lib")
        self.run('cd "%s" && %s -T -I "%s" -c cvsweb.cgi' % (self.source_folder, perl, moddir))

    def package(self):
        src = self.source_folder
        # 脚本与配置装到 libexec/cvsweb/，icons/css 随包
        self.run('mkdir -p "%s/libexec/cvsweb/icons" "%s/libexec/cvsweb/css" "%s/libexec/cvsweb/enscript"' % (
            self.package_folder, self.package_folder, self.package_folder))
        copy(self, "cvsweb.cgi", src=src, dst=os.path.join(self.package_folder, "libexec", "cvsweb"))
        copy(self, "cvsweb.conf", src=src, dst=os.path.join(self.package_folder, "libexec", "cvsweb"))
        for _conf in ("cvsweb.conf-freebsd", "cvsweb.conf-netbsd", "cvsweb.conf-openbsd", "cvsweb.conf-ruby"):
            copy(self, _conf, src=src, dst=os.path.join(self.package_folder, "libexec", "cvsweb"))
        copy(self, "icons/*", src=src, dst=os.path.join(self.package_folder, "libexec", "cvsweb", "icons"))
        copy(self, "css/*", src=src, dst=os.path.join(self.package_folder, "libexec", "cvsweb", "css"))
        copy(self, "enscript/*", src=src, dst=os.path.join(self.package_folder, "libexec", "cvsweb", "enscript"))
        copy(self, "README", src=src, dst=os.path.join(self.package_folder, "libexec", "cvsweb"))
        copy(self, "INSTALL", src=src, dst=os.path.join(self.package_folder, "libexec", "cvsweb"))
        # cvsweb-3.0.6 官方 tarball 无独立 LICENSE 文件（许可声明见 README 头部），
        # 上游无 license 文件时跳过拷贝，避免精确文件名 copy 的版本脆弱性。
        if os.path.exists(os.path.join(src, "LICENSE")):
            copy(self, "LICENSE", src=src, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # 捆绑的纯 Perl 模块：复制 perl-lib/ 的**内容**（避免嵌套 perl-lib/perl-lib/）
        _modsrc = os.path.join(src, "perl-lib")
        _moddst = os.path.join(self.package_folder, "libexec", "cvsweb", "perl-lib")
        if os.path.isdir(_modsrc):
            self.run('mkdir -p "%s" && cp -r "%s/." "%s"' % (_moddst, _modsrc, _moddst))

    def package_info(self):
        # 运行 cvsweb.cgi 需要 PERL5LIB 指向捆绑模块
        _moddir = os.path.join(self.package_folder, "libexec", "cvsweb", "perl-lib")
        self.runenv_info.define("PERL5LIB", _moddir)
        self.cpp_info.bindirs = ["libexec/cvsweb"]
