#!/usr/bin/env python3
"""Conan recipe for gtkspell3 3.0.10-r3 (HarmonyOS PC / OHOS).

Spell checking addon for GTK3's TextView widget, based on Enchant-2.
Build: autotools (configure + make). Depends on glib/gtk3/enchant-2.

OHOS adaptation notes:
- config.guess/config.sub patched (E007) to emit aarch64-unknown-linux-ohos.
- configure patched: skip intltool XML::Parser check (XS module cannot load on
  HMDFS) and fix HMDFS ac_pwd/umask temp-dir issues.
- NLS disabled (--disable-nls) to avoid intltool runtime dependency.
- glib-2.0.pc is augmented with -lintl: gtkspell source calls dgettext()
  unconditionally, and glib headers redirect it to g_libintl_dgettext which is
  provided by libintl (same approach as the gtk/3.24.43 recipe).
- SDK linker runtime: the active OHOS SDK's lld needs libxml2.so.16 from
  <sdk>/llvm/lib; CI shells prepend ~/usr/local/lib which can shadow the
  ABI-matched libxml2 and prevent lld from starting (abseil/20260526 pattern).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class Gtkspell3Conan(ConanFile):
    name = "gtkspell3"
    version = "3.0.10-r3"
    description = "Spell checking addon for GTK3's TextView widget (Enchant-2 based)"
    license = "GPL-2.0-or-later"
    homepage = "https://gtkspell.sourceforge.net/"
    # upstream repo（waterlan 官网已下线，GitCode 镜像仓库地址）
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # 与 GTK 依赖栈一致（gtk/3.24.43、enchant/2.8.2 均为 shared=True）：
    # gtkspell 源码无条件调用 dgettext（glib 头文件重定向为 g_libintl_dgettext），
    # shared 构建可在链接期以 -lintl 解析并将 libintl 写入 DT_NEEDED，
    # 静态库会把这个未定义符号泄漏给消费者导致链接失败。
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("enchant/2.8.2", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps: exposes glib-2.0 / gtk+-3.0 / enchant-2 for configure
        PkgConfigDeps(self).generate()
        self._augment_all_pc_intl()
        # 确保 gettext (含 libintl.so.8) + intltool 已安装——必须在
        # _system_gettext_libdir() 调用前完成，否则 LD_LIBRARY_PATH 不含
        # libintl 目录，configure 的 intltool 检查会因 msgmerge 找不到
        # libintl 而报错。intltool 脚本由独立包提供，需单独安装。
        _gtkspell_prefix = os.path.expanduser("~/usr/local")
        self._install_cmd_pkg("gettext", "0.22.5", _gtkspell_prefix,
                              marker="libintl.so.8")
        self._install_cmd_pkg("intltool", "0.51.0", _gtkspell_prefix,
                              marker="bin/intltool-update")
        # 固化构建环境注入（写入 conanbuild.sh，configure/make 运行时必然加载）：
        # 1) 系统 gettext libintl 需在 conan 依赖库之前（避免 glib proxy-libintl
        #    遮蔽 libintl_gettext 符号导致 msgmerge 无法启动）
        # 2) SDK llvm/lib 需在 ~/usr/local/lib 之前（避免遮蔽 ABI 匹配的
        #    libxml2.so.16 导致 lld 无法启动）
        gettext_lib = self._system_gettext_libdir()
        if gettext_lib:
            self.output.info("Prepending system gettext lib path: {}".format(gettext_lib))
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", gettext_lib)
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            self.output.info("Prepending OHOS SDK linker runtime path: {}".format(sdk_llvm_lib))
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        tc = AutotoolsToolchain(self)
        # R26: static by default for system-name library safety (not a system
        # library, but keep template default: shared option controls it)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # NLS off: intltool requires XML::Parser (XS) which cannot load on HMDFS
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-gtk-doc")
        # cmd-pkgs 的 gtk/glib/cairo-gobject 等 .so 包含未解析的传递依赖
        # 符号（g_libintl_*/ffi_type_*/pcre2_*），--no-allow-shlib-undefined
        # 会拦截。链接时注入 --allow-shlib-undefined 允许这些符号在运行时
        # 由动态链接器解析（qalculate-gtk 同款处理方式）。
        tc.extra_ldflags.append("-Wl,--allow-shlib-undefined")
        tc.generate()

    def _augment_all_pc_intl(self):
        """所有用到 proxy-libintl (g_libintl_*) 的 .pc 文件补 -lintl。

        gtk/glib/cairo-gobject/gdk-pixbuf/atk 等 conan 依赖包均使用
        proxy-libintl 符号，链接期需要 libintl 提供实现。仅给 glib-2.0.pc
        加 -lintl 不够——其他 .pc 的 Libs 也会引入 g_libintl_* 引用。"""
        _pc_dir = self.generators_folder
        for name in ("glib-2.0.pc", "gtk+-3.0.pc", "gdk-3.0.pc",
                      "gdk-pixbuf-2.0.pc", "atk.pc",
                      "cairo-gobject.pc", "cairo.pc"):
            pc = os.path.join(_pc_dir, name)
            if not os.path.isfile(pc):
                continue
            content = open(pc, encoding="utf-8").read()
            lines = []
            for line in content.splitlines(keepends=True):
                if line.startswith("Libs:") and "-lintl" not in line:
                    line = line.rstrip("\r\n") + " -lintl\n"
                lines.append(line)
            new_content = "".join(lines)
            if new_content != content:
                open(pc, "w", encoding="utf-8", newline="\n").write(new_content)
                self.output.info(f"{name}: appended -lintl")

    def _sdk_llvm_libdir(self):
        """Locate the active OHOS SDK llvm/lib that ships libxml2.so.16.

        The SDK's lld links against libxml2.so.16 at runtime; CI shells prepend
        ~/usr/local/lib which can shadow the ABI-matched SDK copy, so lld fails
        to start and configure reports "C compiler cannot create executables".
        Same probe strategy as abseil/20260526.
        """
        if str(self.settings.os) != "OHOS":
            return ""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or compilers.get("c")
        candidates = []
        if cxx:
            try:
                resource_dir = subprocess.check_output(
                    [cxx, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
            except (OSError, subprocess.CalledProcessError):
                pass
            compiler = os.path.realpath(cxx)
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )
        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    def _system_gettext_libdir(self):
        """Locate system gettext lib dir shipping a full libintl.so.8.

        configure 的 intltool 检查会执行 msgmerge（gettext 工具），其运行期
        依赖 libintl.so.8。conan 依赖图里 glib 的 proxy-libintl（仅有
        g_libintl_* 符号）可能被注入 LD_LIBRARY_PATH 并遮蔽系统 gettext 的
        libintl（libintl_gettext 等符号），导致 msgmerge 无法启动 →
        'GNU gettext tools not found; required for intltool'。
        本方法定位含完整 libintl_* 符号的系统 libintl 目录。
        """
        if str(self.settings.os) != "OHOS":
            return ""
        msgmerge = shutil.which("msgmerge")
        if not msgmerge:
            return ""
        # msgmerge 位于 <prefix>/bin，libintl 位于 <prefix>/lib
        prefix = os.path.dirname(os.path.dirname(os.path.realpath(msgmerge)))
        candidates = [
            os.path.join(prefix, "lib"),
            os.path.join(prefix, "lib64"),
        ]
        for cand in dict.fromkeys(candidates):
            lib = os.path.join(cand, "libintl.so.8")
            if os.path.isfile(lib):
                return cand
        return ""

    def _build_environment(self):
        environment = Environment()
        # 系统 gettext libintl 需在 conan 依赖库之前（避免 proxy-libintl 遮蔽）
        gettext_lib = self._system_gettext_libdir()
        if gettext_lib:
            self.output.info("Prepending system gettext lib path: {}".format(gettext_lib))
            environment.prepend_path("LD_LIBRARY_PATH", gettext_lib)
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            self.output.info("Prepending OHOS SDK linker runtime path: {}".format(sdk_llvm_lib))
            environment.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        return environment

    def _install_cmd_pkg(self, name, version, prefix, marker=None):
        """从 cmd-pkgs 下载预编译包并解压到 prefix（qalculate-gtk 同款）。
        marker: 已安装标记文件（如 lib/libintl.so.8），存在则跳过。"""
        if marker and os.path.isfile(os.path.join(prefix, "lib", marker)):
            self.output.info(f"{name} already installed")
            return
        import tarfile
        import urllib.request
        from io import BytesIO
        fname = f"{name}-{version}-ohos-aarch64.tar.gz"
        url = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
               f"download/pkgs/{fname}")
        for attempt in (1, 2, 3):
            self.output.info(f"Installing {name} {version} from cmd-pkgs (try {attempt})")
            try:
                with urllib.request.urlopen(url, timeout=600) as resp:
                    data = resp.read()
                if not (data[:2] == b"\x1f\x8b" and data):
                    self.output.warning(f"  {name} not gzip, retry")
                    continue
                with tarfile.open(fileobj=BytesIO(data), mode="r:gz") as tf:
                    os.makedirs(prefix, exist_ok=True)
                    tf.extractall(prefix)
                self.output.info(f"  Installed {name} {version} from cmd-pkgs")
                return
            except Exception as exc:
                self.output.warning(f"  {name} download failed: {exc}, retry")
        self.output.warning(f"  {name} {version} download failed after 3 tries")

    def build(self):
        apply_conandata_patches(self)
        # 确保 gettext (含 libintl.so.8) 已安装，否则 configure 的 intltool
        # 检查会因 msgmerge 找不到 libintl 而报 "GNU gettext tools not found"
        _gtkspell_prefix = os.path.expanduser("~/usr/local")
        self._install_cmd_pkg("gettext", "0.22.5", _gtkspell_prefix,
                              marker="libintl.so.8")
        envvars = self._build_environment().vars(self)
        with envvars.apply():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # strip .la files (upstream install keeps them; not needed)
        for root, _, files in os.walk(os.path.join(self.package_folder, "lib")):
            for f in files:
                if f.endswith(".la"):
                    os.unlink(os.path.join(root, f))

    def package_info(self):
        # Upstream lib name: libgtkspell3-3.so / .a
        self.cpp_info.libs = ["gtkspell3-3"]
        self.cpp_info.includedirs = ["include/gtkspell-3.0"]
        self.cpp_info.set_property("pkg_config_name", "gtkspell3-3.0")
        # 依赖传递由 requirements() 的 transitive_headers/libs=True 处理
        # （gtk/enchant 均为无组件扁平配方，不可用 cpp_info.requires 引用）
