#!/usr/bin/env python3
"""ircd-irc2 2.11.2p3-dfsg — 经典 IRC 服务器（irc2 系列，C/autotools）。

上游是 1990 年代的 irc2 服务器；源码取 Debian 的 dfsg 版 orig tarball。

**构建方式照抄 Debian 打包的权威步骤**（`debian/rules` 的 override_dh_auto_*），
并针对本环境补三处实测得出的适配点：

  1. 建 `builddir/`，把 `support/configure` 复制进去（irc2 的顶层 `configure` 是自写脚本；
     真正可用的 autoconf 是 `support/configure`；官方做法就是把它拷进独立 builddir 再跑）；
  2. **`builddir` 必须在源码树内**：`config.status` 用 `Makefile:../support/Makefile.in`、
     `version.c.SH:../ircd/version.c.SH.in` 这类**相对上一级**的模板路径；
  3. **`builddir/config.h` 必须先就位**：Makefile 的 `bsd.o: … config.h` 等规则依赖它，
     upstream 由 `support/config.h.dist` 提供（Debian 用自己的 config.h），配方复制前者；
  4. **构建目录要放在可写挂载上**：autoconf 的 `config.status` 会在构建目录内创建临时子目录并
     `rm`/`mv` 文件；实测 conan 缓存所在挂载会拒绝这些操作（`rm: ./confstatXXXX/in: Permission
     denied`、`mv: bad …`），导致 Makefile 生成不出来、`make all` 报 `No rule to make target
     'all'`；换到 `/data/storage/el2/base/cache` 后同一流程正常（实测生成了含 `all:` 的 Makefile）。
     故优先在该可写挂载下构建，不可用时退回 conan 构建目录并在日志里说明。

依赖：`libxcrypt/4.5.2`（libcrypt，`crypt()`）+ `zlib/1.3.1.1`（`--with-zlib`）。
产物：5 个二进制 `ircd`、`chkconf`、`iauth`、`ircd-mkpasswd`、`ircdwatch` → `bin/`。

上游测试：源码树内无 t/、无 test/、无 check 目标 → 上游通过率 N/A（如实披露）。
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

BINARIES = ("ircd", "chkconf", "iauth", "ircd-mkpasswd", "ircdwatch")
# autoconf config.status 在 conan 缓存挂载上做不了它的临时目录 rm/mv（实测），
# 这里优先用已知可写的挂载；不可用则退回构建目录。
SCRATCH_ROOTS = ("/data/storage/el2/base/cache",)


class Ircdirc2Conan(ConanFile):
    name = "ircd-irc2"
    version = "2.11.2p3-dfsg"
    description = ("ircd-irc2 — classic IRC server (irc2 series, C/autotools); "
                   "builds ircd / chkconf / iauth / ircd-mkpasswd / ircdwatch")
    license = "GPL-1.0-or-later"
    homepage = "https://salsa.debian.org/debian/ircd-irc2"
    url = "https://salsa.debian.org/debian/ircd-irc2"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        # 声明 layout 才能让 source_folder 指向真正下载好的源码树
        # （irc2 的构建依赖 builddir 位于源码树内，见 docstring 第 2 点）
        basic_layout(self)

    def requirements(self):
        self.requires("libxcrypt/4.5.2")
        self.requires("zlib/1.3.1.1")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(["--with-zlib", "--enable-ipv6"])
        # 现代 clang 默认 C23：`int f();` 在 C23 里等价 `int f(void)`，
        # 于是 irc2 这种 1990 年代代码里"声明空参、调用带参"的写法会硬报
        # `too many arguments to function call, expected 0, have 2`。
        # Debian 的做法就是追加 `-std=gnu17`（debian/rules 的 DEB_CFLAGS_MAINT_APPEND），
        # 这里照抄以保持与官方构建一致。
        tc.extra_cflags.append("-std=gnu17")
        tc.generate()
        AutotoolsDeps(self).generate()

    # ── 构建目录挑选与准备 ──────────────────────────────────────────────
    def _workdir(self):
        """挑一个能跑 config.status 临时目录套路的构建工作目录。"""
        for root in SCRATCH_ROOTS:
            probe = os.path.join(root, ".ircd-irc2-probe")
            try:
                os.makedirs(root, exist_ok=True)
                with open(probe, "w") as fh:
                    fh.write("probe")
                os.remove(probe)
                return os.path.join(root, "ircd-irc2-%s" % self.version)
            except OSError:
                continue
        self.output.warning(
            "[build] 可写挂载不可用 → 退回 conan 构建目录；"
            "若 config.status 因临时目录 rm/mv 被拒而失败，请参见 notes.md 的环境说明")
        return os.path.join(self.build_folder, "work")

    def build(self):
        # musl/OHOS 的 setpgrp 签名与 irc2 的 2 参调用不兼容 → 先打 portability 补丁
        # （打在源码树上，随后整体复制到工作目录，保证 builddir 内是打过补丁的树）
        apply_conandata_patches(self)
        workdir = self._workdir()
        shutil.rmtree(workdir, ignore_errors=True)
        os.makedirs(workdir, exist_ok=True)
        # 1) 把源码树复制到工作目录（保证 builddir 就在源码树内）
        for entry in os.listdir(self.source_folder):
            src = os.path.join(self.source_folder, entry)
            dst = os.path.join(workdir, entry)
            if os.path.isdir(src):
                shutil.copytree(src, dst, symlinks=True)
            else:
                shutil.copyfile(src, dst)
        # 2) builddir + 复制 support/configure（Debian 的做法）
        builddir = os.path.join(workdir, "builddir")
        os.makedirs(builddir, exist_ok=True)
        shutil.copy(os.path.join(workdir, "support", "configure"),
                    os.path.join(builddir, "configure"))
        os.chmod(os.path.join(builddir, "configure"), 0o755)
        # 3) builddir/config.h：Makefile 的多数规则依赖它（上游由 support/config.h.dist 提供）
        config_dist = os.path.join(workdir, "support", "config.h.dist")
        if os.path.isfile(config_dist):
            shutil.copyfile(config_dist, os.path.join(builddir, "config.h"))
        else:
            raise ConanInvalidConfiguration("缺少 support/config.h.dist，无法生成 builddir/config.h")
        # 4) configure + make（照抄 Debian 的参数）
        #    注意：irc2 的 Makefile 里 `CFLAGS = $(OPTIMIZE) …` **会覆盖**经工具链传入的 CFLAGS
        #    （实测 config.status 记录 'CFLAGS=-O3' 而编译时仍不带 -std=gnu17），
        #    所以生效位置是 configure 的 `OPTIMIZE=` 变量（Debian 亦如此传 OPTIMIZE=-O2）。
        self.run("./configure --with-zlib --enable-ipv6 "
                 "OPTIMIZE='-O2 -std=gnu17' "
                 "--localstatedir=%s" % os.path.join(workdir, "var"),
                 cwd=builddir)
        self.run("make all", cwd=builddir)
        self._builddir = builddir      # 供 package() 使用

    def package(self):
        builddir = getattr(self, "_builddir", None)
        if not builddir or not os.path.isdir(builddir):
            raise ConanInvalidConfiguration("构建目录缺失，无法打包")
        for name in BINARIES:
            src = os.path.join(builddir, name)
            if not os.path.isfile(src):
                raise ConanInvalidConfiguration(
                    "构建产物缺失: %s（irc2 的 make all 未产出该二进制）" % src)
            dest = os.path.join(self.package_folder, "bin", name)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(src, dest)
            os.chmod(dest, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP
                     | stat.S_IROTH | stat.S_IXOTH)
        self.output.info("[package] 安装 %d 个二进制：%s"
                         % (len(BINARIES), ", ".join(BINARIES)))
        for name in ("COPYRIGHT", "LICENSE", "doc/COPYRIGHT"):
            candidate = os.path.join(self.source_folder, name)
            if os.path.isfile(candidate):
                shutil.copyfile(candidate,
                                os.path.join(self.package_folder, os.path.basename(name)))
                break

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
