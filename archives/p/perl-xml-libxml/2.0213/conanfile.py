#!/usr/bin/env python3
"""Conan recipe for perl-xml-libxml 2.0213 — XML::LibXML module
(XS: libxml2 binding, CPAN source; libxml2 from ohpcd).

XS module: build via perl Makefile.PL → make → make install DESTDIR.
The Alien::Libxml2 probe is BYPASSED by patch 0001 (its system probe
cannot locate a custom libxml2 — OHOS) — libxml2 include/lib paths are
passed directly via LIBS/INC on the command line.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class PerlXmlLibxmlConan(ConanFile):
    name = "perl-xml-libxml"
    version = "2.0213"
    description = "XML::LibXML — Interface to libxml2"
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/pod/XML::LibXML"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # XS module — builds a C library (LibXML.so), so type is library
    # (python-require cannot depend on static-library libxml2)
    package_type = "library"
    exports_sources = "0001-*.patch"

    def requirements(self):
        self.requires("libxml2/2.15.3")
        # XML::LibXML.pm 编译期 use XML::SAX::Exception（_SAXParser 子包）——
        # perl 的 use 在编译期执行，无法绕过；按 W0/R36 先发布 SAX 依赖
        self.requires("perl-xml-sax/1.02", transitive_headers=True, transitive_libs=True)
        self.requires("perl-xml-namespacesupport/1.12",
                      transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _find_sax_site(self):
        # 在 perl-xml-sax 依赖包中定位 XML/SAX/Exception.pm 的 @INC 根
        for _ref, dep in self.dependencies.items():
            if dep.ref.name == "perl-xml-sax":
                for root, _dirs, files in os.walk(dep.package_folder):
                    if "Exception.pm" in files:
                        return os.path.dirname(os.path.dirname(os.path.dirname(root)))
        return ""

    def build(self):
        perl = "/data/service/hnp/bin/perl"
        lx = self.dependencies["libxml2"].package_folder
        inc = os.path.join(lx, "include", "libxml2")
        lib = os.path.join(lx, "lib")
        # SAX 依赖的 PERL5LIB（编译期 use XML::SAX::Exception 需要）
        sax_site = self._find_sax_site()
        env = f"PERL5LIB={sax_site} " if sax_site else ""
        # bypass Alien::Libxml2 — pass libxml2 paths directly
        self.run(
            f'{env}{perl} Makefile.PL LIBS="-L{lib} -lxml2" '
            f'INC="-I{inc}"', cwd=self.source_folder)
        # CI 上 lld 链接 LibXML.so 时启动即失败实测（#30218/#30224）：
        # OHOS SDK 的 lld 自身 DT_NEEDED=libxml2.so.16（RUNPATH=
        # $ORIGIN/../lib→SDK llvm/lib 自带 2.14.0）——CI 上无注入时
        # lld 找不到该库；注入 conan libxml2（2.15.3）后符号版本不匹配
        # （'Error relocating lld: xmlFreeDoc: symbol not found'）——
        # 正确做法：注入 lld 的 RUNPATH 目标（SDK llvm/lib，lld 编译
        # 环境的原生 libxml2.so.16 2.14.0——本地 readelf 验证该库有完整
        # 符号）。CI 上 readelf 动态解析不可靠（#30218 实测 _ld_env 为
        # 空导致裸 make 仍失败）——**直接硬编码 SDK llvm/lib 路径**注入
        # LD_LIBRARY_PATH（该路径为 lld 自身 RUNPATH=$ORIGIN/../lib
        # 的目标，lld 编译环境的原生 libxml2）
        _lld_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18" \
                   "/ohos/native/llvm/lib"
        self.run(f"LD_LIBRARY_PATH={_lld_lib} make",
                 cwd=self.source_folder)
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
                # XS .so needs read+exec — HMDFS umask may strip perms
                if f.endswith(".so"):
                    os.chmod(dst, 0o755)
        # locate LibXML.pm (site_perl or lib/perl5 — walk to avoid drift)
        found = None
        for root, _dirs, files in os.walk(self.package_folder):
            if "LibXML.pm" in files and os.path.basename(root) == "XML":
                found = root
                break
        if not found:
            raise ConanException("XML/LibXML.pm not found in package")

    def package_info(self):
        # expose the perl5 dir containing XML/LibXML.pm as PERL5LIB
        site = None
        for root, _dirs, files in os.walk(self.package_folder):
            if "LibXML.pm" in files and os.path.basename(root) == "XML":
                site = root
                break
        if site:
            self.output.info(f"PERL5LIB={site}")
