#!/usr/bin/env python3
"""Conan recipe — cif-api 0.4.2 (Autotools).

CIF (Crystallographic Information File) 2.0 C API and reference
implementation (COMCIFS). Produces libcif (libcif.la → libcif.so).

OHOS adaptation notes:
- Hard dependencies: sqlite3 (AC_MSG_FAILURE if missing) + libm.
  ICU is checked via AX_ICUIO (non-fatal, optional) — ohpcd has no icu
  package, treated as absent.
- Official tarball ships a pre-generated configure (no autoreconf needed).
- OHOS platform identification: patch config.guess/config.sub in place
  (E007/E072) — same pattern as dbustest/telepathy-glib recipes.
- E011: HMDFS/SELinux umask 077 → 000 in configure.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
    copy,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class CifApiConan(ConanFile):
    name = "cif-api"
    version = "0.4.2"
    description = "CIF 2.0 C API and reference implementation"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/COMCIFS/cif_api"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        self.requires("sqlite3/3.53.4", transitive_headers=True, transitive_libs=True)
        # AX_ICUIO 需要 icu-io/icu 的 pkg-config tag（AC_MSG_ERROR 若缺失）——
        # icu4c/77 包内自带 icu-io.pc/icu-uc.pc/icu-i18n.pc
        self.requires("icu4c/77", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _patch_ohos_autotools(self):
        """E007/E072: config.guess/config.sub OHOS 识别（同 dbustest/telepathy-glib）。"""
        for name in ("config.guess", "config.sub"):
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                path = os.path.join(self.source_folder, "build-aux", name)
            if not os.path.isfile(path):
                self.output.warning(f"{name} not found; OHOS patch skipped")
                continue
            with open(path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            orig = text
            if name == "config.guess":
                if "linux-ohos" not in text and "HarmonyOS" not in text:
                    # 旧版（2012）config.guess：各分支自行 echo+exit，UNAME_SYSTEM
                    # =HarmonyOS 匹配不到任何 case 分支（Linux 分支 pattern 不匹配）
                    # → 在 case 语句开头插入 HarmonyOS 分支（skymaker 旧版先例）。
                    marker = 'case "${UNAME_MACHINE}:${UNAME_SYSTEM}:${UNAME_RELEASE}:${UNAME_VERSION}" in'
                    if marker in text:
                        insertion = (
                            "\t*:HarmonyOS:*:*)\n"
                            "\t\techo ${UNAME_MACHINE}-unknown-linux-ohos\n"
                            "\t\texit ;;\n"
                        )
                        text = text.replace(marker, marker + "\n" + insertion)
                    else:
                        # 新式（GUESS= 变量格式）：在 Linux 分支统一输出处前插判断
                        text = text.replace(
                            "echo ${UNAME_MACHINE}-unknown-linux-gnu",
                            "if [ \"${UNAME_SYSTEM}\" = HarmonyOS ]; then "
                            "echo ${UNAME_MACHINE}-unknown-linux-ohos; exit; fi\n"
                            "\techo ${UNAME_MACHINE}-unknown-linux-gnu",
                        )
            elif name == "config.sub":
                if "linux-ohos" not in text:
                    # maybe_os 列表追加 linux-ohos*
                    text = re.sub(
                        r"(\| linux-gnu\*)",
                        r"\1| linux-ohos*",
                        text,
                        count=1,
                    )
                    # os 合法性列表特判：-linux-ohos* 在 -linux* 通用转 linux-gnu 之前
                    text = re.sub(
                        r"(-linux\*)\n(\s*os=`echo \$os \| sed)",
                        r"-linux-ohos*)\n\t\tos=-linux-ohos\n\t\t;;\n\t\1\n\2",
                        text,
                        count=1,
                    )
            if text != orig:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                self.output.info(f"patched {name} for OHOS")

    def generate(self):
        PkgConfigDeps(self).generate()
        self._copy_dep_pc_files()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-static" if self.options.shared else "--enable-static")
        tc.configure_args.append("--enable-shared" if self.options.shared else "--disable-shared")
        # OHOS 无 doxygen，--without-docs 禁用文档安装（否则 make install 的
        # install-html-local 复制不存在的 dox-html 目录失败）
        tc.configure_args.append("--without-docs")
        # configure 用 AC_CHECK_HEADER/AC_SEARCH_LIBS 直接探测 sqlite3（非
        # pkg-config 检查），需把依赖 include/lib 路径显式注入 CFLAGS/LDFLAGS
        for dep_name, dep in self.dependencies.items():
            for p in dep.cpp_info.includedirs:
                flag = "-I" + p
                if flag not in tc.extra_cflags:
                    tc.extra_cflags.append(flag)
            for p in dep.cpp_info.libdirs:
                flag = "-L" + p
                if flag not in tc.extra_ldflags:
                    tc.extra_ldflags.append(flag)
        # ICU 是 C++ 库：icu4c 包为静态 .a，configure 的 AC_CHECK_FUNC 链接
        # 检查（u_fopen_77）需 -lc++ 提供 __gxx_personality_v0/__cxa_begin_catch
        if "-lc++" not in tc.extra_ldflags:
            tc.extra_ldflags.append("-lc++")
        tc.generate()

    def _copy_dep_pc_files(self):
        """Copy dependency .pc files missing from PkgConfigDeps into the
        generators folder.

        icu4c's package_info only declares pkg_config_name "icu-uc", so
        PkgConfigDeps emits icu-uc.pc but not icu-io.pc — yet cif-api's
        AX_ICUIO requires an `icu-io` or `icu` pkg-config tag (AC_MSG_ERROR
        if missing). The .pc files exist inside the icu4c package; copy
        them over so pkg-config lookup succeeds (same pattern as pygobject's
        girepository-2.0.pc / libgudev's libudev.pc).
        """
        for dep_name in ("icu4c", "sqlite3"):
            if dep_name not in self.dependencies:
                continue
            dep = self.dependencies[dep_name]
            pcdir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if not os.path.isdir(pcdir):
                continue
            for name in os.listdir(pcdir):
                if not name.endswith(".pc"):
                    continue
                src = os.path.join(pcdir, name)
                dst = os.path.join(self.generators_folder, name)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    self.output.info(f"Copied {name} to generators folder")

    def build(self):
        apply_conandata_patches(self)
        self._patch_ohos_autotools()
        configure = os.path.join(self.source_folder, "configure")
        # E011: HMDFS/SELinux umask 077 → 000（含 config.status 生成段）
        # AX_ICUIO 的 u_fopen() 真名探测用 `${CPP} ... | sed -n ... q` 管道：
        # sed 匹配 CONF_LINE 后 q 提前退出，clang -E 继续写管道 → SIGPIPE
        # "write on a pipe with no reader" → _ax_icuio_UFOPEN=error → configure 失败。
        # ICU 77 的真实符号名是 u_fopen_77（clang -E 实测），直接硬编码跳过探测。
        # 注意：所有替换必须基于同一份 text 后一次性写回，否则后一次覆盖前一次。
        if os.path.isfile(configure):
            text = open(configure, encoding="utf-8", errors="ignore").read()
            orig = text
            if "umask 077" in text:
                text = text.replace("umask 077", "umask 000")
            old_probe = (
                "_ax_icuio_UFOPEN=`${CPP} ${CPPFLAGS} conftest.c | ${SED} "
                "-n -e '/^\\s*#/d' -e '/^CONF_LINE/,/()/H' "
                "-e '/()/{x;s/\\s*\\S\\+\\s\\+\\(\\w\\+\\).*/\\1/p;q}'` \\\n"
                "    || _ax_icuio_UFOPEN='error'"
            )
            if old_probe in text:
                text = text.replace(
                    old_probe,
                    "_ax_icuio_UFOPEN='u_fopen_77'",
                )
            if text != orig:
                open(configure, "w", encoding="utf-8").write(text)
                self.output.info("patched configure: umask 000 + u_fopen_77 (skip AX_ICUIO pipe probe)")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "cif")
        self.cpp_info.libs = ["cif"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = ["sqlite3::sqlite3", "icu4c::icu4c"]
