#!/usr/bin/env python3
"""Conan recipe — heimdal 7.8.0 (Kerberos 5 implementation)

heimdal 是 Kerberos 5 认证协议实现（KTH 开发，C 语言，MIT 协议），含
KDC/kinit/klist 等客户端+服务端。autotools 构建（官方 tar.gz 含 configure
构建产物，无需 autogen 自举），自带 hcrypto/roken/com_err/wind 子库自包含。

OHOS 适配要点（同 krb5/1.22.1 先例 + E114/E216 知识）:
- config.guess/config.sub 补鸿蒙识别（0001/0002 patch，同 krb5）;
- E114 ac_tmp/TMPDIR patch（0003）：configure conftest 在 HMDFS 沙箱写临时
  文件被拦（"C compiler cannot create executables"）;
- 依赖：sqlite3（--with-db-type-preference=sqlite）、libedit、gettext
  （libintl）、libxcrypt、flex（tool_requires 构建工具）均制品仓已发布;
- configure 参数参考 Chimera cports：--enable-kcm --without-openssl
  --with-hcrypto-default-backend=hcrypto。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.build import cross_building


class HeimdalConan(ConanFile):
    name = "heimdal"
    version = "7.8.0"
    description = "Heimdal — Kerberos 5 implementation"
    license = "BSD-3-Clause"
    homepage = "https://www.h5l.org/"
    url = "https://github.com/heimdal/heimdal"
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def requirements(self):
        # sqlite 后端（--with-db-type-preference=sqlite 核心）
        # 注意: 用制品仓已发布版本 sqlite3/3.49.1(3.53.3 不在 ohpcd,
        # L0i 门禁 NOT in registry 会拦截, CI 实测)
        self.requires("sqlite3/3.49.1")
        # libedit（--with-libedit，命令行编辑）
        self.requires("libedit/20240808")
        # libxcrypt（--with-libxcrypt，密码哈希）
        self.requires("libxcrypt/4.5.2")
        # readline: lib/sl 的 sl.c 因 HAVE_READLINE 定义引用外部
        # readline/add_history(制品仓已发布 readline/8.3 二进制)。
        # 用 --with-readline 链接真实 readline 库, 不依赖捆绑 libedit。
        self.requires("readline/8.3")
        # 注意: 不声明 ncurses/libedit——heimdal 捆绑的 lib/libedit 子目录
        # configure 需 libcurses/libncurses(tgetent), 而 ncurses/6.4 制品仓
        # 二进制为 shared=False 静态(21b17f8b)与本 profile 不匹配 → 从源码
        # 构建失败(CI 实测 form/Makefile No such file)。改用
        # --without-libedit --without-readline 规避(命令行编辑可选)。
        # 注意: 不声明 gettext——gettext/0.22.5 制品仓二进制配置不匹配
        # (需 57ec024c... 而 ohpcd 只有 6b129b06...) → 从源码构建 → 其配方
        # tool_requires automake/1.16.5 也需从源码构建(无 E114 处理, 失败)。
        # heimdal 的 libintl 是可选(--with-libintl), 去掉后 configure 自动
        # 检测本机 libintl(NLS 可选, libgsf 先例本机有 libintl.a)。

    def build_requirements(self):
        # heimdal configure 的 AM_PROG_LEX 需要 flex——flex 已在 CI 工具链
        # /data/service/hnp/bin 自带（PATH 可见），无需 conan tool_requires。
        # gettext/0.22.5（requirements 依赖）在制品仓无匹配二进制 → 从源码构建，
        # 其配方 tool_requires autoconf/2.71 + automake/1.16.5 + m4/1.4.19 也会
        # 从源码构建（1.16.5 不在制品仓且无 E114 处理，构建失败 CI 实测）。
        # override 到制品仓已发布版本（autoconf/2.72 + automake/1.18 +
        # m4/1.4.19 二进制均在 ohpcd）→ 工具从制品仓下载，不再从源码构建。
        self.tool_requires("autoconf/2.72", override=True)
        self.tool_requires("automake/1.18", override=True)
        self.tool_requires("m4/1.4.19", override=True)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E114: HMDFS 沙箱拦 configure conftest 写临时文件 → ac_tmp 重定向
        # 到可写目录（patch 0003 内嵌 config.status 的 ac_tmp 变量）
        # sqlite/readline include/lib 注入（捆绑 libedit 已跳过, readline
        # 用制品仓 8.3 二进制满足 lib/sl 的 HAVE_READLINE 链接需求）。
        # 注意: 用 configure_args 追加 CPPFLAGS/LDFLAGS 而非 tc.extra_cflags
        # ——extra_cflags 在 conanbuild 环境加载后才生效, 本配方 Autotools
        # configure 命令里实测未带上(create13: CFLAGS 仅 -Wno-error) → readline
        # 检测 "checking for readline... no"。configure_args 直接追加到
        # configure 命令行(abiword 同款, 验证有效)。
        _cpps = []
        _lds = []
        for _dep_name in ("sqlite3", "libxcrypt", "readline"):
            if _dep_name in self.dependencies:
                _dep = self.dependencies[_dep_name]
                _pf = getattr(_dep, "package_folder", None) or ""
                for _i in _dep.cpp_info.includedirs:
                    _cpps.append(_i if (os.path.isabs(_i) or not _pf)
                                else os.path.join(_pf, _i))
                for _l in _dep.cpp_info.libdirs:
                    _lds.append(_l if (os.path.isabs(_l) or not _pf)
                               else os.path.join(_pf, _l))
        if _cpps:
            tc.configure_args.append("CPPFLAGS={}".format(
                " ".join("-I{}".format(i) for i in _cpps)))
        if _lds:
            tc.configure_args.append("LDFLAGS={}".format(
                " ".join("-L{}".format(l) for l in _lds)))
        tc.configure_args.extend([
            "--enable-kcm",
            "--without-openssl",
            "--with-hcrypto-default-backend=hcrypto",
            "--with-db-type-preference=sqlite",
            "--with-sqlite3",
            # 命令行编辑: lib/sl 因 HAVE_READLINE 引用外部 readline,
            # 用制品仓 readline/8.3(--with-readline 链接真实库)
            "--with-readline",
            # otp(一次性密码)可选组件: 其 libotp.so 依赖 __roken_dbm_* 符号
            # 与 sqlite 后端不匹配(链接 undefined, CI 实测) → 禁用(同 Chimera
            # cports --disable-otp)
            "--disable-otp",
            # --with-libintl 已去掉(gettext 依赖未声明, configure 自动检测
            # 本机 libintl, NLS 可选)
            # MAKEINFO=true + --disable-nls: 鸿蒙 CI 无 makeinfo(texinfo),
            # doc 目录生成 heimdal.info 报 "makeinfo: command not found"
            # (Error 127, CI 实测) → makeinfo 无害化(true), NLS 关闭
            "--disable-nls",
            "MAKEINFO=true",
        ])
        tc.generate()

    def build(self):
        # 1) 应用鸿蒙 patches（config.guess/sub + E114 ac_tmp）
        apply_conandata_patches(self)
        # 2) E114: HMDFS 沙箱拦脚本子进程写临时文件——ac_tmp 重定向 + TMPDIR
        #    patch 0003 内嵌 configure 的 ac_tmp=./.ac_tmp(相对路径解析到
        #    build 目录); 但 configure 运行期间 clang conftest 编译还用
        #    $TMPDIR 写临时文件, CI 系统 TMPDIR=/data/storage/el2/base/cache
        #    被 HMDFS 拦 → "C compiler cannot create executables"(CI 实测)。
        #    修法(同 abiword 先例): 配方(主进程)预建可写目录 + 显式设置
        #    os.environ["TMPDIR"] 指向它, 本机 conan 自动重定向 TMPDIR 的
        #    行为在 CI 上不存在, 必须配方自己设。
        #    注意: TMPDIR 必须用**独立目录**(.conan_tmpdir), 不能复用
        #    .ac_tmp——configure 退出时按 trap 会 rm -fr $ac_tmp 清理
        #    .ac_tmp 目录(0003 patch 改的路径), 复用会导致 make 阶段
        #    TMPDIR 指向已删除目录("make: TMPDIR value ... No such file",
        #    create23 实测)。
        _fixed_tmp = os.path.join(self.build_folder, ".conan_tmpdir")
        os.makedirs(_fixed_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _fixed_tmp
        # 3) configure + make
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # conan 2: copy 需从 conan.tools.files 导入后以 copy(self, ...) 调用
        # （不能用 conan 1 的 self.copy(...)，会 AttributeError）
        copy(self, "license*", src=self.source_folder, dst="licenses",
             ignore_case=True, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["krb5", "kdc", "gssapi", "hcrypto", "hdb", "roken", "wind", "heimbase"]
        self.cpp_info.includedirs = ["include", "include/krb5"]
        self.cpp_info.set_property("pkg_config_name", "krb5")
