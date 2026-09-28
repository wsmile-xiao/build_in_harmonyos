#!/usr/bin/env python3
"""Conan recipe for COIN-OR Bonmin 1.8.9 — OpenHarmony aarch64 port.

Bonmin 是 COIN-OR 的混合整数非线性规划（MINLP）求解器。产物：静态库
`libbonmin.a` + `include/coin/*.hpp`（package_type=library；**无 CLI**，见 ASL 段）。

依赖与探测（W0/设备实测）：
  - `Bonmin/configure` 用 pkg-config 探测三件套 `cbc osi-clp ipopt`，缺一即
    `Required package Cbc or Ipopt not available` 硬错；ohpcd 侧 Osi 由 `coin-or`
    包承载、OsiClp/ClpSolver 由 `clp` 包承载 ⇒ generate() 写 `osi-clp.pc` 兼容
    别名（cbc/2.10.13、cgl/0.60.10.1 同款做法）。
  - **ASL 不在档** ⇒ `AC_COIN_CHECK_PACKAGE(ASL, ipoptamplinterface)` 自动
    `coin_has_asl=no`，`if COIN_HAS_ASL` 结构闸关掉 `libbonminampl.la`、
    `test/unitTest` 的 AMPL 段与 `bin_PROGRAMS=bonmin` ⇒ 本包无 CLI（R38 判
    「库型」，commands.json 不适用）。任务卡的 `--disable-sAMPL-interface` 开关
    在 1.8.9 的 configure 选项表里**不存在**（--help 与全文 0 命中），故不传；
    `test/mytoy.nl` 用例被 `#ifdef COIN_HAS_ASL` 编译期关掉 ⇒ 计 SKIP。
  - FilterSQP / CPLEX 均不在档 ⇒ 对应 AC_COIN_CHECK_PACKAGE 自动跳过（可选依赖）。

平台补丁（3 件，见 conandata.yml）：
  1/2. `config.guess`/`config.sub` 是 2007 旧件（不认 aarch64、不认 linux-musl
       三元组）⇒ 整文件换新件，新件注 `HarmonyOS|HongMeng` 分支 →
       `aarch64-unknown-linux-musl`（与 cbc/clp 的 musl 口径一致）。
  3.   configure 里 config.status 的临时目录 `mktemp -d`（0700）在 HMDFS 落成
       `drwx--S---` 且自身写不进 ⇒ `config.status: creating Makefile` 之后紧跟
       `mv … Permission denied`，**rc=0 但 Makefile/config.h/bonmin.pc 全没生成**
       的假绿 ⇒ 改 `mkdir -p conftmp` + `umask 022`（E678/cbc conftmp 同款）。

链接（coinor 族两个坑的实测组合，缺一不可）：
  - 依赖包 `.la` 内 `libdir='//lib'` 无效 ⇒ libtool 解析 `-lCbc` 报
    `//lib/libCbc.la is not a valid libtool archive`（首测 rc=2）。
  - 但**不能**照 cbc 方案 B 把 `-l*` 换成绝对 `.a` 路径：libtool 会把这些归档
    **合并进本包静态库**（首测 libbonmin.a 膨胀到 1.7 GB、成员内嵌 18 个依赖
    .a；cbc 包 250 MB 同源）。
  - 正解：把**带 .la 的依赖包**的 `-L` 重定向到 build 内 `dep-libs/`（只放 .a
    符号链接、无 .la）：既绕开 .la 解析，又不触发归档合并。实测
    `libbonmin.a`=2.8 MB、成员 62、嵌套 .a=0。

其它硬口径：
  - `CC=clang CXX=clang++` 用**裸名**：绝对路径会命中 coin m4
    `case "$CC" in clang*) ;; cl* | */cl* …` 的 `*/cl*` 分支被判成 MSVC
    ⇒ `coin_cc_is_cl=true` ⇒ pkg-config 全程不跑、configure 直接硬错（实测）；
    worker/设备 PATH 均含 `/data/service/hnp/bin`。
  - `CFLAGS/CXXFLAGS='-O3 -pipe -DNDEBUG'` **双钉**（configure 期 + make 调用行）。
  - 构建产物反假绿断言：configure 后必须真见到 Makefile / config.h /
    config_bonmin.h / bonmin.pc / libtool 才进 make。
"""

import glob
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)
from conan.tools.gnu import PkgConfigDeps


class BonminConan(ConanFile):
    name = "coinor-bonmin"
    version = "1.8.9"
    description = "COIN-OR basic open-source mixed-integer nonlinear programming (MINLP) solver"
    topics = ("coin-or", "bonmin", "minlp", "nlp", "solver")
    url = "https://github.com/coin-or/Bonmin"
    homepage = "https://github.com/coin-or/Bonmin"
    license = "EPL-2.0"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/*"

    # 依赖全部在 ohpcd 在档（W0 conan list 实证）：
    # cbc → coinutils/coin-or/clp/cgl/zlib；coinor-ipopt → mumps/openblas。
    # 显式声明是为了让 Bonmin 的公开头（含 OsiClp/Cbc/Ipopt 头）与静态链接闭包
    # 随 cpp_info.requires 传给消费者。
    _deps = (
        "cbc/2.10.13",
        "coinor-ipopt/3.14.19",
        "clp/1.17.10",
        "coin-or/0.108.12",
        "coinutils/2.11.13",
        "cgl/0.60.10.1",
        "zlib/1.3.1",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        for ref in self._deps:
            self.requires(ref, transitive_headers=True, transitive_libs=True)

    def layout(self):
        # COIN-OR 递归 autotools 不支持 Conan VPATH 布局：源码与构建同目录
        # （与 cbc/2.10.13 同款）。
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        deps = PkgConfigDeps(self)
        deps.generate()

        # Bonmin 的 AC_COIN_CHECK_PACKAGE(CoinDepend, [cbc osi-clp ipopt]) 需要
        # `osi-clp` 这个 pkg-config 模块名；ohpcd 的 clp 包导出名是 `clp`，
        # 故写兼容别名（cbc/2.10.13 generate() 同款），并补上 clp.pc 未导出的
        # OsiClp/ClpSolver 库（clp/1.17.10 的 package_info 只导出 -lClp）。
        clp = self.dependencies["clp"]
        pc = os.path.join(self.generators_folder, "osi-clp.pc")
        with open(pc, "w", encoding="utf-8") as fh:
            fh.write(
                "prefix={prefix}\n"
                "libdir=${{prefix}}/lib\n"
                "includedir=${{prefix}}/include/coin\n"
                "\n"
                "Name: OsiClp\n"
                "Description: OsiClp compatibility alias (coinor-bonmin build)\n"
                "Version: {version}\n"
                "Requires: clp coin-or coinutils\n"
                'Libs: -L"${{libdir}}" -lOsiClp -lClpSolver -lClp\n'
                'Cflags: -I"${{includedir}}"\n'.format(
                    prefix=clp.package_folder, version=str(clp.ref.version)
                )
            )
        self.output.info("osi-clp.pc -> %s" % pc)

    def build(self):
        src = self.source_folder
        bonmin = os.path.join(src, "Bonmin")
        gen = self.generators_folder

        # ── 0) 补丁反静默断言：三件补丁必须真落进源码树 ────────────────────
        guess = os.path.join(bonmin, "config.guess")
        sub = os.path.join(bonmin, "config.sub")
        conf = os.path.join(bonmin, "configure")
        checks = (
            (guess, "*:HarmonyOS:*:*", "0001-config.guess HarmonyOS 分支"),
            (sub, "linux-musl", "0002-config.sub musl 三元组"),
            (conf, "tmp=./conftmp", "0003-configure confstat mkdir"),
        )
        for path, marker, what in checks:
            with open(path, encoding="utf-8", errors="surrogateescape") as fh:
                ok = marker in fh.read()
            if not ok:
                raise ConanException("补丁未生效（%s）: %s 缺少 %r" % (what, path, marker))
            self.output.info("补丁生效核对 OK: %s (%s)" % (what, marker))

        # ── 1) HMDFS 可执行位不持久化：给 aux 脚本统一补 x 位（带反静默回读）──
        self.run(
            "find '%s' -maxdepth 2 -type f \\( -name configure -o -name config.guess "
            "-o -name config.sub -o -name install-sh -o -name ltmain.sh -o -name depcomp "
            "-o -name missing -o -name mkinstalldirs \\) -exec chmod +x {} \\; "
            "&& test -x '%s/configure' && echo 'aux x-bit OK'"
            % (bonmin, bonmin)
        )

        # ── 2) 带 .la 的依赖包 → 本地无 .la 目录（.la 解析 + 归档合并双避）──
        dep_libs = os.path.join(bonmin, "dep-libs")
        self.run("rm -rf '%s' && mkdir -p '%s'" % (dep_libs, dep_libs))
        la_dirs = []
        for require in self.dependencies.values():
            libdir = os.path.join(require.package_folder, "lib")
            if glob.glob(os.path.join(libdir, "*.la")):
                la_dirs.append(libdir)
                for archive in glob.glob(os.path.join(libdir, "*.a")):
                    self.run("ln -sf '%s' '%s/'" % (archive, dep_libs))
        n_link = len(glob.glob(os.path.join(dep_libs, "*.a")))
        if not la_dirs or n_link == 0:
            raise ConanException(
                "dep-libs 未生成（带 .la 依赖 %d 个、链接 .a %d 个）——后续 -L 重定向会静默失效"
                % (len(la_dirs), n_link)
            )
        self.output.info("带 .la 的依赖包 %d 个 → dep-libs 链接 %d 个 .a"
                         % (len(la_dirs), n_link))

        tmpdir = os.path.join(self.build_folder, "tmp-bonmin")
        self.run("mkdir -p '%s'" % tmpdir)

        # ── 3) configure（CFLAGS 双钉·第一钉；CC/CXX 必须裸名，见文件头）────
        shared = self.options.shared
        link_kind = "--enable-shared --disable-static" if shared else "--disable-shared --enable-static"
        self.run(
            "cd '{bonmin}' && TMPDIR='{tmp}' PKG_CONFIG_PATH='{gen}' "
            "CC=clang CXX=clang++ "
            "CFLAGS='-O3 -pipe -DNDEBUG' CXXFLAGS='-O3 -pipe -DNDEBUG' "
            "./configure --prefix=/ {link_kind} --disable-dependency-tracking "
            "--enable-pkg-config".format(
                bonmin=bonmin, tmp=tmpdir, gen=gen, link_kind=link_kind
            )
        )

        # ── 3b) 反假绿：HMDFS 下 configure rc=0 不代表文件真生成 ────────────
        missing = [
            rel for rel in (
                "Makefile",
                "src/Interfaces/config.h",
                "src/Interfaces/config_bonmin.h",
                "bonmin.pc",
                "libtool",
            )
            if not os.path.isfile(os.path.join(bonmin, rel))
        ]
        if missing:
            raise ConanException("configure 假绿：产物缺失 %s" % ", ".join(missing))
        self.output.info("configure 产物 5/5 落地（Makefile/config.h/config_bonmin.h/bonmin.pc/libtool）")

        # ── 4) 把带 .la 依赖包的 -L 重定向到本地无 .la 目录（保留 -l 语义）──
        #    反静默：sed 后逐包 grep 残留，命中即 rc≠0 硬停。首测正是这里
        #    （find -exec 写成 {{}}）静默 no-op，libtool 又去解析
        #    //lib/libCbc.la 报 `is not a valid libtool archive`。
        for libdir in la_dirs:
            self.run(
                "find '%s' -name Makefile -exec sed -i 's|-L%s|-L%s|g' {} \\;"
                % (bonmin, libdir, dep_libs)
            )
            self.run(
                "n=$(find '%s' -name Makefile -exec grep -lF 'L%s' {} \\; | wc -l); "
                "echo 'L-redirect residual(%s)='$n; test \"$n\" = 0"
                % (bonmin, libdir, libdir)
            )

        # ── 5) make（CFLAGS 双钉·第二钉）───────────────────────────────────
        jobs = self.conf.get("tools.build:jobs", default=4)
        self.run(
            "cd '{bonmin}' && MAKEFLAGS='' make -j{jobs} "
            "CFLAGS='-O3 -pipe -DNDEBUG' CXXFLAGS='-O3 -pipe -DNDEBUG'".format(
                bonmin=bonmin, jobs=jobs
            )
        )

        # ── 6) 上游标准 test 套件（test/Makefile.am 的 `test:` 目标）────────
        #   unitTest：OsiTMINLPInterface + Ipopt 全断言（非 AMPL 段）
        #   CppExample：B-BB 求解上游 4 变量 MINLP，期望 obj=-2.500141411335916
        #   test/mytoy.nl：被 `#ifdef COIN_HAS_ASL` 关掉（ASL 不在档）⇒ SKIP
        #   运行期需要 deps 的 lib 目录（libipopt.so），显式注入 LD_LIBRARY_PATH。
        libpath = ":".join(
            os.path.join(r.package_folder, "lib")
            for r in self.dependencies.values()
            if os.path.isdir(os.path.join(r.package_folder, "lib"))
        )
        self.run(
            "cd '{bonmin}' && LD_LIBRARY_PATH='{libpath}' MAKEFLAGS='' make "
            "CFLAGS='-O3 -pipe -DNDEBUG' CXXFLAGS='-O3 -pipe -DNDEBUG' test".format(
                bonmin=bonmin, libpath=libpath
            )
        )

    def package(self):
        bonmin = os.path.join(self.source_folder, "Bonmin")
        self.run(
            "cd '{bonmin}' && MAKEFLAGS='' make "
            "CFLAGS='-O3 -pipe -DNDEBUG' CXXFLAGS='-O3 -pipe -DNDEBUG' "
            "install DESTDIR='{dest}'".format(bonmin=bonmin, dest=self.package_folder)
        )
        # libtool 把依赖绝对路径烤进 .la（同族包 .la 内 libdir='//lib' 即此产物），
        # .la 不进包；链接信息由 package_info()/cpp_info 提供（coinor-ipopt 同款）。
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)
            self.output.info("移除 .la: %s" % la)
        copy(self, "LICENSE",
             src=os.path.join(self.source_folder, "Bonmin"),
             dst=os.path.join(self.package_folder, "licenses"))
        # 反假绿：安装树必须真有库与头（install 阶段的 rc=0 同样不可单独采信）
        libs = glob.glob(os.path.join(self.package_folder, "lib", "libbonmin.*"))
        hdrs = glob.glob(os.path.join(self.package_folder, "include", "coin", "*.hpp"))
        hdrs += glob.glob(os.path.join(self.package_folder, "include", "coin", "BonminConfig.h"))
        if not libs or len(hdrs) < 10:
            raise ConanException("install 假绿：lib=%s hdr=%d" % (libs, len(hdrs)))
        self.output.info("install 清点：lib=%d 头文件=%d"
                         % (len(libs), len(hdrs)))

    def package_info(self):
        self.cpp_info.libs = ["bonmin"]
        self.cpp_info.set_property("pkg_config_name", "bonmin")
        self.cpp_info.set_property("cmake_file_name", "coinor-bonmin")
        self.cpp_info.set_property("cmake_target_name", "coinor-bonmin::coinor-bonmin")
        self.cpp_info.includedirs = ["include/coin"]
        # libbonmin.a 是静态库：消费者必须拿到完整依赖闭包（上游公开头按裸名
        # include Cbc/Clp/Osi/CoinUtils/Ipopt 头，链接期也要这些归档）。
        self.cpp_info.requires = [
            "cbc::cbc",
            "clp::clp",
            "coin-or::coin-or",
            "coinutils::coinutils",
            "cgl::cgl",
            "coinor-ipopt::coinor-ipopt",
            "zlib::zlib",
        ]
