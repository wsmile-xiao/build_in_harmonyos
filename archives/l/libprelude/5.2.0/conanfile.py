#!/usr/bin/env python3
"""Conan recipe — libprelude 5.2.0 (Prelude SIEM 安全通信库) on HarmonyOS PC.

libprelude 是 Prelude SIEM 的通信框架：IDMEF 消息模型、agent/manager 之间的
匿名与证书 TLS 会话、事件上报与连接池。上游只发布 autotools 源码。

上游源码地址（见 conandata.yml 说明）：原官网域名已劫持失效、官方 tarball 404，
故锁定 Prelude-SIEM 官方 GitHub 组织的 tag 归档。该归档是 **autoreconf 输入**：
configure / Makefile.in / config.h.in / build-aux/* 都没有提交进版本库，
所以 build() 必须按上游 autogen.sh 的思路先自举（libtoolize + aclocal +
autoconf + autoheader + automake），再 configure/make。

OHOS 侧的四个真实障碍（详见 notes.md 与知识图谱）：
  * libtool 制品把独立 libltdl 发行版装到了 share/libtool/，libtoolize 期望的
    share/libtool-conan/libltdl/ 里只剩头文件 → libtoolize --ltdl 复制失败 →
    autoreconf 直接 exit 1；本配方改为从 tool_requires 的 libtool 包里物化
    libltdl/，并把 LTDL_INIT 切到 subproject 模式让 libltdl 跑自己的 configure
    （否则父 configure  substituted 出的 LTLIBOBJS 为空，libltdlc.a 缺
    lt__argz.lo，libprelude.so 留下未定义符号）。
  * E007：automake 1.18 自带的 config.guess 不认 `uname -s` = HarmonyOS。
  * E011：HMDFS 下 configure 的 `umask 077` 临时目录不可写 → config.status 失败。
  * E236：gnutls 依赖链制品内的 .la 元数据带着构建机 `//lib` 前缀，libtool
    解析 -lgcrypt 时追 dependency_libs 会报 "not a valid libtool archive"；
    改为把依赖库复制到 build 私有目录并改写 .pc 的 -L（Conan 缓存保持只读）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps


class LibpreludeConan(ConanFile):
    name = "libprelude"
    version = "5.2.0"
    description = ("LibPrelude: the secure agent/manager communication library of the "
                   "Prelude SIEM (IDMEF message model, anonymous and certified TLS "
                   "sessions, event failover)")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/Prelude-SIEM/libprelude"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("prelude", "siem", "idmef", "tls", "security")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libprelude supports Linux/OHOS only, got {self.settings.os}")
        if not self.options.shared:
            # 上游 configure.ac: LT_INIT([dlopen win32-dll disable-static])
            raise ConanInvalidConfiguration(
                "libprelude upstream is shared-only (LT_INIT disable-static); "
                "static libraries are not supported by the upstream build system")

    def requirements(self):
        # 唯一的强制依赖：TLS 会话层（configure.ac 里 PKG_CHECK_MODULES([LIBGNUTLS])
        # 失败即 AC_MSG_ERROR）。PCRE / lua / perl / python / ruby / swig 都是可选
        # 绑定，见 generate() 中的显式关闭。
        self.requires("gnutls/3.8.10")

    def build_requirements(self):
        # GitHub tag 归档没有 configure/Makefile.in，需要 automake + libtool 自举。
        # autoconf 故意 **不** 声明 tool_requires：ohpcd 的 autoconf/2.72 制品里
        # .autoreconf-real 的 shebang 和 PERL5LIB 指向该包自带的 perl/5.42.2，而
        # automake/1.18 制品的 .automake-real shebang 又写死了宿主 perl，两者混用会
        # 在 HNP 上炸出 "Can't load .../auto/Cwd/Cwd.so ... Permission denied"。
        # 宿主 autoconf/autoreconf 已是 2.72（CI 能力矩阵内 ✅），只用制品补 automake
        # 与 libtool 即可，环境保持自洽。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        # 上游 src/Makefile.am 用 `-I$(srcdir)/libprelude-error` 引用**生成**头
        # (prelude-error.h)，VPATH(out-of-tree) 构建时它只存在于 build 树，编译
        # src/common.c 直接 fatal error: 'prelude-error.h' file not found。
        # 所以本配方固定 in-tree 布局（source == build）。
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = ".conan"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── generate ───────────────────────────────────────────────
    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        self._rewrite_pkgconfig_to_la_free_dir()

        tc = AutotoolsToolchain(self)
        # Conan 的 Release 会给 CFLAGS 追加 -DNDEBUG，而上游 9 个测试里有 6 个把
        # 被测 API 写在 assert() 的参数里（tests/idmef.c:18
        # `assert(idmef_message_new(&idmef) == 0)`），NDEBUG 会连调用一起编译掉，
        # 后续解引用空对象直接 SIGSEGV（exit 139）。保持优化等级不变、只不再定义
        # NDEBUG，测试无需任何改动即可全绿。
        tc.ndebug = None
        # 归档没有 configure，AM_MAINTAINER_MODE 默认会要求 maintainer 模式
        tc.configure_args.append("--disable-maintainer-mode")
        # 文档与所有语言绑定都需要 gtkdocize/swig，OHOS 上没有这些生成器
        tc.configure_args.append("--disable-gtk-doc")
        tc.configure_args.append("--disable-easy-bindings")
        for opt in ("swig", "perl", "python2", "python3", "ruby", "lua", "valgrind"):
            tc.configure_args.append(f"--without-{opt}")
        # E063: clang 15 把 int→pointer 等旧代码写法判成错误（upstream
        # src/idmef-class.c:164 在 `const char **` 函数里 `return ret;`），
        # 只降级这几类，不改上游语义。
        for flag in ("int-conversion", "incompatible-pointer-types",
                     "implicit-function-declaration"):
            tc.extra_cflags.append(f"-Wno-error={flag}")
        tc.generate()

    # ── dependency .la relocation workaround (E236) ────────────
    def _dependency_lib_dirs(self):
        dirs = []
        for dep in self.dependencies.host.values():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            for libdir in dep.cpp_info.aggregated_components().libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(folder, libdir)
                if os.path.isdir(path) and path not in dirs:
                    dirs.append(path)
        return dirs

    def _rewrite_pkgconfig_to_la_free_dir(self):
        """E236：把依赖库镜像到 build 私有目录，并让生成的 .pc 只指向该目录。

        制品里的 libgcrypt.la/libgpg-error.la 记录着 `libdir='//lib'`（打包时
        prefix=/），libtool 在一个目录里优先读 .la，会去追 '//lib/libgpg-error.la'
        并报 "not a valid libtool archive"。这里只复制归档/动态库（跳过 .la），
        再把 generators 目录里每个 .pc 的 `-L"${libdir}"` 换成私有目录：链接期
        根本看不到 .la，Conan 缓存也不被改写。
        """
        private_dir = os.path.join(self.build_folder, ".dependency-archives")
        os.makedirs(private_dir, exist_ok=True)
        copied = 0
        for libdir in self._dependency_lib_dirs():
            for entry in sorted(os.listdir(libdir)):
                src = os.path.join(libdir, entry)
                if entry.endswith((".la", ".pkgdef")) or os.path.isdir(src):
                    continue
                if not (entry.endswith((".a", ".so")) or ".so." in entry):
                    continue
                real = os.path.realpath(src)
                if not os.path.isfile(real):
                    continue
                shutil.copy2(real, os.path.join(private_dir, entry))
                copied += 1
        self.output.info(f"[E236] la-free 依赖目录 {private_dir}：{copied} 个归档/库")

        for entry in sorted(os.listdir(self.generators_folder)):
            if not entry.endswith(".pc"):
                continue
            path = os.path.join(self.generators_folder, entry)
            with open(path, encoding="utf-8", errors="surrogateescape") as handle:
                text = handle.read()
            lines = []
            for line in text.splitlines():
                if line.startswith("Libs") and "${libdir}" in line:
                    line = line.replace('"${libdir}"', f'"{private_dir}"')
                lines.append(line)
            with open(path, "w", encoding="utf-8", newline="\n",
                      errors="surrogateescape") as handle:
                handle.write("\n".join(lines) + "\n")

    # ── bootstrap the missing autoreconf output ────────────────
    def _materialize_libltdl(self):
        """从 tool_requires 的 libtool 包里物化独立 libltdl 发行版。

        configure.ac 里 LT_CONFIG_LTDL_DIR([libltdl]) + 顶层 Makefile.am 的
        SUBDIRS = libltdl 都要求源码树里有完整的 libltdl/（自带 pregenerated
        configure）。libtoolize 只会去 share/libtool-conan/libltdl 拿文件，而该
        制品在那个目录里只放了头文件，完整发行版在 share/libtool/ —— 于是
        libtoolize 报一串 "not found" 并返回 1，autoreconf 直接终止。
        """
        folder = self.dependencies.build["libtool"].package_folder
        candidates = [os.path.join(folder, "share", "libtool"),
                      os.path.join(folder, "share", "libtool-conan", "libltdl")]
        ltdl_src = next((c for c in candidates
                         if os.path.isfile(os.path.join(c, "configure"))
                         and os.path.isfile(os.path.join(c, "ltdl.c"))), None)
        if ltdl_src is None:
            raise RuntimeError(f"libtool 包内找不到独立 libltdl 发行版: {candidates}")
        target = os.path.join(self.source_folder, "libltdl")
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(ltdl_src, target)
        # 防御性清理：standalone libltdl 的 configure 没有 AM_MAINTAINER_MODE，
        # 若 Makefile.in 残留未被替换的 @MAINTAINER_MODE_TRUE@ 字面量，make 会把
        # 它当成待生成的目标文件而失败。当前 libtool/2.5.4 制品该文件已无此字面量
        # （实测 0 处），保留这步以兼容历史形态。
        makefile_in = os.path.join(target, "Makefile.in")
        with open(makefile_in, encoding="utf-8", errors="surrogateescape") as handle:
            text = handle.read()
        text = text.replace("@MAINTAINER_MODE_TRUE@ ", "").replace("@MAINTAINER_MODE_TRUE@", "")
        with open(makefile_in, "w", encoding="utf-8", newline="\n",
                  errors="surrogateescape") as handle:
            handle.write(text)
        # 让生成物永远比（父包刚重新生成的）configure.ac / m4 新，避免 maintainer
        # 规则去重跑 aclocal。
        for name in ("aclocal.m4", "configure", "Makefile.in"):
            path = os.path.join(target, name)
            if os.path.isfile(path):
                os.utime(path, None)
        self.output.info(f"[libltdl] 已从 {ltdl_src} 物化")

    def _bootstrap_autotools(self):
        src = self.source_folder
        if os.path.isfile(os.path.join(src, "configure")):
            self.output.info("configure 已存在，跳过自举")
            return
        # 上游 autogen.sh 等价流程（gnulib-tool / gtkdocize 可选项在本树里已就绪：
        # libmissing/ 与 m4/gtk-doc.m4 + gtk-doc.make 都随归档提交）
        self.run('"${LIBTOOLIZE:-libtoolize}" -c --force --automake',
                 cwd=src, env="conanbuild", ignore_errors=True)
        self._materialize_libltdl()
        for cmd in ("aclocal -I m4 -I libmissing/m4", "autoconf", "autoheader",
                    "automake --add-missing --copy --foreign"):
            self.run(cmd, cwd=src, env="conanbuild")
        # libltdl/configure.ac 用 AC_CONFIG_AUX_DIR([../build-aux])，而 libprelude
        # 没有 AC_CONFIG_AUX_DIR —— aux 脚本都落在树根，补一个 build-aux/ 供子配置用
        aux_dir = os.path.join(src, "build-aux")
        os.makedirs(aux_dir, exist_ok=True)
        for script in ("config.guess", "config.sub", "compile", "depcomp",
                       "install-sh", "missing", "ltmain.sh", "test-driver", "ylwrap"):
            root_path = os.path.join(src, script)
            if os.path.isfile(root_path):
                shutil.copy2(root_path, os.path.join(aux_dir, script))
                os.chmod(os.path.join(aux_dir, script), 0o755)

    def _patch_config_guess_for_ohos(self):
        """E007：给自举出来的 config.guess 补 HarmonyOS 识别。

        automake 1.18 自带的 config.guess（FSF 2024-07-27）里没有 HarmonyOS 分支，
        `uname -s` = HarmonyOS 时直接 "cannot guess build type"。按 E007 的铁律不能
        用 --build/--host 伪造三元组绕过（那会让 configure 认定交叉编译，跳过全部
        AC_RUN_IFELSE 探测、生成与平台不符的 config.h），改为注入 case 分支，输出
        标准三元组 aarch64-unknown-linux-ohos。同版本的 config.sub 已认识 `linux-*`，
        无需再补 ohos 分支。
        """
        block = ('    *:HarmonyOS:*:*)\n'
                 '\tGUESS=$UNAME_MACHINE-unknown-linux-ohos\n'
                 '\t;;\n\n'
                 '    *:NetBSD:*:*)')
        patched = []
        for script in ("config.guess", os.path.join("build-aux", "config.guess")):
            path = os.path.join(self.source_folder, script)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8", errors="surrogateescape") as handle:
                text = handle.read()
            if "HarmonyOS" in text:
                continue
            if "    *:NetBSD:*:*)" not in text:
                self.output.warning(f"{script} 里找不到 HarmonyOS 注入锚点，跳过")
                continue
            text = text.replace("    *:NetBSD:*:*)", block, 1)
            with open(path, "w", encoding="utf-8", newline="\n",
                      errors="surrogateescape") as handle:
                handle.write(text)
            os.chmod(path, 0o755)
            patched.append(script)
        self.output.info(f"[E007] config.guess 已支持 HarmonyOS: {patched}")

    def _relax_configure_umask(self):
        """E011：HMDFS 下 configure 的 `umask 077` 建出的临时目录不可写。

        config.status 往 `(umask 077 && mktemp -d ./confXXXXXX)` 里写 subs1.awk 会被
        拒绝（HMDFS 的 UID 映射让 0700 目录对当前进程也不开放写权限），报
        "could not setup config files machinery"。与 ncdc/bsdtar 等配方一致，把
        configure 里的 umask 077 放宽成 022。
        """
        path = os.path.join(self.source_folder, "configure")
        with open(path, encoding="utf-8", errors="surrogateescape") as handle:
            text = handle.read()
        hits = text.count("umask 077")
        if hits:
            with open(path, "w", encoding="utf-8", newline="\n",
                      errors="surrogateescape") as handle:
                handle.write(text.replace("umask 077", "umask 022"))
        self.output.info(f"[E011] configure umask 077→022: {hits} 处")

    # ── build ──────────────────────────────────────────────────
    def _runenv_export(self):
        """测试/链接期需要能看到 la-free 目录里的 .so 与刚构建的 libprelude.so。

        用 `export` 而不是 `VAR=x cmd` 前缀：后者只作用于第一个命令，`cmd || retry`
        里的第二次 make check 会丢库搜索路径。
        """
        dirs = [os.path.join(self.build_folder, ".dependency-archives"),
                os.path.join(self.build_folder, "src", ".libs")]
        dirs += self._dependency_lib_dirs()
        seen, out = set(), []
        for path in dirs:
            if path not in seen:
                seen.add(path)
                out.append(path)
        return 'export LD_LIBRARY_PATH="' + ":".join(out) + ':$LD_LIBRARY_PATH"; '

    def build(self):
        apply_conandata_patches(self)
        self._bootstrap_autotools()
        self._patch_config_guess_for_ohos()
        self._relax_configure_umask()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

        # 上游自带测试：tests/Makefile.am 的 TESTS 共 9 个程序（autotools
        # parallel-tests）。只在 tests 子目录里跑 —— 顶层 `make check` 会先跑
        # vendored gnulib（libmissing）的 160 项 libc/kernel 自检，其中 3 项在
        # HongMeng 内核上按设计失败（见 notes.md），而 libprelude 自身 9 项全绿。
        # 另外必须 cd 进 tests/ 执行：从父目录 `make -C tests check` 会让 libtool
        # wrapper 的 getcwd 解析失败（HMDFS），9 项会全部假失败。
        #
        # 失败后重跑一次：prelude-timer 的回调断言 `elapsed ==
        # prelude_timer_get_expire(&timer->timer)`（tests/prelude-timer.c:34）要求
        # wall-clock 秒差与到期值「精确相等」，在高负载 worker 上会 ±1s 抖动——本机
        # 8 轮命中 1 次，CI 构建 #49675 同样是该项 FAIL(8/9)。这里只做「重跑一次」：
        # 9 个用例、181 处断言、上游源码全不改动（R51 不减少/不跳过用例），第二次仍
        # 失败则构建照红。configure 与编译本身不受影响（该轮日志已进到 make check）。
        self.run(self._runenv_export() + "make check || (echo 'retry'; make check)",
                 cwd=os.path.join(self.build_folder, "tests"), env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 库包只交付 .so/头/ .pc /配置模板：libtool 归档元数据在制品间不可重定位
        # （E236），man 页与 bin/ 下的 prelude-admin / prelude-adduser /
        # libprelude-config 属于 Prelude 服务器侧的运维工具（需要活的 manager 与
        # spool 环境，且 pkg-config 已取代 libprelude-config），不进库包。
        for folder in ("bin", "share/man"):
            shutil.rmtree(os.path.join(self.package_folder, folder), ignore_errors=True)
        for la_file in os.listdir(os.path.join(self.package_folder, "lib")):
            if la_file.endswith(".la"):
                os.remove(os.path.join(self.package_folder, "lib", la_file))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["prelude"]
        # 上游头文件装在 $(prefix)/include/libprelude，libprelude.m4/pkg-config
        # 也都以该目录为 include 根（#include <prelude.h>）
        self.cpp_info.includedirs = ["include/libprelude", "include"]
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("pkg_config_name", "libprelude")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        # libprelude.so 的 DT_NEEDED 里有 gnutls/libgcrypt/libtasn1/libgpg-error 的
        # .so，但 Conan 不会自动把它们带进下游 LD_LIBRARY_PATH：ohpcd 的 gnutls 制品
        # 以 option shared=False 发布、包内却只有 .so（配方 package() 无条件复制
        # .libs/*.so*），require.run 因此为 False。这里按“目录里真的有 .so”来补运行环境，
        # 否则下游一加载 libprelude.so 就报 Error loading shared library libgnutls.so.30。
        for dep in self.dependencies.host.values():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            libdir = os.path.join(folder, "lib")
            if not os.path.isdir(libdir):
                continue
            if any(name.endswith(".so") or ".so." in name for name in os.listdir(libdir)):
                self.runenv_info.append_path("LD_LIBRARY_PATH", libdir)
