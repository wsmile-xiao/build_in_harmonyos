#!/usr/bin/env python3
"""Conan recipe for abuild-rootbld 3.18.0_rc3 — Alpine rootbld meta-package.

abuild-rootbld is a noarch subpackage of Alpine's abuild: it declares the
runtime dependency set for `abuild rootbld` (building .apk packages in a
bubblewrap-based chroot sandbox): abuild + bubblewrap + envsubst(gettext).

The rootbld command itself is a shell function inside abuild.in (provided by
the abuild package). This recipe therefore:
- depends on abuild/3.17.0.1, bubblewrap/0.11.0, gettext/0.22.5.1;
- installs a small bin/rootbld wrapper that delegates to `abuild rootbld`
  (rootbld is a subcommand of abuild) so the sandboxed build entrypoint is
  discoverable via PATH;
- has no C/C++ compilation (pure noarch meta-package, build system: custom).

Upstream tests: rootbld has no standalone test target; abuild's own ATF/Kyua
suite is exercised by the abuild package recipe (atf-shim.sh). test_package
here verifies the dependency contract: bwrap/envsubst/abuild present and the
rootbld wrapper runs.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class AbuildRootbldConan(ConanFile):
    name = "abuild-rootbld"
    version = "3.18.0_rc3"
    description = "Build packages in chroot (Alpine abuild rootbld meta-package)"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/alpine/abuild/"
    url = "https://gitlab.alpinelinux.org/alpine/abuild/"
    package_type = "application"

    # OHOS profile 需要全部四项 settings（L0p 门禁）
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # rootbld runtime contract: abuild (provides `abuild rootbld`) +
        # bubblewrap (chroot sandbox) + envsubst (gettext, template vars).
        # 引用格式与本地缓存/制品仓实际发布形式一致：
        # abuild/bubblewrap/gettext 均以无 channel 形式发布（制品仓一致）
        # abuild 引用制品仓最新修复版 3.17.0.1（上游无 3.18.x 正式发布，
        # abuild 主包在制品仓的最新可用版本为 3.17.0.1）
        self.requires("abuild/3.17.0.1")
        self.requires("bubblewrap/0.11.0")
        self.requires("gettext/0.22.5.1")

    def layout(self):
        pass

    def source(self):
        # Source tarball is abuild itself (rootbld lives in abuild.in); we
        # only extract it to document the rootbld implementation. The build
        # itself needs no compilation.
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Noarch meta-package: nothing to compile. The rootbld entry point is
        # provided by the abuild dependency (`abuild rootbld`); we install a
        # thin PATH wrapper below.
        apply_conandata_patches(self)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        wrapper = os.path.join(bindir, "rootbld")
        with open(wrapper, "w", encoding="utf-8") as handle:
            handle.write(
                '#!/bin/sh\n'
                '# rootbld — Alpine abuild-rootbld meta-package wrapper.\n'
                '# The rootbld implementation is provided by the abuild\n'
                '# package (`abuild rootbld`); this wrapper delegates so the\n'
                '# entry point is available on PATH.\n'
                'if [ "${1:-}" = "--version" ] || [ "${1:-}" = "-V" ]; then\n'
                '    echo "abuild-rootbld 3.18.0_rc3 (rootbld provided by abuild)"\n'
                '    exit 0\n'
                'fi\n'
                'exec abuild rootbld "$@"\n'
            )
        os.chmod(wrapper, 0o755)
        # Ship the abuild rootbld source excerpt for reference (optional doc).
        src_rootbld = os.path.join(self.source_folder, "abuild.in")
        if os.path.isfile(src_rootbld):
            sharedir = os.path.join(self.package_folder, "share", "abuild-rootbld")
            os.makedirs(sharedir, exist_ok=True)
            shutil.copy2(src_rootbld, os.path.join(sharedir, "abuild.in"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
