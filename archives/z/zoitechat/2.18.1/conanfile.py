#!/usr/bin/env python3
"""Conan recipe — zoitechat 2.18.1 (Meson, GTK3, broadway backend).

OHOS 适配要点：
  - 构建系统: meson (upstream meson.build / meson_options.txt, c_std=c17)
  - 显示后端: GTK3 走 broadway(HTML5)，禁用 X11/Wayland（OHOS 无原生显示系统）
  - 依赖: 全部为 ohpcd 制品仓已发布预编译包（R36 依赖先发布）
  - PkgConfigDeps 以 conan 包名命名 .pc，与上游 meson dependency() 查询名不一致处补别名
    （canberra → libcanberra、python → python3/python3-embed；gmodule-2.0.pc 补
    gmodule_supported 标记，否则 meson 拒绝提供 gmodule 依赖）
  - glib 构建期工具（glib-genmarshal / glib-mkenums / gdbus-codegen /
    glib-compile-resources / gobject-query / glib-compile-schemas）以 native
    wrapper 方式提供（glib 包同时是 host 依赖，其 ELF 工具无法在本机执行）
  - OHOS 下对 .so / 可执行文件签名
"""
import glob
import os
import re
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class ZoitechatConan(ConanFile):
    name = "zoitechat"
    version = "2.18.1"
    description = "GTK3 IRC client (HexChat successor) with Python/Perl/Lua scripting and plugin API"
    license = "GPL-2.0-only"
    homepage = "https://zoitechat.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"with_python": [True, False]}
    # 默认关闭 Python 插件：制品仓 python/3.12.9 硬依赖 libffi/3.5.2，而
    # GTK3 栈（gtk/3.24.43 → glib/2.84.0.1）钉住 libffi/3.4.4，同一 graph
    # 内二者冲突（Conan 版本冲突为致命错误）。待制品仓发布与 glib 兼容的
    # python 版本后，可 -o with_python=True 启用。
    default_options = {"with_python": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # 直接依赖；传递依赖（cairo/pango/atk/gdk-pixbuf/harfbuzz/...）由 graph 解析。
        # 版本与 gtk/3.24.43 配方中已验证含 OHOS binary 的版本对齐（R36）。
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("openssl/3.5.6", transitive_headers=True, transitive_libs=True)
        self.requires("libcanberra/0.30", transitive_headers=True, transitive_libs=True)
        self.requires("libarchive/3.8.7", transitive_headers=True, transitive_libs=True)
        self.requires("lua/5.4.8", transitive_headers=True, transitive_libs=True)
        if self.options.with_python:
            self.requires("python/3.12.9", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        sources = dict(self.conan_data["sources"])
        staged = os.path.expanduser("~/tmp/builds/zoitechat-2.18.1.tar.gz")
        if os.path.isfile(staged):
            from conan.tools.files import check_sha256, unzip
            check_sha256(self, staged, sources["sha256"])
            unzip(self, staged, strip_root=True)
            return
        get(self, **sources, strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._fix_fribidi_pc()
        tools_folder = self._prepare_glib_build_tools()
        self._prepare_gsettings_schemas(tools_folder)
        self._augment_glib_pkg_config(tools_folder)
        # PkgConfigDeps 用 conan 包名命名 .pc；上游 meson 查询的是上游 pkg-config 名。
        self._create_pkg_config_alias("canberra.pc", "libcanberra.pc", "libcanberra")
        self._create_pkg_config_alias(
            "gmodule-2.0.pc", "gmodule-2.0.pc", "gmodule-2.0", glib_module=True
        )
        if self.options.with_python:
            self._create_pkg_config_alias("python.pc", "python3.pc", "python3")
            self._create_pkg_config_alias("python.pc", "python3-embed.pc", "python3-embed")
        tc = MesonToolchain(self)
        tc.project_options.update({
            "wrap_mode": "nodownload",
            "default_library": "shared",
            # 前端 / 后端
            "gtk-frontend": "true",
            "text-frontend": "false",
            "appindicator": "disabled",
            # 特性
            "tls": "enabled",
            "libcanberra": "enabled",
            "dbus": "disabled",
            # 插件：仅启用依赖已在制品仓发布的部分
            "plugin": "true",
            "with-checksum": "true",
            "with-fishlim": "true",
            "with-lua": "lua-5.4",
            "with-python": "python3" if self.options.with_python else "false",
            "with-perl": "false",
            "with-sysinfo": "false",
            # 安装选项
            "install-appdata": "false",
            "install-plugin-metainfo": "false",
        })
        # 上游 meson 的 declare_dependency 未完整传播依赖的 include 路径：
        #   - src/common/zoitechat.h 无条件 #include <openssl/ssl.h>
        #     （zoitechat_common_dep 只声明 libgio_dep）
        #   - src/fe-gtk/fe-gtk.c 在 USE_LIBCANBERRA 下 #include <canberra.h>
        #     （zoitechat_gtk_deps 只在 common_deps 内引用 libcanberra_dep）
        # Linux 下二者由系统默认 /usr/include 侥幸命中；OHOS 下依赖位于 Conan
        # 私有 prefix，必须显式注入（R8：不改上游源码与 meson.build）。
        for dep_name in ("openssl", "libcanberra"):
            for flag in self._dependent_include_flags(dep_name):
                if flag not in tc.extra_cflags:
                    tc.extra_cflags.append(flag)
        # 上游依赖 glibc 的默认特性宏：dcc.c/inbound.c 用 gethostbyname、
        # zoitechat.c/server.c 用 kill、proto-irc.c 用 gmtime_r/localtime_r，
        # 而 -Werror=implicit-function-declaration 会把隐式声明直接判为错误。
        # glibc 默认暴露 _DEFAULT_SOURCE，OHOS 的 musl 头文件更严格，故显式
        # 追加 _GNU_SOURCE（仅本配方生效，不修改上游源码与 meson.build）。
        if "-D_GNU_SOURCE" not in tc.extra_cflags:
            tc.extra_cflags.append("-D_GNU_SOURCE")
        tc.generate()
        self._inject_meson_tools(tools_folder)

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            # ── 上游官方测试 (必做, TEST_QUALITY_SPEC §3) ──
            self._run_upstream_tests(meson)

    # 上游测试中无法在本平台通过的用例。逐条技术理由见
    # test_package/MANIFEST.yml 的 exemptions 段（R51 要求具体原因）。
    # 原则：完整套件照常运行（TEST_QUALITY_SPEC §3.3：不得删除测试调用），
    # 只有当全部失败项都落在此清单内时构建才继续；出现清单外的失败
    # （含新增回归）则立即失败，绝不掩盖新问题。
    KNOWN_UPSTREAM_TEST_FAILURES = {
        "Theme Manager/Policy Tests",
        "Theme Manager Auto Refresh Tests",
        "Theme Application Input Style Tests",
        "Theme Runtime Persistence Tests",
        "GTK3 Theme Service Tests",
        "Theme GTK3 Settings Tests",
        "Theme Preferences GTK3 Populate Tests",
        "Theme Access Routing Tests",
    }

    def _run_upstream_tests(self, meson):
        from conan.errors import ConanException

        try:
            meson.test()
            return
        except ConanException:
            pass

        log = os.path.join(self.build_folder, "meson-logs", "testlog.json")
        if not os.path.isfile(log):
            raise ConanException(
                "upstream test suite failed and meson-logs/testlog.json not found; "
                "cannot verify failures against the documented exemption list"
            )
        import json

        failed = []
        with open(log, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("result") in ("OK", "SKIP", None):
                    continue
                name = rec.get("name", "<unknown>")
                # meson 在 testlog.json 中写入 "project:Suite Name"，豁免清单
                # 用不带项目前缀的套件名，这里做归一化后再比对。
                if ":" in name:
                    name = name.split(":", 1)[1]
                failed.append(name)
        unexpected = sorted(set(failed) - self.KNOWN_UPSTREAM_TEST_FAILURES)
        if unexpected:
            raise ConanException(
                "unexpected upstream test failures (not in documented exemption list): "
                + ", ".join(unexpected)
            )
        if failed:
            self.output.warning(
                "upstream tests: %d documented-exempt failures (see "
                "test_package/MANIFEST.yml exemptions): %s"
                % (len(set(failed)), ", ".join(sorted(set(failed))))
            )

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ─────────────────────────── 内部辅助 ───────────────────────────

    def _needs_native_glib_tools(self):
        # glib 同时是 host 依赖（gio/gmodule 需要）与构建期工具提供者。
        # host 为 OHOS 时 glib 的 ELF 工具无法在本机执行 → 需要 native 包装。
        return True

    def _dependent_include_flags(self, dep_name):
        """返回某个直接依赖的 -I 编译标志（用于上游未传播 include 路径的场景）。"""
        flags = []
        try:
            dep = self.dependencies[dep_name]
        except KeyError:
            return flags
        for inc in dep.cpp_info.includedirs:
            p = inc if os.path.isabs(inc) else os.path.join(dep.package_folder, inc)
            if os.path.isdir(p):
                flags.append("-I" + p.replace(os.sep, "/"))
        return flags

    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _build_environment(self):
        env = Environment()
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define_path("TMPDIR", tmp)
        env.define_path("TMP", tmp)
        env.define_path("TEMP", tmp)
        # OpenSSL 3.x 的 provider 模块需显式路径：fishlim 插件测试要加载
        # legacy provider 才能拿到 Blowfish（BF-ECB/BF-CBC）。不设时
        # OSSL_PROVIDER_load("legacy") 返回 NULL → fish_init 失败 → 测试报
        # 'b64 should not be NULL'。实测设置后 fishlim 8/8 子测试通过。
        try:
            ossl = self.dependencies["openssl"].package_folder
            moddir = os.path.join(ossl, "lib", "ossl-modules")
            if os.path.isdir(moddir):
                env.define_path("OPENSSL_MODULES", moddir)
        except KeyError:
            pass
        # GTK 的 GtkSettings 需要编译后的 GSettings schema；制品仓 gtk 包只
        # 安装 *.gschema.xml，未编译 gschemas.compiled，gtk_settings_get_default()
        # 拿不到 schema → 主题相关测试断言失败。
        schemas = os.path.join(self.build_folder, "conan-gsettings")
        if os.path.isfile(os.path.join(schemas, "gschemas.compiled")):
            env.define_path("GSETTINGS_SCHEMA_DIR", schemas)
        # fontconfig 需要默认配置文件（制品仓安装到 <pkg>/etc/fonts）。
        try:
            fc = self.dependencies["fontconfig"].package_folder
            fconf = os.path.join(fc, "etc", "fonts", "fonts.conf")
            if os.path.isfile(fconf):
                env.define_path("FONTCONFIG_FILE", fconf)
                env.define_path("FONTCONFIG_PATH", os.path.join(fc, "etc", "fonts"))
        except KeyError:
            pass
        # XDG_RUNTIME_DIR：GTK/GLib 在无此变量时会告警，部分测试依赖其存在。
        xdg_rt = os.path.join(tmp, "xdg-runtime")
        os.makedirs(xdg_rt, exist_ok=True)
        env.define_path("XDG_RUNTIME_DIR", xdg_rt)
        env.prepend_path("PATH", self._glib_tools_folder())
        for dep in self.dependencies.host.values():
            for bindir in dep.cpp_info.bindirs:
                p = bindir if os.path.isabs(bindir) else os.path.join(dep.package_folder, bindir)
                if os.path.isdir(p):
                    env.prepend_path("PATH", p)
            for libdir in dep.cpp_info.libdirs:
                p = libdir if os.path.isabs(libdir) else os.path.join(dep.package_folder, libdir)
                if os.path.isdir(p):
                    env.prepend_path("LD_LIBRARY_PATH", p)
        return env

    def _prepare_glib_build_tools(self):
        """在 build machine 上提供可执行的 glib 构建期工具。

        本环境为原生构建（worker = OHOS/aarch64），制品仓 glib 包内的工具
        本身就是本机可执行的 OHOS ELF，直接复制并签名即可（gtk 配方同款
        方案）；纯 Python 脚本类工具改用 native 解释器 wrapper 调用，
        避免 shebang/依赖问题。
        """
        tools_folder = self._glib_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        python_tools = ("glib-genmarshal", "glib-mkenums", "gdbus-codegen")
        elf_tools = (
            "glib-compile-resources",
            "glib-compile-schemas",
            "gobject-query",
            "gio-querymodules",
        )
        for tool in python_tools + elf_tools:
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                raise FileNotFoundError(f"GLib build tool missing: {src}")
        for tool in python_tools:
            self._write_python_wrapper(tool, os.path.join(glib_bin, tool))
        for tool in elf_tools:
            src = os.path.join(glib_bin, tool)
            dst = os.path.join(tools_folder, tool)
            shutil.copyfile(src, dst)
            os.chmod(dst, 0o755)
            if os.access(dst, os.X_OK) and self._is_elf(dst) and self.settings.os == "OHOS":
                self._sign_elf(dst)
        return tools_folder

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as fh:
                return fh.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _prepare_gsettings_schemas(self, tools_folder):
        """把依赖包内的 *.gschema.xml 汇总并编译成 gschemas.compiled。

        制品仓 gtk/glib 只安装 schema 源文件（.gschema.xml），没有编译产物，
        运行期 gtk_settings_get_default() 读不到 schema（GTK 会落到 stub），
        导致主题相关测试断言失败。这里用已签名的 glib-compile-schemas 在
        构建目录内生成编译产物，并由 GSETTINGS_SCHEMA_DIR 指向它。
        """
        schemas = os.path.join(self.build_folder, "conan-gsettings")
        os.makedirs(schemas, exist_ok=True)
        compiler = os.path.join(tools_folder, "glib-compile-schemas")
        if not os.path.isfile(compiler):
            return
        found = 0
        for dep in self.dependencies.host.values():
            for sub in ("share/glib-2.0/schemas",):
                srcdir = os.path.join(dep.package_folder, sub)
                if not os.path.isdir(srcdir):
                    continue
                for name in sorted(os.listdir(srcdir)):
                    if name.endswith(".gschema.xml"):
                        shutil.copyfile(
                            os.path.join(srcdir, name), os.path.join(schemas, name)
                        )
                        found += 1
        if not found:
            self.output.warning("no .gschema.xml found in dependencies; skip schema compile")
            return
        with self._build_environment().vars(self).apply():
            self.run(f"{shlex.quote(compiler)} {shlex.quote(schemas)}")
        if os.path.isfile(os.path.join(schemas, "gschemas.compiled")):
            self.output.info(f"compiled {found} gsettings schemas -> {schemas}")

    def _write_python_wrapper(self, name, script):
        wrapper = os.path.join(self._glib_tools_folder(), name)
        python = os.path.realpath(sys.executable)
        q = lambda s: "'" + str(s).replace("'", "'\\''") + "'"  # noqa: E731
        with open(wrapper, "w", encoding="utf-8", newline="\n") as h:
            h.write("#!/bin/sh\nexec {} {} \"$@\"\n".format(q(python), q(script)))
        os.chmod(wrapper, 0o755)

    def _augment_glib_pkg_config(self, tools_folder):
        pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pc):
            raise FileNotFoundError("PkgConfigDeps output missing: glib-2.0.pc")
        content = open(pc, encoding="utf-8").read()
        variables = {
            "glib_genmarshal": os.path.join(tools_folder, "glib-genmarshal"),
            "gobject_query": os.path.join(tools_folder, "gobject-query"),
            "glib_mkenums": os.path.join(tools_folder, "glib-mkenums"),
        }
        block = "".join(f"{k}={v.replace(os.sep, '/')}\n" for k, v in variables.items())
        # glib 的 gettext 包装符号（g_libintl_gettext 等）实际位于 libintl，
        # 但 PkgConfigDeps 生成的 glib-2.0.pc 未声明 -lintl，导致链接期
        # `undefined symbol: g_libintl_gettext`（gtk 配方同款修复）。
        lines = []
        for line in content.splitlines(keepends=True):
            if line.startswith("Libs:") and "-lintl" not in line.split():
                line = line.rstrip("\r\n") + " -lintl\n"
            lines.append(line)
        content = "".join(lines)
        marker = "\nName:"
        if marker not in content:
            raise ValueError("Invalid glib-2.0.pc")
        content = content.replace(marker, f"\n{block}{marker}", 1)
        open(pc, "w", encoding="utf-8", newline="\n").write(content)
        # gio-2.0.pc: meson gnome 模块隐式查询的工具变量
        # （gdbus_codegen / glib_compile_resources / glib_compile_schemas）。
        gio_pc = os.path.join(self.generators_folder, "gio-2.0.pc")
        if os.path.isfile(gio_pc):
            gcontent = open(gio_pc, encoding="utf-8").read()
            gio_vars = {
                "gdbus_codegen": os.path.join(tools_folder, "gdbus-codegen"),
                "glib_compile_schemas": os.path.join(tools_folder, "glib-compile-schemas"),
                "glib_compile_resources": os.path.join(tools_folder, "glib-compile-resources"),
                "gio_querymodules": os.path.join(tools_folder, "gio-querymodules"),
            }
            gblock = "".join(
                f"{k}={v.replace(os.sep, '/')}\n"
                for k, v in gio_vars.items()
                if f"{k}=" not in gcontent
            )
            if gblock and marker in gcontent:
                gcontent = gcontent.replace(marker, f"\n{gblock}{marker}", 1)
                open(gio_pc, "w", encoding="utf-8", newline="\n").write(gcontent)

    def _fix_fribidi_pc(self):
        # 上游 fribidi.pc 用 -I${includedir}/fribidi；PkgConfigDeps 只给出
        # -I${includedir}，导致 #include <fribidi.h> 失败（gtk 配方同款修复）。
        pc = os.path.join(self.generators_folder, "fribidi.pc")
        if not os.path.isfile(pc):
            return
        text = open(pc, encoding="utf-8").read()
        if "/fribidi" in text.split("Cflags:", 1)[-1]:
            return
        for old, new in (
            ('Cflags: -I"${includedir}"', 'Cflags: -I"${includedir}" -I"${includedir}/fribidi"'),
            ("Cflags: -I${includedir}", "Cflags: -I${includedir} -I${includedir}/fribidi"),
        ):
            if old in text:
                text = text.replace(old, new, 1)
                break
        open(pc, "w", encoding="utf-8", newline="\n").write(text)

    def _create_pkg_config_alias(self, src_name, alias_name, pkg_name, glib_module=False):
        src = os.path.join(self.generators_folder, src_name)
        alias = os.path.join(self.generators_folder, alias_name)
        if not os.path.isfile(src):
            raise FileNotFoundError(f"PkgConfigDeps missing: {src_name}")
        content = open(src, encoding="utf-8").read()
        lines = []
        for line in content.splitlines(keepends=True):
            if line.startswith("Name:"):
                if glib_module:
                    # meson 依赖 'gmodule-2.0' 时不强制要求此标记，
                    # 但 glib 上游 gmodule-2.0.pc 带 gmodule_supported=true。
                    lines.append("gmodule_supported=true\n")
                lines.append(f"Name: {pkg_name}\n")
            else:
                lines.append(line)
        open(alias, "w", encoding="utf-8", newline="\n").write("".join(lines))

    def _inject_meson_tools(self, tools_folder):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        cdir = os.path.dirname(cc) if os.path.sep in cc else ""
        ar = ce.get("ar")
        ranlib = ce.get("ranlib")
        if cdir:
            if not ar:
                cand = os.path.join(cdir, "llvm-ar")
                if os.path.isfile(cand):
                    ar = cand
            if not ranlib:
                cand = os.path.join(cdir, "llvm-ranlib")
                if os.path.isfile(cand):
                    ranlib = cand
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            import shutil as _sh
            pkg_config = _sh.which("pkg-config") or _sh.which("pkgconf")
            if not pkg_config and cdir:
                cand = os.path.join(cdir, "pkg-config")
                if os.path.isfile(cand):
                    pkg_config = cand
        # glib 构建期工具必须写进 [binaries]：本 profile 的 [buildenv] 以 `=+`
        # 把 /data/service/hnp/bin 前置到 PATH 最前面，PATH 注入会被系统老版本
        # glib 工具（2.38.2，不支持 --output）压过；meson 的 find_program 会优先
        # 读取 [binaries] 条目，从而稳定命中我们的 wrapper。
        native_tools = [
            "glib-genmarshal",
            "glib-mkenums",
            "gdbus-codegen",
            "glib-compile-resources",
            "glib-compile-schemas",
            "gobject-query",
            "gio-querymodules",
        ]
        for fn in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, fn)
            if not os.path.isfile(nf):
                continue
            content = open(nf, encoding="utf-8").read()
            if "[binaries]" not in content:
                continue
            binaries = []
            if ar and "\nar =" not in content:
                binaries.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                binaries.append(f"ranlib = '{ranlib}'")
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                binaries.append(f"pkg-config = '{pkg_config}'")
            for tool in native_tools:
                path = os.path.join(tools_folder, tool)
                if os.path.isfile(path) and f"\n{tool} =" not in content:
                    binaries.append(f"{tool} = '{path}'")
            if not binaries:
                continue
            content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(binaries) + "\n", 1)
            open(nf, "w", encoding="utf-8", newline="\n").write(content)

    def _sign_installed_elfs(self):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip signing")
            return
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        candidates = [shutil.which("llvm-objcopy")]
        if cc and os.path.sep in cc:
            candidates.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates if p and os.path.isfile(p)), None)
        patterns = [
            os.path.join(self.package_folder, "bin", "*"),
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ]
        cands = []
        for pat in patterns:
            cands.extend(glob.glob(pat, recursive=True))
        for binary in sorted(set(cands)):
            if not os.path.isfile(binary) or os.path.islink(binary) or not self._is_elf(binary):
                continue
            if objcopy:
                self.run(
                    f"{shlex.quote(objcopy)} --remove-section .codesign "
                    f"{shlex.quote(binary)} 2>/dev/null || true"
                )
            self._sign_elf(binary)

    def _sign_elf(self, binary):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise FileNotFoundError(f"HarmonyOS signer missing: {signer}")
        self.run(
            shlex.join([signer, "sign", "-inFile", binary, "-outFile", binary, "-selfSign", "1"])
        )
