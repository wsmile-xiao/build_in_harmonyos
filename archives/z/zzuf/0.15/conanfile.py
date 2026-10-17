#!/usr/bin/env python3
"""Conan recipe — zzuf 0.15 (autotools, bootstrap 生成 configure)

zzuf 是透明输入模糊测试工具：LD_PRELOAD 拦截程序的文件读取并随机翻转位。
产物: bin/zzuf(模糊器), bin/zzat(散列/统计工具), lib/zzuf/libzzuf.so(拦截库)。

OHOS 适配要点（R32/R33/R49，均已在本地 W3 实测验证）：
1. 源码包无 configure，需先跑 ./bootstrap (autoreconf) 生成。
2. HMDFS 忽略 chmod、setgid 目录按组权限判定写入：autoconf 生成的临时目录
   umask 077 -> 组无写位，config.status 报 Permission denied。配方在 build
   前以默认 umask 022 运行 bootstrap/configure 命令 (R49 平台限制绕行)。
3. OHOS (musl 派生) libc 的 fortify helper 与 glibc 签名不同且声明受
   __FORTIFY_COMPILATION 门控 (知识 E235 同类)：
   - __fread_chk/__fgets_chk 参数顺序 (ptr,size,count,stream,bos) 与 glibc 不同
     -> 禁用以防隐式声明/误调用；
   - fseeko64/fsetpos64/fpos64_t 是 fseeko/fsetpos/fpos_t 的宏别名且 fpos64_t
     为 union -> LP64 下与标准 64 位接口等价，禁用无损失；
   - __read_chk/__recv_chk/__recvfrom_chk 参数顺序与 glibc 一致且 libc.so 实际
     导出 -> 保留，保证子进程 (cat/dd) 读文件被拦截 (check-utils 92% 断言通过)。
4. OHOS FILE 结构不透明 (bits/alltypes.h: struct _IO_FILE { char __x; })，
   zzuf 的 glibc/FreeBSD/Solaris streambuf 探测在编译期失败 -> 上游
   check-utils 中 ungetc/streambuf 类断言与本机参考 md5 不一致，属平台限制；
   本配方的 test_package 只验证平台可用功能 (确定性/拦截链路/比率语义)。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ZzufConan(ConanFile):
    name = "zzuf"
    version = "0.15"
    description = "Transparent application input fuzzer (zzuf 0.15, Sam Hocevar)"
    license = "WTFPL"
    homepage = "https://github.com/samhocevar/zzuf"
    url = "https://github.com/samhocevar/zzuf"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # autotools bootstrap 需要直接访问源码树（configure.ac/Makefile.am），
        # 且 tarball 无 configure 需就地生成 —— in-source 构建（zopfli 同惯例）
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("zzuf is built for Linux/OHOS only")

    def build_requirements(self):
        # zzuf 0.15 官方 archive 不含 configure，需 ./bootstrap 生成；
        # CI worker 无系统 automake/autoconf/libtool，由 tool_requires 提供
        # （avimetaedit 1.0.2 同型先例）
        self.tool_requires("automake/1.18")
        self.tool_requires("autoconf/2.72")
        self.tool_requires("libtool/2.5.4")

    def generate(self):
        # bootstrap 工具链注入 build PATH（tool_requires bin/ 前置）
        VirtualBuildEnv(self).generate()
        # 编译命令通过 conan profile conf 注入 (tools.build:compiler_executables)
        env = Environment()
        env.define("CFLAGS", f"{self.settings.get_safe('cflags') or ''} -fPIC -O2")
        env.vars(self).save_script("zzuf_env")

    def build(self):
        apply_conandata_patches(self)

        # 1. 生成 configure：zzuf 官方 archive 不含 configure，需 autotools
        #    bootstrap。tool_requires 提供 automake/autoconf/libtool，但
        #    conan 的 perl 包在 HMDFS 不可用（Cwd.so dlopen 失败），且 PATH
        #    中系统旧 automake 优先 —— 按 avimetaedit 1.0.2 先例手动执行
        #    上游 bootstrap 同序序列（libtoolize → aclocal → autoconf →
        #    automake），强制 PERL=系统 perl、PERL5LIB 指向 tool 包 share。
        shell = os.environ.get("CONFIG_SHELL", "bash")
        self.run(
            f"{shell} -c \"set -e"
            f" && export PERL=/data/service/hnp/bin/perl"
            f" && LIBTOOLIZE=$(command -v libtoolize 2>/dev/null || exit 1)"
            f" && sh $LIBTOOLIZE --copy --force"
            f" && ACLOCAL=$(command -v aclocal-1.18 2>/dev/null || command -v aclocal 2>/dev/null || exit 1)"
            f" && unset PERL5LIB"
            f" && export PERL5LIB=$(dirname $(dirname $ACLOCAL))/share/automake-1.18"
            f" && sh $ACLOCAL -I m4"
            f" && AUTOCONF=$(command -v autoconf 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOCONF))/share/autoconf"
            f" && sh $AUTOCONF"
            f" && AUTOHEADER=$(command -v autoheader 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOHEADER))/share/autoconf"
            f" && sh $AUTOHEADER"
            f" && AUTOMAKE=$(command -v automake-1.18 2>/dev/null || command -v automake 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOMAKE))/share/automake-1.18"
            f" && sh $AUTOMAKE --foreign --add-missing --copy\"",
            env="conanbuild",
        )

        # 1b. autoconf 生成的 configure/config.status 内部仍以 umask 077 创建
        #     ./confXXXXXX 临时目录，HMDFS 上组无写位导致 subs1.awk 写入失败
        #     (Permission denied)。对生成脚本做 umask 替换（平台适配，非源码补丁）。
        for script in ("configure", "config.status"):
            path = os.path.join(self.source_folder, script)
            if os.path.exists(path):
                with open(path) as f:
                    content = f.read()
                content = content.replace("umask 077", "umask 022")
                with open(path, "w") as f:
                    f.write(content)

        # 2. configure：显式 build/host 跳过 config.guess，并注入
        #    OHOS fortify/fpos64 符号禁用 cache 变量（见文件头说明）
        cache_vars = " ".join([
            "ac_cv_func___fread_chk=no",
            "ac_cv_func___fgets_chk=no",
            "ac_cv_func_fseeko64=no",
            "ac_cv_func_fsetpos64=no",
            "ac_cv_type_fpos64_t=no",
        ])
        self.run(
            "umask 022 && ./configure --prefix=" + self.package_folder +
            f" --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu "
            f"{cache_vars}",
            env="conanbuild",
        )

        # 3. 编译（-j1 保证顺序，参考上游构建习惯）
        self.run("umask 022 && make -j1", env="conanbuild")

    def package(self):
        # --prefix 已指向 package_folder，直接 make install（无需 DESTDIR）
        self.run("umask 022 && make install")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib", "lib/zzuf"]
        self.cpp_info.libs = ["zzuf"]
        self.cpp_info.includedirs = ["include"]
        # libzzuf.so 存放在 lib/zzuf/ 子目录 (pkglib)，消费端运行期需要该路径
        # （Conan 2 runenv_info 惯例，替代 deprecated env_info）
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH",
            os.path.join(self.package_folder, "lib", "zzuf"),
        )