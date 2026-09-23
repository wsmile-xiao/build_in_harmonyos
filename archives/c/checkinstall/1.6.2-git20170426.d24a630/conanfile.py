#!/usr/bin/env python3
"""Conan recipe for checkinstall 1.6.2-git20170426.d24a630 — make-install packager tool.

checkinstall turns `make install` into a native package (deb/rpm/slackware).
The distribution is a set of bash scripts (checkinstall, makepak) plus the
installwatch LD_PRELOAD interposer (C, lib/installwatch.so) that tracks the
files written by `make install`.

OHOS / musl adaptation highlights:
- installwatch.c: glibc versioned stat ABI (__xstat/_STAT_VER/...) does not
  exist in musl; apps call stat/lstat/mknod/fstatat directly. The patch
  (0005) adds musl standard-symbol interposers and disables glibc-only
  64-bit wrappers (musl collapses stat64/open64/... onto 32-bit names).
- Scripts use `#!/usr/bin/env bash` (no /bin/bash on OHOS).
- Installed scripts embed PREFIX; we rewrite to a runtime-relative lookup
  (like abi-compliance-checker) so the package works at any install path.
- create-localdecls gains a musl fast path (no gcc/glibc headers needed);
  installwatch/Makefile uses $(CC) instead of hardcoded gcc.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, load, save, mkdir
from conan.tools.layout import basic_layout

# 编译期占位 PREFIX：make 生成脚本时嵌入，package() 阶段统一替换为运行时相对定位
_PLACEHOLDER_PREFIX = "/opt/checkinstall"


class CheckinstallConan(ConanFile):
    name = "checkinstall"
    version = "1.6.2-git20170426.d24a630"
    description = "Install a program with `make install` and generate a native Linux package"
    license = "GPL-2.0-or-later"
    homepage = "https://checkinstall.izto.org/"
    url = "https://github.com/giuliomoro/checkinstall"
    package_type = "application"

    # OHOS profile 需要全部四项 settings（L0p 门禁）
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        # R33: 编译器必须从 Conan conf 获取，不能依赖未定义 shell 变量
        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp.get("c") or "clang"

    def build(self):
        apply_conandata_patches(self)

        cc = self._get_cc()
        # `make`（默认 all 目标）生成:
        #   - checkinstall 主脚本 (sed: MAKEFILE_PREFIX -> PREFIX)
        #   - locale/*.mo (msgfmt)
        #   - installwatch/installwatch.so (C 编译, CC-from-conf)
        # 不执行 make install（其用 `install -o root -g root`，OHOS 无 root）；
        # 实际安装由 package() 手工完成（参照 abuild 先例）。
        # PREFIX 用占位符：sed 仅负责把 MAKEFILE_PREFIX 文本替换掉，
        # 之后 package() 会替换为基于脚本位置的相对路径，避免嵌入
        # 不可迁移的绝对路径。
        # Makefile 在 source 目录：先 cd 再 make（参照 abuild 先例）。
        src = self.source_folder
        self.run(f"cd {src} && make -j1 PREFIX={_PLACEHOLDER_PREFIX} CC={cc}")

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        # sbin/: checkinstall 主脚本 (make 生成) + makepak 辅助脚本
        bindir = os.path.join(pkg, "sbin")
        mkdir(self, bindir)
        for f in ("checkinstall", "makepak"):
            fpath = os.path.join(src, f)
            if os.path.isfile(fpath):
                copy(self, f, src=src, dst=bindir, keep_path=False)
                os.chmod(os.path.join(bindir, f), 0o755)

        # bin/: installwatch 包装脚本（模板 #PREFIX# 由 installwatch/Makefile 的
        # install 目标 sed；此处手工做等价替换为占位符）
        wbindir = os.path.join(pkg, "bin")
        mkdir(self, wbindir)
        tmpl = load(self, os.path.join(src, "installwatch", "installwatch"))
        tmpl = tmpl.replace("#PREFIX#", _PLACEHOLDER_PREFIX)
        wrapper = os.path.join(wbindir, "installwatch")
        save(self, wrapper, tmpl)
        os.chmod(wrapper, 0o755)

        # lib/: installwatch.so
        libdir = os.path.join(pkg, "lib")
        mkdir(self, libdir)
        copy(self, "installwatch.so", src=os.path.join(src, "installwatch"),
             dst=libdir, keep_path=False)

        # lib/checkinstall/: 配置模板 + locale .mo
        cidir = os.path.join(libdir, "checkinstall")
        mkdir(self, cidir)
        copy(self, "checkinstallrc-dist", src=src, dst=cidir, keep_path=False)
        locale_src = os.path.join(src, "locale")
        if os.path.isdir(locale_src):
            lang_dirs = os.path.join(cidir, "locale")
            for mo_name in sorted(os.listdir(locale_src)):
                if not (mo_name.endswith(".mo") and mo_name.startswith("checkinstall-")):
                    continue
                lang = mo_name[len("checkinstall-"):-len(".mo")]
                if not lang or lang == "template":
                    continue
                lc = os.path.join(lang_dirs, lang, "LC_MESSAGES")
                mkdir(self, lc)
                dst_path = os.path.join(lc, mo_name)
                copy(self, mo_name, src=locale_src, dst=lc, keep_path=False)
                os.rename(dst_path, os.path.join(lc, "checkinstall.mo"))

        # licenses/
        copy(self, "COPYING", src=src, dst=os.path.join(pkg, "licenses"), keep_path=False)
        copy(self, "installwatch/COPYING", src=src,
             dst=os.path.join(pkg, "licenses"), keep_path=False)

        # 脚本内嵌 PREFIX → 运行时相对定位（包任意路径可迁移）
        self._relocate_scripts()

    def _relocate_scripts(self):
        """把脚本里的占位 PREFIX 改写为基于 $0 的运行时相对定位。"""
        pkg = self.package_folder

        # 1) sbin/checkinstall: INSTALLDIR=<占位> → 依脚本位置推导包根
        ci = os.path.join(pkg, "sbin", "checkinstall")
        if os.path.isfile(ci):
            content = load(self, ci)
            if f"INSTALLDIR={_PLACEHOLDER_PREFIX}" in content:
                content = content.replace(
                    f"INSTALLDIR={_PLACEHOLDER_PREFIX}",
                    'INSTALLDIR="$(cd "$(dirname "$0")/.." && pwd)"'
                )
                save(self, ci, content)
                os.chmod(ci, 0o755)

        # 2) bin/installwatch: PREFIX=${PREFIX:-<占位>} → 运行时推导
        iw = os.path.join(pkg, "bin", "installwatch")
        if os.path.isfile(iw):
            content = load(self, iw)
            if f"PREFIX=${{PREFIX:-{_PLACEHOLDER_PREFIX}}}" in content:
                content = content.replace(
                    f"PREFIX=${{PREFIX:-{_PLACEHOLDER_PREFIX}}}",
                    'PREFIX=${PREFIX:-$(cd "$(dirname "$0")/.." && pwd)}'
                )
                save(self, iw, content)
                os.chmod(iw, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib"]
