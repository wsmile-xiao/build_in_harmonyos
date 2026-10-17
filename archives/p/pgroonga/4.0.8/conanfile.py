#!/usr/bin/env python3
"""Conan recipe — pgroonga 4.0.8 (Meson, PostgreSQL 扩展).

PGroonga 是基于 Groonga 的 PostgreSQL 全文检索扩展：它注册 `pgroonga` 索引访问方法
（Index AM），提供 `&@` / `&@~` / `&~` 等运算符、`pgroonga_*` 系列函数，以及
正则 / 相似度 / JSONB / 语义检索能力。产物是一组 **PostgreSQL shared module**
（`pgroonga.so` 等）+ `share/extension/` 下的 control 与 SQL 安装脚本。

OHOS 适配要点（详见 README.md 与 knowledge/drafts/ 中的三条草稿）：

1. **PostgreSQL 走 tool_requires**。CI 的 `-pr:b` 与 `-pr:h` 是同一个 OHOS profile，
   tool_requires 因此直接解析到已发布的 OHOS 制品 `postgresql/18.3`，一次下载即得到
   `include/postgresql/server/`（服务端头）、`lib/postgresql/`（pkglibdir）、
   `lib/postgresql/pgxs/`（PGXS）与全套服务端可执行文件（initdb/postgres/pg_ctl/
   psql/pg_regress），无需像 postgresql-topn 那样在构建期自举一份 PG 源码树。
2. **pg_config shim**。上游 meson.build 通过 `pg_config --includedir-server /
   --pkglibdir / --sharedir / --bindir / --cppflags / --cflags_sl` 反查 PG 安装位置，
   而 Conan 打包的 postgresql 是 DESTDIR 可重定位安装（configure 前缀为空），
   `pg_config` 会回 `//include/postgresql/server`、`//lib` 这类不可用路径。
   generate() 因此生成一个 pg_config shim，把这几条查询重定向到包内真实目录。
3. **groonga 的 .pc 不能用**，必须由 Conan 的 PkgConfigDeps 重新生成（上游 tarball 里
   烘焙了构建机前缀）。配方 `generators = "PkgConfigDeps"`，
   MesonToolchain 自动把 generators 目录写进 `pkg_config_path`。
4. **不安装进 PostgreSQL 目录**（`-Dinstall_to_postgresql=false`），产物落在包内的
   `lib/` 与 `share/extension/`，消费侧通过 PG 18 的 `extension_control_path` /
   `dynamic_library_path` 指向即可。

上游自带的 rubygem 回归入口（`-Dtest=true` → `find_program('ruby')`）在 OHOS 上不可用，
因此构建期显式关闭（`-Dtest=false`），回归测试改在 test_package 中用 PG 官方
`pg_regress` 直接驱动（不需要 ruby）。
"""
import os
import shutil
import stat
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.meson import Meson, MesonToolchain

# 鸿蒙 ELF 重签名工具（E077：内核只让装载带有效 .codesign 段的 ELF）
HNP_BIN = "/data/service/hnp/bin"


class PgroongaConan(ConanFile):
    name = "pgroonga"
    version = "4.0.8"
    description = ("Super fast and all languages supported full text search index "
                   "based on Groonga")
    license = "PostgreSQL"
    homepage = "https://pgroonga.github.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # 上游用 pkg-config 找 groonga；groonga 包内的 groonga.pc 烘焙了构建机前缀，
    # 必须由 Conan 重新生成。
    generators = "PkgConfigDeps"

    _PG_VERSION = "18.3"

    # 随包发布的上游回归套件清单（供 test_package 使用）
    _UPSTREAM_TEST_DIRS = ("sql", "expected", "test")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # groonga 是 pgroonga 的检索引擎（shared_module 直接链接 libgroonga.so）。
        #
        # run=True 不是装饰：pgroonga 的产物是 **shared module**（package_type SHARED），
        # Conan 对 SHARED 包的传递依赖会把 traits 压成 headers=False / libs=False /
        # run=require.run（requires.py:transform_downstream），而 groonga/16.0.8 声明的是
        # package_type=library + shared=False（STATIC）→ 它自己的 run trait 是 False。
        # 两者相乘的结果是「整条 groonga 闭包 files=False」，于是 Conan 在 test_package
        # 图里把 groonga 标成 `Skipped binaries`、package_folder 直接是 None，
        # 运行期 LD_LIBRARY_PATH 里就没有 <groonga>/lib，PG 后端 dlopen pgroonga.so 时
        # 报 `Error loading shared library libgroonga.so.0: (needed by .../pgroonga.so)`。
        # 显式 run=True 把 groonga 钉回运行期闭包（也让使用者的 conanrun.sh 带上它的
        # libdir），语义上正是事实：pgroonga.so 的 DT_NEEDED 里就有 libgroonga.so.0。
        # lz4 / zlib 不必加：已发布的 groonga 包只装 libgroonga.so*（无 .a），
        # 而 libgroonga.so.0 的 DT_NEEDED 只有 libc++_shared.so 与 libc.so，
        # 它们已被静态链入；msgpack / libxxhash 同理（包内只有 .a）。
        self.requires("groonga/16.0.8", run=True)
        # 上游 meson_options 里 message_pack / xxhash 的默认值是 auto：
        # 找得到就启用。这里显式钉住，避免 CI 上因探测结果漂移导致产物特性变化。
        self.requires("msgpack/7.0.1")
        self.requires("libxxhash/0.8.3")

    def build_requirements(self):
        # PostgreSQL 只在构建/测试期需要（头文件 + 服务端二进制）
        self.tool_requires("postgresql/18.3")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── pg_config shim ────────────────────────────────────────────────────
    def _pg_package_folder(self):
        try:
            return self.dependencies.build["postgresql"].package_folder
        except Exception as exc:  # pragma: no cover - 只在依赖缺失时触发
            raise ConanException(
                "postgresql/%s tool_requires 未解析到包目录: %s"
                % (self._PG_VERSION, exc))

    def _write_pg_config_shim(self, pg_pkg):
        """生成一个只改路径类查询的 pg_config 包装脚本。

        Conan 打包的 postgresql 用 DESTDIR 安装、configure 前缀为空，所以
        `pg_config --includedir-server` 会回 `//include/postgresql/server`
        （`//` 在 Linux 上等价于 `/`，指向系统根目录而非包目录）。
        上游 meson.build 用 run_command 拿这些路径，所以必须在 configure 之前
        把查询重定向到包内真实目录。未知参数原样转发给真 pg_config。
        """
        real = os.path.join(pg_pkg, "bin", "pg_config")
        if not os.path.isfile(real):
            raise ConanException("pg_config not found at %s" % real)

        inc_server = os.path.join(pg_pkg, "include", "postgresql", "server")
        inc = os.path.join(pg_pkg, "include")
        pkglibdir = os.path.join(pg_pkg, "lib", "postgresql")
        sharedir = os.path.join(pg_pkg, "share", "postgresql")
        bindir = os.path.join(pg_pkg, "bin")
        libdir = os.path.join(pg_pkg, "lib")
        pgxs = os.path.join(pkglibdir, "pgxs", "src", "makefiles", "pgxs.mk")

        script = """#!/bin/sh
# pg_config shim — 由 conanfile.py generate() 生成，勿手工编辑。
# 仅重定向「路径类」查询；其余参数（--version/--configure/...）转发给真 pg_config。
REAL="%s"
case "$1" in
  --includedir)        echo "%s" ;;
  --includedir-server) echo "%s" ;;
  --pkglibdir)         echo "%s" ;;
  --sharedir)          echo "%s" ;;
  --bindir)            echo "%s" ;;
  --libdir)            echo "%s" ;;
  --pgxs)              echo "%s" ;;
  --cppflags)          echo "-I%s -I%s" ;;
  --cflags_sl)         echo "-fPIC" ;;
  *)                   exec "$REAL" "$@" ;;
esac
""" % (real, inc, inc_server, pkglibdir, sharedir, bindir, libdir, pgxs,
            inc_server, inc)

        shim_dir = os.path.join(self.generators_folder, "pgsql-bin")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "pg_config")
        with open(shim, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(script)
        os.chmod(shim, os.stat(shim).st_mode | stat.S_IXUSR | stat.S_IXGRP
                 | stat.S_IXOTH)
        return shim

    def generate(self):
        # meson 需要能找到 AR；OHOS aarch64 上用 llvm-ar
        ar_path = shutil.which("llvm-ar") or shutil.which("ar")
        if ar_path:
            os.environ["AR"] = ar_path

        pg_pkg = self._pg_package_folder()
        shim = self._write_pg_config_shim(pg_pkg)

        tc = MesonToolchain(self)
        tc.default_library = "shared" if self.options.shared else "static"
        # 不装进 PostgreSQL 安装目录：产物落在 <pkg>/lib 与 <pkg>/share/extension。
        tc.project_options["install_to_postgresql"] = False
        # ConanToolchain 默认把 datadir 设为 resdirs[0]（"res"），这里改回 share，
        # 让扩展脚本落在 share/extension（与真实 PG 安装布局一致）。
        tc.project_options["datadir"] = "share"
        # 上游默认 auto：显式 enabled 与 requirements() 中钉住的依赖保持一致。
        tc.project_options["message_pack"] = "enabled"
        tc.project_options["xxhash"] = "enabled"
        # 上游 test=true 会 find_program('ruby')（跑 test/prepare.rb 生成 schedule）。
        # OHOS 无 ruby；回归测试改由 test_package 用 pg_regress 直接驱动。
        tc.project_options["test"] = False
        tc.project_options["pg_config"] = shim
        tc.generate()

    def build(self):
        if not shutil.which("meson"):
            self.run(f"{sys.executable} -m pip install --user meson")
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

        # 随包发布上游回归套件，供 test_package 用 pg_regress 驱动。
        # pg_regress 以 --inputdir 为根，按 <inputdir>/sql/<name>.sql 找用例、
        # <inputdir>/expected/<name>.out 找 oracle，所以保持原目录结构。
        upstream_dst = os.path.join(self.package_folder, "upstream")
        for sub in self._UPSTREAM_TEST_DIRS:
            src = os.path.join(self.source_folder, sub)
            if os.path.isdir(src):
                copy(self, "*", src=src, dst=os.path.join(upstream_dst, sub))
        # --launcher 必须是可执行的：copy() 不保留权限位
        launcher = os.path.join(upstream_dst, "test", "short-pgappname")
        if os.path.isfile(launcher):
            os.chmod(launcher, os.stat(launcher).st_mode | stat.S_IXUSR
                     | stat.S_IXGRP | stat.S_IXOTH)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_package_elfs()

    def _sign_package_elfs(self):
        """给包内所有 ELF 重新签名（E077）。

        鸿蒙内核只让装载带有效 ``.codesign`` 段的 ELF：没有被签的
        ``lib/pgroonga.so`` 被 PostgreSQL 用 ``dlopen`` 加载时会直接
        ``Error loading shared library ...: Permission denied``（EPERM），
        表现为 test_package 里 pg_regress 的每个用例都报

            ERROR:  could not load library ".../lib/pgroonga.so":
                    Error loading shared library .../pgroonga.so: Permission denied

        这与「库本身有缺陷」是两回事——CI 的失败类别「测试失败」也是误导。
        做法同 ``xxhash/0.8.3``：``llvm-objcopy --remove-section .codesign``
        去掉陈旧签名段后用 ``binary-sign-tool -selfSign 1`` 就地重签；
        只签真实 ELF，跳过版本化 ``.so`` 的软链（否则对同一目标重复签）。
        """
        objcopy = os.path.join(HNP_BIN, "llvm-objcopy")
        signer = os.path.join(HNP_BIN, "binary-sign-tool")
        targets = []
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path):
                    continue
                if ".so" in name or root == os.path.join(self.package_folder, "bin"):
                    if self._is_elf(path):
                        targets.append(path)
        for target in targets:
            self.run('{} --remove-section .codesign "{}"'.format(objcopy, target))
            self.run('{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                signer, target, target))
            os.chmod(target, os.stat(target).st_mode | stat.S_IXUSR
                     | stat.S_IXGRP | stat.S_IXOTH)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def package_info(self):
        # PG 扩展的消费者是 PostgreSQL 服务端而不是链接器；这里只声明布局，
        # 让 conanrun / 消费侧能拿到 lib 与 share 目录。
        self.cpp_info.libs = ["pgroonga"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.bindirs = []
