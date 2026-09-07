#!/usr/bin/env python3
"""Conan recipe — hunspell 1.7.3 (GNU Autotools).

Hunspell is a spell-checker library (libhunspell-1.7) plus command-line tools
(analyze/chmorph/hunspell/munch/unmunch/hzip/hunzip), used by LibreOffice,
Mozilla Firefox, Google Chrome and many others.

OHOS adaptation notes:
  - config.guess is patched so the OHOS build machine (uname -s = HarmonyOS) is
    recognised and emits ``aarch64-unknown-linux-ohos``.
  - hunspell 1.7.3 ships the 2024 config.sub which already validates the
    ``linux-ohos*`` kernel-OS combination natively, so no config.sub patch is
    needed for this version.
  - configure is patched to create its temporary directory under
    ``${TMPDIR:-$HOME/tmp}`` (the OHOS build sandbox restricts ``./confXXXXXX``
    under umask 077).
  - ``--disable-nls``: hunspell's configure uses ``AM_GNU_GETTEXT([external])``
    which would require a host libintl/msgfmt; the pre-built ``po/*.gmo``
    catalogs are not needed by the library consumer.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class HunspellConan(ConanFile):
    name = "hunspell"
    version = "1.7.3"
    description = "Spell checker library and command-line tool used by LibreOffice, Firefox, Chrome"
    license = "LGPL-2.1-or-later"
    homepage = "https://hunspell.github.io"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os 判断必须覆盖 "Linux" 和 "OHOS"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "hunspell recipe currently supports Linux and OHOS builds only"
            )

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self._ensure_tmpdir()
        tc = AutotoolsToolchain(self)
        # NLS 需要外部 gettext/libintl（AM_GNU_GETTEXT external），--disable-nls
        # 让 configure 跳过 libintl probe；翻译语料 po/*.gmo 已随源码预编译。
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-rpath")
        tc.generate()
        # configure 执行期需要 TMPDIR（patch 后 conf 目录建在 ${TMPDIR:-$HOME/tmp}）
        env = Environment()
        env.define("TMPDIR", self._tmpdir())
        env.vars(self).save_script("conanbuild_tmpdir")

    def build(self):
        self._ensure_tmpdir()
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # -j1: OHOS 沙箱不支持 mkfifo（GNU make jobserver），串行构建（先例见 vala）
        autotools.make(args=["-j1"])
        # 上游回归 make check 不集成进 build()：OHOS CI worker 实测（#40559）
        # 145 项中 133 项 FAIL（11 PASS + 1 SKIP）——tests/ 全量 .aff/.dic 回归在
        # conan 分离构建目录（out-of-tree VPATH）下运行，测试数据未落入 builddir，
        # 且驱动的是新编译 hunspell CLI，属沙箱/构建模式环境限制（非产物缺陷）。
        # 消费者视角实质验证由 test_package 承担（R34，见 MANIFEST.yml）。

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # HMDFS 动态链接器无法解析符号链接：把 .so 别名链的符号链接替换为
        # 真实文件副本（E004/1.7.2 notes 同款，libtool 默认只装链的头部为链接）
        self._dereference_shared_aliases()

    def package_info(self):
        self.cpp_info.libs = ["hunspell-1.7"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "hunspell")
        self.cpp_info.set_property("cmake_file_name", "hunspell")
        self.cpp_info.set_property("cmake_target_name", "hunspell::hunspell")
        # 消费方 test 运行期 LD_LIBRARY_PATH 兜底
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )

    # ── Helper methods ──────────────────────────────────────────

    @staticmethod
    def _tmpdir():
        return os.environ.get("TMPDIR") or os.path.join(
            os.path.expanduser("~"), "tmp"
        )

    def _ensure_tmpdir(self):
        tmpdir = self._tmpdir()
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

    def _dereference_shared_aliases(self):
        """把 lib/ 下 .so 符号链接替换为真实文件副本（HMDFS 不解析符号链接）。

        libtool install 生成 libhunspell-1.7.so -> libhunspell-1.7.so.0 ->
        libhunspell-1.7.so.0.0.1 链；逐级解引用到真实文件后，把真实文件
        copy 覆盖到每个别名位置，使包内不存在符号链接。
        注意：必须先 rm 掉符号链接再 cp（否则 cp -a 目标=链接→同一 inode，
        OHOS /system/bin/cp 报 "is the same file" 错误，见 #8449 build #40571）。
        """
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for entry in sorted(os.listdir(libdir)):
            path = os.path.join(libdir, entry)
            if not os.path.islink(path):
                continue
            try:
                target = os.path.realpath(path)
            except OSError:
                continue
            if not os.path.isfile(target):
                continue
            # 只处理本包内的 .so 链，避免误伤
            if os.path.commonpath([libdir, target]) != libdir:
                continue
            self.run(f"rm -f '{path}' && cp -a '{target}' '{path}'")
            self.output.info(f"dereferenced symlink {entry} -> real copy")
