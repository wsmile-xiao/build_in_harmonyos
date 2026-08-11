#!/usr/bin/env python3
"""Conan recipe — cyrus-sasl 2.1.28 (autotools)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout



class CyrusSaslConan(ConanFile):
    name = "cyrus-sasl"
    version = "2.1.28"
    license = "BSD-4-Clause"  # CMU/Cyrus BSD 风格（见 COPYING）
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("lmdb/0.9.35")
        self.requires("sqlite3/3.49.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # cyrus-sasl 2.1.28 是老代码：sample/client.c 调 getpass() 等，musl 无原型，
        # clang 15 默认把 implicit-function-declaration / int-conversion 升为 error。
        # 降回 warning（发行版编老代码通用做法），不影响库本体正确性。
        tc.extra_cflags.append("-Wno-error=implicit-function-declaration")
        tc.extra_cflags.append("-Wno-error=int-conversion")
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--disable-gssapi")
        # sample/ 示例程序调 getpass()——musl 无此符号(已废弃移除)，链接 undefined symbol。
        # 示例非库本体，直接不编。
        tc.configure_args.append("--disable-sample")
        # saslauthd 是服务端守护(需 PAM/shadow，OHOS 无)，非库本体，不编。
        tc.configure_args.append("--without-saslauthd")
        tc.configure_args.append("--enable-login")
        tc.configure_args.append("--enable-ntlm")
        tc.configure_args.append("--enable-srp")
        tc.configure_args.append("--enable-sql")
        # SQL auxprop 插件只用 sqlite3：不显式禁掉 mysql/pgsql 时 configure 会给 libsql 挂
        # -lmysqlclient -lpq，OHOS 无这两个库 → ld.lld unable to find library。
        tc.configure_args.append("--without-mysql")
        tc.configure_args.append("--without-pgsql")
        tc.configure_args.append("--with-dblib=lmdb")
        tc.configure_args.append("--with-openssl={}".format(self.dependencies["openssl"].package_folder))
        tc.configure_args.append("--with-sqlite3={}".format(self.dependencies["sqlite3"].package_folder))
        # cyrus-sasl 的 configure 用 AC_PROG_CC_FOR_BUILD 探测「build 机编译器」——它清掉 host 前缀、
        # 裸搜 gcc/cc/cl.exe，而 OHOS 只有 clang（无 gcc/cc）→ `no acceptable C compiler found`。
        # 本机原生构建 build==host，build 编译器就是 clang，显式喂进去即可。
        tc.configure_args.append("CC_FOR_BUILD=clang")
        tc.configure_args.append("CPP_FOR_BUILD=clang -E")
        tc.generate()
        # lmdb 无 --with-lmdb 旗标：靠 AutotoolsDeps 把依赖的 -I/-L/-l 注入 configure，
        # 让 cyrus-sasl 的 AC_CHECK_HEADERS(lmdb.h)/AC_CHECK_LIB(lmdb) 找得到（同 krb5 lmdb KDB 做法）。
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # 鸿蒙 PC：HMDFS 默认 TMPDIR（/storage/.../tmp）不可写，configure 的 conftest /
        # mktemp 会 Permission denied。指到 conan build 目录下（可写）。同 krb5 做法。
        import os
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp

        autotools = Autotools(self)
        # 发布 tarball（ftp.gnu.org 那类）里带现成的 configure，直接用；
        # 但 **GitHub 的 archive tarball 从不含 configure**（它只是 git tree 的快照，
        # configure 是 autoreconf 的产物、不进版本库），此时必须先自举。
        # 判在运行期而非生成期：同一份配方两种源都能用。
        import os as _os
        if not _os.path.isfile(_os.path.join(self.source_folder, "", "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            # **必须在源码所在子目录里跑**：判定用的是 SRC_SUBDIR，执行也要一致。
            # 实测 libmspack/1.11：源码是 `libmspack/configure.ac`，在顶层 autoreconf
            # 直接报 `autoreconf: error: 'configure.ac' is required`。
            autotools.autoreconf(build_script_folder=_os.path.join(
                self.source_folder, ""))
        # ⚠️ umask / uname 这类对 configure 脚本本身的修补**必须在 autoreconf 之后**：
        # 自举会重新生成 configure，放在前面等于白改（改的是不存在的文件，
        # 或改完又被覆盖）。
        import glob, os
        for _cfg in glob.glob(os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        import os
        _shim = os.path.join(self.build_folder, '_uname_shim')
        os.makedirs(_shim, exist_ok=True)
        _u = os.path.join(_shim, 'uname')
        with open(_u, 'w') as _f:
            _f.write('#!/bin/sh\ncase "${1:-}" in\n  -s|"") echo Linux ;;\n  -r) echo 6.6 ;;\n  -m) echo aarch64 ;;\n  *) exec /system/bin/uname "$@" 2>/dev/null || exec /bin/uname "$@" ;;\nesac\n')
        os.chmod(_u, 0o755)
        os.environ['PATH'] = _shim + os.pathsep + os.environ.get('PATH', '')
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        import glob, os
        # 删掉 libtool .la：libdir='//lib'（prefix=/ 烤死）+ dependency_libs 里烤死了构建机
        # conan cache 的绝对路径（.conan2/p/xxx/lib），换机即失效，下游 libtool 链接会踩坑。
        # 链接信息已由 .pc + cpp_info 提供，.la 无用。递归扫（插件在 lib/sasl2/ 子目录，共 12 个）。
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "**", "*.la"),
                             recursive=True):
            os.remove(_la)
        # bin/ 里的 saslpasswd2 / sasldblistusers2 / pluginviewer 保留：saslpasswd2 正是
        # 用来往本包所带 sasldb 插件的口令库里建/改用户口令的，deploy sasldb 认证的用户需要它；
        # 三者在 conan VirtualRunEnv 下能正常运行（其 RUNPATH=//lib 由 LD_LIBRARY_PATH 覆盖、无害）。
        # 清理 upstream libsasl2.pc 的 Libs.private：libsasl2.so 依赖已静态焊入（DT_NEEDED 仅
        # libc），原列表把插件的静态 dep（sqlite3/lmdb/ssl/crypto）误列进来，仅静态链接才读、
        # 会误导下游；改为只留真实系统库。
        _pc = os.path.join(self.package_folder, "lib", "pkgconfig", "libsasl2.pc")
        if os.path.exists(_pc):
            _lines = []
            for _ln in open(_pc, encoding="utf-8"):
                if _ln.startswith("Libs.private:"):
                    _ln = "Libs.private: -ldl -lm -lpthread\n"
                _lines.append(_ln)
            open(_pc, "w", encoding="utf-8").writelines(_lines)
        # 拷上游许可证（CMU/Cyrus BSD 风格）到 licenses/（合规惯例）
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))



    def package_info(self):
        explicit_libs = ['sasl2']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "cyrus-sasl")
        self.cpp_info.set_property("cmake_target_name", "cyrus-sasl::cyrus-sasl")
        pkg = "" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ['dl', 'm', 'pthread']
        import os
        # 机制/auxprop 插件是运行期 dlopen 进来的。libsasl2 的编译期默认插件目录被烤成
        # //lib/sasl2（=/lib/sasl2，prefix=/），conan 包重定位后指不到真实插件目录 →
        # 消费方若只调 sasl_client_init(NULL) 会找不到 PLAIN/SCRAM 等插件、只剩内建 EXTERNAL。
        # 经 conan VirtualRunEnv 暴露 SASL_PATH 指向包内插件目录，消费方即可开箱发现全部插件。
        self.runenv_info.define_path(
            "SASL_PATH", os.path.join(self.package_folder, "lib", "sasl2"))

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
