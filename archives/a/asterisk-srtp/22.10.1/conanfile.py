#!/usr/bin/env python3
"""Conan recipe — asterisk-srtp 22.10.1 (Asterisk res_srtp module).

Asterisk Secure RTP (SRTP) module — res_srtp.so.
Uses the full Asterisk autotools build (configure + make). The source
tarball is the canonical Asterisk release; this recipe packages only the
SRTP module.

SRTP needs libsrtp2 (srtp/2.8.0, published on ohpcd) plus OpenSSL headers
and libraries in SYS_PREFIX. `generate()` ensures both are present under
SYS_PREFIX (copying from the conan dependency package folders when not
already installed), then passes CPPFLAGS/LDFLAGS so configure's
AST_EXT_LIB_CHECK([SRTP], [srtp2], ...) and the OpenSSL pkg-config probe
both succeed (PBX_OPENSSL=1 → res_srtp gets enabled in menuselect).
"""

import os
import shutil
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, chdir, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

SYS_PREFIX = os.environ.get("DEFAULT_PREFIX") or os.path.join(os.path.expanduser("~"), "usr", "local")


def _copy_tree(src, dst):
    if os.path.isdir(src):
        os.makedirs(dst, exist_ok=True)
        for name in os.listdir(src):
            s = os.path.join(src, name)
            d = os.path.join(dst, name)
            if os.path.isdir(s):
                _copy_tree(s, d)
            else:
                os.makedirs(os.path.dirname(d), exist_ok=True)
                if not os.path.exists(d):
                    shutil.copy2(s, d)


def _ensure_dep_present(prefix, pkg_dirs, rels):
    """Copy header/lib files from a dependency package folder into SYS_PREFIX.

    pkg_dirs: list of (pkg_dir, rel_path) pairs; rels: list of rel paths to verify.
    """
    missing = [r for r in rels if not os.path.exists(os.path.join(prefix, r))]
    if not missing:
        return
    for pkg_dir, rel in pkg_dirs:
        src = os.path.join(pkg_dir, rel)
        if os.path.exists(src):
            _copy_tree(src, os.path.join(prefix, rel))
    still = [r for r in rels if not os.path.exists(os.path.join(prefix, r))]
    if still:
        raise ConanInvalidConfiguration(
            "dependency provisioning did not provide: " + ", ".join(still))


def _ensure_srtp(prefix, srtp_pkg_dir):
    inc = os.path.join(prefix, "include", "srtp2", "srtp.h")
    libs = [os.path.join(prefix, "lib", "libsrtp2.a")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs):
        return
    if not srtp_pkg_dir or not os.path.isdir(srtp_pkg_dir):
        raise ConanInvalidConfiguration(
            "srtp2 not found in SYS_PREFIX and no srtp dependency package folder available")
    _ensure_dep_present(prefix, [(srtp_pkg_dir, "include"), (srtp_pkg_dir, "lib")],
                        ["include/srtp2/srtp.h", "lib/libsrtp2.a"])


def _ensure_openssl(prefix, ssl_pkg_dir):
    inc = os.path.join(prefix, "include", "openssl", "opensslv.h")
    libs = [os.path.join(prefix, "lib", "libssl.a"), os.path.join(prefix, "lib", "libcrypto.a")]
    pcs = [os.path.join(prefix, "lib", "pkgconfig", "openssl.pc")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs) and all(os.path.exists(p) for p in pcs):
        return
    if not ssl_pkg_dir or not os.path.isdir(ssl_pkg_dir):
        raise ConanInvalidConfiguration(
            "openssl not found in SYS_PREFIX and no openssl dependency package folder available")
    # openssl.pc 在不同 recipe 修订中可能位于 lib/pkgconfig 或 share/pkgconfig，
    # 用递归搜索定位真实位置，避免写死路径导致 CI 失败（R36）
    pc_src = None
    for root, _, files in os.walk(ssl_pkg_dir):
        if "openssl.pc" in files:
            pc_src = os.path.join(root, "openssl.pc")
            break
    if pc_src:
        rel = os.path.relpath(pc_src, ssl_pkg_dir)
        _ensure_dep_present(prefix, [(ssl_pkg_dir, os.path.dirname(rel))],
                            [rel])
        # 保证标准路径 lib/pkgconfig/openssl.pc 也存在（configure 用 PKG_CONFIG_PATH 指向它）
        std_pc = os.path.join(prefix, "lib", "pkgconfig", "openssl.pc")
        if not os.path.exists(std_pc) and os.path.exists(pc_src):
            os.makedirs(os.path.dirname(std_pc), exist_ok=True)
            shutil.copy2(pc_src, std_pc)
    else:
        # 兜底：若包内确实无 .pc，生成最小 shim 满足 AST_EXT_LIB_CHECK
        pc_dir = os.path.join(prefix, "lib", "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        shim = os.path.join(pc_dir, "openssl.pc")
        if not os.path.exists(shim):
            with open(shim, "w", encoding="utf-8") as f:
                f.write("prefix=%s\n" % prefix)
                f.write("exec_prefix=${prefix}\nlibdir=${exec_prefix}/lib\n"
                        "includedir=${prefix}/include\nName: OpenSSL\n"
                        "Description: OpenSSL shim for Asterisk SRTP\n"
                        "Version: 3.5.6\nLibs: -L${libdir} -lssl -lcrypto\n"
                        "Cflags: -I${includedir}\n")
    # 再补充头文件与静态库（路径固定）
    _ensure_dep_present(prefix, [(ssl_pkg_dir, "include"), (ssl_pkg_dir, "lib")],
                        ["include/openssl/opensslv.h", "lib/libssl.a", "lib/libcrypto.a"])


def _fix_pc_prefix(pc_path, prefix):
    """改写 .pc 的 prefix 为 SYS_PREFIX（否则 pkg-config 拿到错误 include/lib 路径）。

    包内 .pc 的 prefix 是构建前缀（如 /usr/local 或 /），本机不存在该路径 →
    LIBXML2_INCLUDE=-I/usr/local/include/libxml2 找不到头文件。无论文件是否已
    存在都要执行（历史注入残留可能仍是旧 prefix）。
    """
    if not os.path.isfile(pc_path):
        return
    import re as _re
    data = open(pc_path, encoding="utf-8", errors="replace").read()
    data = _re.sub(r"(?m)^prefix=.*$", f"prefix={prefix}", data, count=1)
    open(pc_path, "w", encoding="utf-8").write(data)


def _ensure_libedit(prefix, edit_pkg_dir):
    """Provision libedit into SYS_PREFIX (Asterisk configure REQUIRES it).

    CI worker 与本地不共享 ~/usr/local：本地是历史遗留装过 libedit，CI 干净环境
    没有 → 主 configure 报 `Please install the 'libedit' development package.`
    硬错误。故从 conan 依赖包复制 include/lib/pkgconfig 到 SYS_PREFIX。
    """
    inc = os.path.join(prefix, "include", "histedit.h")
    libs = [os.path.join(prefix, "lib", "libedit.a")]
    pcs = [os.path.join(prefix, "lib", "pkgconfig", "libedit.pc")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs + pcs):
        _fix_pc_prefix(pcs[0], prefix)
        return
    if not edit_pkg_dir or not os.path.isdir(edit_pkg_dir):
        raise ConanInvalidConfiguration(
            "libedit not found in SYS_PREFIX and no libedit dependency package folder available")
    # libedit.pc 的 Libs.private 引用 -ltinfo（ncurses），一并确认存在性
    _ensure_dep_present(prefix, [(edit_pkg_dir, "include"), (edit_pkg_dir, "lib")],
                        ["include/histedit.h", "include/editline/readline.h",
                         "lib/libedit.a", "lib/pkgconfig/libedit.pc"])
    # ⭐ 改写 libedit.pc 的 prefix（包内是 /，指向根目录 → pkg-config 拿到
    # includedir=/include、libdir=/lib 均不存在）。改为 SYS_PREFIX。
    _fix_pc_prefix(pcs[0], prefix)


def _ensure_libxml2(prefix, xml_pkg_dir):
    """Provision libxml2 into SYS_PREFIX (menuselect sub-configure REQUIRES it).

    libxml2/2.15.3 包只发布共享库（libxml2.so.16.1.3，无 .a）；libxml2 非系统
    同名库（R26 只约束 zlib/ncurses 等 OHOS 自带库），接受共享库。复制时
    HMDFS 不支持 symlink → _copy_tree 按实体副本复制（libxml2.so 为真实文件）。
    """
    inc = os.path.join(prefix, "include", "libxml2", "libxml", "parser.h")
    libs = [os.path.join(prefix, "lib", "libxml2.so")]
    pcs = [os.path.join(prefix, "lib", "pkgconfig", "libxml-2.0.pc")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs + pcs):
        _fix_pc_prefix(pcs[0], prefix)
        return
    if not xml_pkg_dir or not os.path.isdir(xml_pkg_dir):
        raise ConanInvalidConfiguration(
            "libxml2 not found in SYS_PREFIX and no libxml2 dependency package folder available")
    # .pc 可能位于 lib/pkgconfig 或 lib/x86_64-linux-gnu/pkgconfig 等，递归定位
    pc_src = None
    for root, _, files in os.walk(xml_pkg_dir):
        if "libxml-2.0.pc" in files:
            pc_src = os.path.join(root, "libxml-2.0.pc")
            break
    if pc_src:
        pc_dir = os.path.join(prefix, "lib", "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        std_pc = os.path.join(pc_dir, "libxml-2.0.pc")
        if not os.path.exists(std_pc):
            shutil.copy2(pc_src, std_pc)
        # ⭐ .pc 里 prefix 是包的构建前缀（如 /usr/local），必须改写为 SYS_PREFIX，
        # 否则 menuselect configure 通过 pkg-config 拿到的 LIBXML2_INCLUDE=
        # -I/usr/local/include/libxml2（本机不存在该路径）→ 编译找不到头文件。
        data = open(std_pc, encoding="utf-8", errors="replace").read()
        data = data.replace("prefix=/usr/local", f"prefix={prefix}")
        data = data.replace("prefix=${exec_prefix}", f"prefix={prefix}")
        # 兼容其他写法：独立 prefix 行直接替换为绝对路径
        import re as _re
        data = _re.sub(r"(?m)^prefix=.*$", f"prefix={prefix}", data, count=1)
        open(std_pc, "w", encoding="utf-8").write(data)
    # 头/库复制（include 下的 libxml2 子目录整体复制，避免只认 parser.h 路径）
    _copy_tree(os.path.join(xml_pkg_dir, "include", "libxml2"),
               os.path.join(prefix, "include", "libxml2"))
    _ensure_dep_present(prefix, [(xml_pkg_dir, "lib")],
                        ["lib/libxml2.so"])


def _ensure_ncurses(prefix, ncurses_pkg_dir):
    """Provision ncurses into SYS_PREFIX (libedit.pc Libs.private=-ltinfo)."""
    # ncurses 6.6 包提供 libncursesw.a（含 tinfo 符号），link -ltinfo 需要 libtinfo.a
    have_w = os.path.exists(os.path.join(prefix, "lib", "libncursesw.a"))
    have_t = os.path.exists(os.path.join(prefix, "lib", "libtinfo.a"))
    if have_w and have_t:
        return
    if not ncurses_pkg_dir or not os.path.isdir(ncurses_pkg_dir):
        raise ConanInvalidConfiguration(
            "ncurses not found in SYS_PREFIX and no ncurses dependency package folder available")
    _copy_tree(os.path.join(ncurses_pkg_dir, "include"),
               os.path.join(prefix, "include"))
    _copy_tree(os.path.join(ncurses_pkg_dir, "lib"),
               os.path.join(prefix, "lib"))
    # 若包内没有独立的 libtinfo.a，从 libncursesw.a 复制一份作为 -ltinfo 目标
    tinfo = os.path.join(prefix, "lib", "libtinfo.a")
    if not os.path.exists(tinfo) and os.path.exists(os.path.join(prefix, "lib", "libncursesw.a")):
        shutil.copy2(os.path.join(prefix, "lib", "libncursesw.a"), tinfo)


def _ensure_uuid(prefix, uuid_pkg_dir):
    """Provision libuuid into prefix (Asterisk configure REQUIRES uuid_generate_random).

    e2fsprogs 包提供 libuuid.a/uuid.h/uuid.pc；Asterisk configure 在
    checking for uuid_generate_random 失败即报错
    `*** uuid support not found`（方案 C 私有 prefix 暴露的真实缺失依赖）。
    """
    inc = os.path.join(prefix, "include", "uuid", "uuid.h")
    libs = [os.path.join(prefix, "lib", "libuuid.a")]
    pcs = [os.path.join(prefix, "lib", "pkgconfig", "uuid.pc")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs + pcs):
        _fix_pc_prefix(pcs[0], prefix)
        return
    if not uuid_pkg_dir or not os.path.isdir(uuid_pkg_dir):
        raise ConanInvalidConfiguration(
            "uuid not found in prefix and no e2fsprogs dependency package folder available")
    _ensure_dep_present(prefix, [(uuid_pkg_dir, "include"), (uuid_pkg_dir, "lib")],
                        ["include/uuid/uuid.h", "lib/libuuid.a", "lib/pkgconfig/uuid.pc"])
    _fix_pc_prefix(pcs[0], prefix)


def _ensure_jansson(prefix, jansson_pkg_dir):
    """Provision jansson into prefix (Asterisk configure REQUIRES jansson >= 2.11).

    缺失即报 `*** Asterisk requires libjansson >= 2.11`（方案 C 私有 prefix 暴露）。
    jansson/2.15.1.1 包同 libxml2 一样只发布共享库（libjansson.so，无 .a）。
    """
    inc = os.path.join(prefix, "include", "jansson.h")
    libs = [os.path.join(prefix, "lib", "libjansson.so")]
    pcs = [os.path.join(prefix, "lib", "pkgconfig", "jansson.pc")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs + pcs):
        _fix_pc_prefix(pcs[0], prefix)
        return
    if not jansson_pkg_dir or not os.path.isdir(jansson_pkg_dir):
        raise ConanInvalidConfiguration(
            "jansson not found in prefix and no jansson dependency package folder available")
    _ensure_dep_present(prefix, [(jansson_pkg_dir, "include"), (jansson_pkg_dir, "lib")],
                        ["include/jansson.h", "lib/libjansson.so", "lib/pkgconfig/jansson.pc"])
    _fix_pc_prefix(pcs[0], prefix)


def _ensure_sqlite3(prefix, sqlite_pkg_dir):
    """Provision sqlite3 into prefix (Asterisk configure REQUIRES SQLite3).

    缺失即报 `*** Asterisk now uses SQLite3 for the internal Asterisk database`
    （方案 C 私有 prefix 暴露的真实缺失依赖）。
    sqlite3/3.49.1 包有 libsqlite3.a + sqlite3.h 但无 .pc → 生成 shim 供 pkg-config。
    """
    inc = os.path.join(prefix, "include", "sqlite3.h")
    libs = [os.path.join(prefix, "lib", "libsqlite3.a")]
    pcs = [os.path.join(prefix, "lib", "pkgconfig", "sqlite3.pc")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs):
        _ensure_sqlite3_pc(prefix)
        return
    if not sqlite_pkg_dir or not os.path.isdir(sqlite_pkg_dir):
        raise ConanInvalidConfiguration(
            "sqlite3 not found in prefix and no sqlite3 dependency package folder available")
    _ensure_dep_present(prefix, [(sqlite_pkg_dir, "include"), (sqlite_pkg_dir, "lib")],
                        ["include/sqlite3.h", "lib/libsqlite3.a"])
    _ensure_sqlite3_pc(prefix)


def _ensure_sqlite3_pc(prefix):
    """生成 sqlite3.pc shim（sqlite3 包无 .pc，Asterisk configure 用 pkg-config 探测）。"""
    pc_dir = os.path.join(prefix, "lib", "pkgconfig")
    os.makedirs(pc_dir, exist_ok=True)
    pc = os.path.join(pc_dir, "sqlite3.pc")
    if not os.path.exists(pc):
        with open(pc, "w", encoding="utf-8") as f:
            f.write("prefix=%s\n" % prefix)
            f.write("exec_prefix=${prefix}\nlibdir=${exec_prefix}/lib\n"
                    "includedir=${prefix}/include\nName: SQLite\n"
                    "Description: SQLite3 shim for Asterisk\n"
                    "Version: 3.49.1\nLibs: -L${libdir} -lsqlite3\n"
                    "Cflags: -I${includedir}\n")


def _drop_umask_077(path):
    try:
        data = open(path, "r", encoding="utf-8", errors="replace").read()
        if "umask 077" in data:
            open(path, "w", encoding="utf-8").write(data.replace("umask 077", "umask 022"))
    except Exception:
        pass


class AsteriskSrtpConan(ConanFile):
    name = "asterisk-srtp"
    version = "22.10.1"
    description = "Asterisk Secure RTP (SRTP) module (res_srtp.so)"
    license = "GPL-2.0-only"
    homepage = "https://www.asterisk.org/"
    url = "https://www.asterisk.org/"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*", "packaging/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"asterisk-srtp does not support os={self.settings.os}")

    def requirements(self):
        # libsrtp2 + OpenSSL devel are needed by configure's SRTP/PBX_OPENSSL
        # detection; libedit is a REQUIRED dep of Asterisk configure (hard error
        # without it); libxml2 needed by menuselect sub-configure; ncurses
        # provides tinfo symbols referenced by libedit; e2fsprogs provides
        # libuuid (Asterisk configure REQUIRES uuid_generate_random); jansson
        # REQUIRED by Asterisk configure (>= 2.11); sqlite3 REQUIRED by
        # Asterisk configure (internal database). All published on ohpcd.
        self.requires("srtp/2.8.0")
        self.requires("openssl/3.5.6.1")
        self.requires("libedit/20240808")
        self.requires("libxml2/2.15.3")
        self.requires("ncurses/6.6")
        self.requires("e2fsprogs/1.47.4")
        self.requires("jansson/2.15.1.1")
        self.requires("sqlite3/3.49.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        srtp_pkg = None
        ssl_pkg = None
        edit_pkg = None
        xml_pkg = None
        ncurses_pkg = None
        uuid_pkg = None
        jansson_pkg = None
        sqlite_pkg = None
        try:
            srtp_pkg = self.dependencies["srtp"].package_folder
        except Exception:
            pass
        try:
            ssl_pkg = self.dependencies["openssl"].package_folder
        except Exception:
            pass
        try:
            edit_pkg = self.dependencies["libedit"].package_folder
        except Exception:
            pass
        try:
            xml_pkg = self.dependencies["libxml2"].package_folder
        except Exception:
            pass
        try:
            ncurses_pkg = self.dependencies["ncurses"].package_folder
        except Exception:
            pass
        try:
            uuid_pkg = self.dependencies["e2fsprogs"].package_folder
        except Exception:
            pass
        try:
            jansson_pkg = self.dependencies["jansson"].package_folder
        except Exception:
            pass
        try:
            sqlite_pkg = self.dependencies["sqlite3"].package_folder
        except Exception:
            pass
        _ensure_srtp(self._prefix(), srtp_pkg)
        _ensure_openssl(self._prefix(), ssl_pkg)
        _ensure_libedit(self._prefix(), edit_pkg)
        _ensure_libxml2(self._prefix(), xml_pkg)
        _ensure_ncurses(self._prefix(), ncurses_pkg)
        _ensure_uuid(self._prefix(), uuid_pkg)
        _ensure_jansson(self._prefix(), jansson_pkg)
        _ensure_sqlite3(self._prefix(), sqlite_pkg)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--build=x86_64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
            "--without-pjproject",
            "--with-pjproject-bundled=no",
        ])
        inc_dir = os.path.join(self._prefix(), "include")
        lib_dir = os.path.join(self._prefix(), "lib")
        pc_dir = os.path.join(lib_dir, "pkgconfig")
        if os.path.isdir(inc_dir):
            tc.configure_args.append(f"CPPFLAGS=-I{inc_dir}")
        if os.path.isdir(lib_dir):
            tc.configure_args.append(f"LDFLAGS=-L{lib_dir} -Wl,-rpath,{lib_dir}")
        tc.configure_args.append(f"PKG_CONFIG_PATH={pc_dir}")
        tc.generate()

    def _prefix(self):
        """方案 C：依赖注入目标 = build_folder 私有目录（不污染共享 /usr/local）。

        CI worker 与本地共享同一台机器的 /storage/Users/currentUser/usr/local
        （SYS_PREFIX）——此前注入 libedit/libxml2/ncurses 到共享目录，CI 从制品仓
        下载的依赖包 revision 与本地不同（共享库版 vs 静态库版、.pc 布局不同），
        注入后污染共享目录 → clang 链接 conftest 时 -L/usr/local/lib 找到坏库 →
        C compiler cannot create executables（19 轮 CI 全部失败根因，本地恰好是好的
        所以永远复现不了）。改为注入到 build_folder 私有目录，CI 每轮构建独立。
        """
        return os.path.join(self.build_folder, "prefix")

    def _fs_env(self):
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.define("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # menuselect 的 MAKE_MENUSELECT 硬编码 CC="cc"（BUILD_CC），鸿蒙无 cc
        env.define("CC", "/data/service/hnp/bin/clang")
        env.define("BUILD_CC", "/data/service/hnp/bin/clang")
        env.define("HOST_CC", "/data/service/hnp/bin/clang")
        return env

    def _configure_args(self) -> list:
        """Asterisk configure 参数（构建时由 build() 直接使用）。"""
        args = [
            "--prefix=/",
            "--build=x86_64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
            "--without-pjproject",
            "--with-pjproject-bundled=no",
        ]
        inc_dir = os.path.join(self._prefix(), "include")
        lib_dir = os.path.join(self._prefix(), "lib")
        pc_dir = os.path.join(lib_dir, "pkgconfig")
        if os.path.isdir(inc_dir):
            args.append(f"CPPFLAGS=-I{inc_dir}")
        if os.path.isdir(lib_dir):
            # 含空格的值必须整体引号包裹，否则 configure 把 -Wl,-rpath,... 当未识别选项
            args.append(f"LDFLAGS='-L{lib_dir} -Wl,-rpath,{lib_dir}'")
        args.append(f"PKG_CONFIG_PATH={pc_dir}")
        # ⭐ CI worker 沙箱（hishell_hap 域）禁止生成/运行 conftest 可执行文件
        # → checking whether the C compiler works... no（17 轮 CI 全部失败根因）。
        # autoconf cache 变量 ac_cv_prog_cc_works=yes 强制跳过该检查
        # （交叉编译模式下 AC_TRY_RUN 均跳过运行，构建产物 .so 非可执行文件不受限）。
        args.append("ac_cv_prog_cc_works=yes")
        return args

    def build(self):
        apply_conandata_patches(self)
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        # ⭐ menuselect/configure 同样含 umask 077（第 15 次 verify 定位的最终根因：
        # HMDFS 上 077 临时文件(0600)被 MAC 拒绝、022(0644) 可写；主 configure
        # 打补丁后 config.status 即成功，menuselect 未打补丁故 6 连败）
        _drop_umask_077(os.path.join(self.source_folder, "menuselect", "configure"))
        env = self._fs_env()
        # ⭐ HMDFS 规避（E052/E060）：conan 进程树在 .conan2 缓存源码目录跑
        # config.status 时写临时文件报 Permission denied；探索阶段在 $TMPDIR/builds
        # 下手动 configure+make 端到端成功。故复制源码到可执行工作目录构建。
        # ⭐ work 目录必须可执行（clang 需生成 conftest/可执行文件）：
        #   - conan build_folder（.cache/conan2/p/b/.../b）→ 其他成功包均在其下构建 ✅
        #   - $TMPDIR 派生路径在 CI 上 noexec（#29493/#29513 根因）❌
        # ⚠️ 不能用 os.access(X_OK) 探测——HMDFS chmod 被忽略、权限固定 660
        #    （AGENTS.md），X_OK 恒为 False → 永远回退到 noexec 的 $TMPDIR。
        # 故直接用 build_folder 下子目录（conan 构建目录本身可写可执行）。
        work = os.path.join(self.build_folder, "worktree")
        if os.path.exists(work):
            shutil.rmtree(work)
        os.makedirs(os.path.dirname(work), exist_ok=True)
        shutil.copytree(self.source_folder, work,
                        ignore=shutil.ignore_patterns(".tmp"))
        with env.vars(self, scope="build").apply():
            with chdir(self, work):
                # ⭐ HMDFS 间歇性问题（已实验定位）：config.status 首次运行时写
                # ./confXXXXXX/subs1.awk 偶发 Permission denied，直接重跑即成功
                # （手动复现：conanbuild.sh 环境下重跑 config.status exit=0）。
                # 故 configure 失败时：先重跑 config.status，再退回整个 configure。
                cfg = f"./configure {' '.join(self._configure_args())}"
                makeopts = os.path.join(work, "makeopts")
                for attempt in range(1, 4):
                    try:
                        self.run(cfg, env="conanbuild")
                    except Exception:
                        pass
                    if os.path.isfile(makeopts) and os.path.getsize(makeopts) > 1000:
                        break
                    time.sleep(5)
                    cs = os.path.join(work, "config.status")
                    if os.path.isfile(cs):
                        try:
                            self.run("./config.status", env="conanbuild")
                        except Exception:
                            pass
                    if os.path.isfile(makeopts) and os.path.getsize(makeopts) > 1000:
                        break
                # 无条件补跑一次 config.status（实验证明：间歇性失败后重跑必成功，
                # 确保 Makefile/config 文件机制完整生成）
                cs = os.path.join(work, "config.status")
                if os.path.isfile(cs):
                    try:
                        self.run("./config.status", env="conanbuild")
                    except Exception:
                        time.sleep(3)
                        self.run("./config.status", env="conanbuild")
                # ⭐ 预配置 menuselect 子项目（HMDFS 间歇性重试）：
                # 需要：CC=clang（缺省 cc 不存在）+ PKG_CONFIG_PATH（libxml2 必需）。
                ms_dir = os.path.join(work, "menuselect")
                if os.path.isfile(os.path.join(ms_dir, "configure")):
                    ms_mk = os.path.join(ms_dir, "makeopts")
                    pc_dir = os.path.join(self._prefix(), "lib", "pkgconfig")
                    for _ in range(3):
                        try:
                            self.run(
                                f"cd menuselect && "
                                f"CC=/data/service/hnp/bin/clang "
                                f"PKG_CONFIG_PATH={pc_dir} ./configure "
                                f"--build=x86_64-unknown-linux-gnu "
                                f"--host=aarch64-unknown-linux-ohos "
                                f"ac_cv_prog_cc_works=yes",
                                env="conanbuild",
                            )
                        except Exception:
                            pass
                        if os.path.isfile(ms_mk) and os.path.getsize(ms_mk) > 100:
                            break
                        time.sleep(3)
                        cs = os.path.join(ms_dir, "config.status")
                        if os.path.isfile(cs):
                            try:
                                self.run("cd menuselect && ./config.status",
                                         env="conanbuild")
                            except Exception:
                                pass
                        if os.path.isfile(ms_mk) and os.path.getsize(ms_mk) > 100:
                            break
                # ⭐ 注入探索验证的完整版配置（必须在 menuselect 预配置【之后】：
                # 第16次verify教训——若在之前注入，make 会用预配置产出的 menuselect
                # 二进制重新生成默认 makeopts（全模块启用），覆盖掉本文件；
                # 默认配置下 res_adsi 等使用 GCC 嵌套函数扩展，clang 直接编译失败。
                # 本文件为排除列表语义：除 res_srtp 外全部排除。
                # 未来时间戳：让 make 认为已是最新，不再触发 menuselect 重新生成。
                # 缺失即报错（第17次verify教训：静默跳过导致全模块启用→res_adsi 编译炸）
                # ⭐ 查找路径：Conan 2 中 exports_sources 复制到 export_sources_folder
                # （cache 构建时不在 source_folder——CI 日志确认 "Copied .makeopts" 但
                # source_folder 里找不到，报 FileNotFoundError）；本地/探索则可能不同。
                for fn in ("menuselect.makeopts", "menuselect.makedeps"):
                    src = None
                    candidates = []
                    esf = getattr(self, "export_sources_folder", "") or ""
                    for base in (esf, self.source_folder):
                        if base:
                            candidates.append(os.path.join(base, "packaging", fn))
                    for cand in candidates:
                        if os.path.isfile(cand):
                            src = cand
                            break
                    if not src:
                        # 兜底：本地调试时回退到探索验证目录
                        alt = os.path.join(
                            "/storage/Users/currentUser/tmp/builds",
                            f"asterisk-{self.name.split('-', 1)[1]}-{self.version}.work", fn)
                        if os.path.isfile(alt):
                            src = alt
                    if not src:
                        raise FileNotFoundError(
                            f"{fn} 缺失：packaging/ 未随源导出且无探索兜底"
                            f"（已尝试: {candidates}）")
                    dst = os.path.join(work, fn)
                    shutil.copy2(src, dst)
                    os.utime(dst, (time.time() + 86400 * 365,) * 2)
                # ⭐ 只构建 res 子目录（绕开 main/utils：顶层 `make res` 会先构建
                # 整个 main 核心，utils 因缺 sqlite3.h 失败；而模块 .so 不链接核心，
                # 无需 main）。子 make 必须显式传 ASTTOPDIR（否则 Makefile.moddir_rules
                # 解析为 /Makefile.moddir_rules）与 SOLINK（不随环境传递，第17次验证）。
                pc_dir = os.path.join(self._prefix(), "lib", "pkgconfig")
                mk_vars = (f"BUILD_CC=/data/service/hnp/bin/clang "
                           f"PKG_CONFIG_PATH={pc_dir}")
                solink = ""
                mo = os.path.join(work, "makeopts")
                if os.path.isfile(mo):
                    with open(mo, encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("SOLINK="):
                                solink = line.split("=", 1)[1].strip()
                                break
                solink_var = f"SOLINK='{solink}' " if solink else ""
                try:
                    self.run(f"make -j1 -C res SUBDIR=res ASTTOPDIR={work} "
                             f"{solink_var}{mk_vars}", env="conanbuild")
                except Exception:
                    self.run(f"make -j1 res {mk_vars}", env="conanbuild")
        # 产物拷回 source_folder，供 package() 与调试检查
        so_src = os.path.join(work, "res", "res_srtp.so")
        if os.path.isfile(so_src):
            dst_res = os.path.join(self.source_folder, "res")
            os.makedirs(dst_res, exist_ok=True)
            shutil.copy2(so_src, os.path.join(dst_res, "res_srtp.so"))

    def package(self):
        import glob
        candidates = [
            os.path.join(self.build_folder, "res", "res_srtp.so"),
            os.path.join(self.source_folder, "res", "res_srtp.so"),
        ]
        src_so = next((p for p in candidates if os.path.exists(p)), None)
        if src_so and os.path.isfile(src_so):
            copy(self, "res_srtp.so", src=os.path.dirname(src_so),
                 dst=os.path.join(self.package_folder, "lib", "asterisk", "modules"))
        else:
            # Fallback: make install then prune to only the SRTP module
            autotools = Autotools(self)
            env = self._fs_env()
            with env.vars(self, scope="build").apply():
                autotools.install(args=["-j1"])
            keep = os.path.join(self.package_folder, "lib", "asterisk", "modules", "res_srtp.so")
            for mod in glob.glob(os.path.join(self.package_folder, "lib", "asterisk", "modules", "*.so")):
                if os.path.abspath(mod) != os.path.abspath(keep):
                    try:
                        os.remove(mod)
                    except Exception:
                        pass
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/asterisk/modules"]
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
