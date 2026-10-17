"""ima-evm-utils 1.5 — IMA/EVM 完整性度量工具库（libimaevm）与 evmctl 工具.

autotools C 项目（configure.ac：AC_INIT v1.5），无预生成 configure，
需 tool_requires automake/libtool 手动 autogen；依赖 openssl（LIBCRYPTO）。
OHOS 适配：config.guess 平台识别 + keyutils 头可选化（OHOS 无 libkeyutils）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, copy, patch
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


class ImaEvmUtilsConan(ConanFile):
    name = "ima-evm-utils"
    version = "1.5"
    license = "GPL-2.0-or-later"
    url = "https://github.com/linux-integrity/ima-evm-utils"
    description = "IMA/EVM integrity measurement utilities (libimaevm + evmctl)"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "patches/*"

    def requirements(self):
        self.requires("openssl/1.1.1w")

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            tc.configure_args += ["--build=aarch64-unknown-linux-ohos",
                                  "--host=aarch64-unknown-linux-ohos",
                                  "--disable-engine"]
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()
        pkg = PkgConfigDeps(self)
        pkg.generate()
        # configure.ac 用 PKG_CHECK_MODULES(LIBCRYPTO, [libcrypto >= 0.9.8])
        # 检测 openssl 的 libcrypto，但 conan openssl 包 PkgConfigDeps 生成的
        # 模块名是 "openssl"（无 libcrypto.pc）→ 走 configure.ac 官方 fallback：
        # 注入 LIBCRYPTO_CFLAGS/LIBCRYPTO_LIBS 环境变量绕过 pkg-config 检测
        if self.settings.os == "OHOS":
            cpp_info = self.dependencies["openssl"].cpp_info
            env = Environment()
            env.define("LIBCRYPTO_CFLAGS", f"-I{cpp_info.includedirs[0]}")
            env.define("LIBCRYPTO_LIBS", f"-L{cpp_info.libdirs[0]} -lcrypto")
            env.vars(self).save_script("conanbuild_libcrypto")

    def source(self):
        get(self, **self.conan_data["package"])
        src = os.path.join(self.source_folder, f"{self.name}-{self.version}")
        os.rename(src, os.path.join(self.source_folder, "s"))
        # keyutils 头可选化（OHOS 无 libkeyutils）：configure.ac 硬性
        # AC_MSG_ERROR 降级为 AC_CHECK_HEADERS。不用外部 patch：
        # 沙箱 toybox patch 0.8.12 静默失败（输出 "patching ..." 但文件不变），
        # conan patch 解析器亦报 incomplete → 直接 Python 字符串替换
        # （与 0002 补丁内容等价）
        src_dir = os.path.join(self.source_folder, "s")
        cfg_ac = os.path.join(src_dir, "configure.ac")
        with open(cfg_ac, encoding="utf-8") as f:
            content = f.read()
        old_line = ("AC_CHECK_HEADERS(keyutils.h, , [AC_MSG_ERROR("
                    "[keyutils.h header not found. You need the libkeyutils "
                    "development package.])])")
        new_line = "AC_CHECK_HEADERS(keyutils.h)"
        assert old_line in content, "keyutils 硬检查行未找到"
        content = content.replace(old_line, new_line)
        with open(cfg_ac, "w", encoding="utf-8") as f:
            f.write(content)
        self.output.info("keyutils.h 检查已降级为可选（Python replace）")
        # evmctl.c：keyutils 依赖条件化（OHOS 无 libkeyutils）——
        # include 用 HAVE_KEYUTILS_H 保护；cmd_import 整体包 #ifdef
        # （无 keyutils 时给 stub 返回错误），Makefile.am 去掉硬链接 -lkeyutils
        evmctl = os.path.join(src_dir, "src", "evmctl.c")
        with open(evmctl, encoding="utf-8") as f:
            c = f.read()
        c = c.replace("#include <keyutils.h>",
                      "#ifdef HAVE_KEYUTILS_H\n#include <keyutils.h>\n#endif")
        start = c.index("static int cmd_import(struct command *cmd)")
        end = c.index("static int setxattr_ima(const char *file, char *sig_file)")
        stub = ("#ifdef HAVE_KEYUTILS_H\n" + c[start:end] +
                "#else\n"
                "static int cmd_import(struct command *cmd)\n"
                "{\n"
                "\tlog_info(\"keyring import requires libkeyutils, "
                "not available on OHOS\\n\");\n"
                "\treturn 1;\n"
                "}\n"
                "#endif\n\n")
        c = c[:start] + stub + c[end:]
        with open(evmctl, "w", encoding="utf-8") as f:
            f.write(c)
        mf_am = os.path.join(src_dir, "src", "Makefile.am")
        with open(mf_am, encoding="utf-8") as f:
            m = f.read()
        m = m.replace("$(LIBCRYPTO_LIBS) -lkeyutils libimaevm.la",
                      "$(LIBCRYPTO_LIBS) libimaevm.la")
        with open(mf_am, "w", encoding="utf-8") as f:
            f.write(m)
        # hash_info.gen 生成的 hash_algo_name 是全局数组定义，evmctl.c 与
        # libimaevm.c 都 include hash_info.h → 链接重复符号；
        # 改为 static（各 TU 私有副本，功能不变）
        hg = os.path.join(src_dir, "src", "hash_info.gen")
        with open(hg, encoding="utf-8") as f:
            g = f.read()
        g = g.replace("const char *const hash_algo_name[HASH_ALGO__LAST]",
                      "static const char *const hash_algo_name[HASH_ALGO__LAST]")
        with open(hg, "w", encoding="utf-8") as f:
            f.write(g)
        # OHOS bionic 的 linux/byteorder/little_endian.h 只有 __be32_to_cpu
        # （值版本），无 __be32_to_cpup（指针版本）→ libimaevm.c/evmctl.c
        # 隐式声明导致链接 undefined symbol；注入 fallback 宏
        for fn in ("libimaevm.c", "evmctl.c"):
            p = os.path.join(src_dir, "src", fn)
            with open(p, encoding="utf-8") as f:
                c = f.read()
            if "__be32_to_cpup" in c and "#define __be32_to_cpup" not in c:
                c = c.replace(
                    "#include <assert.h>\n",
                    "#include <assert.h>\n"
                    "#ifndef __be32_to_cpup\n"
                    "#define __be32_to_cpup(p) "
                    "__builtin_bswap32(*(const unsigned int *)(p))\n"
                    "#endif\n", 1)
                with open(p, "w", encoding="utf-8") as f:
                    f.write(c)
        self.output.info("evmctl keyutils 依赖已条件化（HAVE_KEYUTILS_H）")

    def build(self):
        # OHOS 沙箱默认 umask 077 → autotools 临时目录(0700)不可写
        # （config.status 报 "can't create .../subs1.awk: Permission denied"，
        #  同 librrd 0003 先例），强制 022
        os.umask(0o022)
        src = os.path.join(self.source_folder, "s")
        # 手动 autogen（tarball 无预生成 configure）
        for cmd in ("aclocal", "libtoolize --force --copy --automake",
                    "autoheader", "autoconf", "automake --foreign --copy --add-missing"):
            self.run(cmd, cwd=src)
        # autoconf 生成的 configure/config.status 内部自带 umask 077
        # （OHOS 沙箱 0700 临时目录不可写 → config.status 报 Permission
        #  denied，外部 os.umask 会被脚本覆盖），替换为 022
        # （libneurosim/librrd 先例）；build 目录副本一并处理
        for base in (src, self.build_folder):
            for root, _dirs, files in os.walk(base):
                for fn in files:
                    if fn in ("configure", "config.status"):
                        p = os.path.join(root, fn)
                        with open(p, encoding="utf-8", errors="surrogateescape") as f:
                            c = f.read()
                        if "umask 077" in c:
                            with open(p, "w", encoding="utf-8",
                                      errors="surrogateescape") as f:
                                f.write(c.replace("umask 077", "umask 022"))
                            self.output.info(f"umask 077→022: {p}")
        # config.guess 由 automake --add-missing 生成（无预生成版本）——
        # autogen 后注入 OHOS 识别段（同 libobjfw config.sub 注入先例）：
        # 使 aarch64:OHOS/HarmonyOS 识别为 linux-ohos。
        if self.settings.os == "OHOS":
            cg = os.path.join(src, "build-aux", "config.guess")
            if not os.path.isfile(cg):
                for root, _dirs, files in os.walk(src):
                    if "config.guess" in files:
                        cg = os.path.join(root, "config.guess")
                        break
            if os.path.isfile(cg):
                with open(cg, encoding="utf-8", errors="surrogateescape") as f:
                    content = f.read()
                if "OHOS" not in content:
                    ohos_case = (
                        '    aarch64:OHOS:*:* | aarch64:HarmonyOS:*:*)\n'
                        "        echo ${UNAME_MACHINE}-unknown-linux-ohos\n"
                        "        exit ;;\n"
                    )
                    marker = "    *:Linux:*:*)\n"
                    content = content.replace(marker, marker + ohos_case, 1)
                    with open(cg, "w", encoding="utf-8", errors="surrogateescape") as f:
                        f.write(content)
        autotools = Autotools(self)
        # configure 脚本由 autogen 生成在 src（源码重命名目录），
        # 显式指定 build_script_folder 让 configure 在 build 目录找到它
        autotools.configure(build_script_folder=src)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        copy(self, "COPYING", src=os.path.join(self.source_folder, "s"),
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["imaevm"]
        self.cpp_info.set_property("pkg_config_name", "imaevm")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["crypto", "m"]
