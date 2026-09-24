#!/usr/bin/env python3
"""Conan recipe for xsane 0.999.

Upstream is a legacy Autotools frontend for SANE scanners.  The recipe keeps
the optional image-format probes off to reduce the dependency surface, stages
missing Autotools helper scripts from autotools-dev, and lets the historical
GTK+ 2 pkg-config probe resolve against the repo's native gtk2/2.24.33 package
(pkg_config_name "gtk+-2.0"), which provides the GtkObject/GdkGC-era APIs
xsane's sources actually use.

The source URL and SHA256 are kept in this recipe (no conandata.yml) so the
package never enters the CI pre-download branch and cannot be hit by its
conandata.yml rewriting logic.
"""
import glob
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import copy, get, save
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XsaneConan(ConanFile):
    name = "xsane"
    version = "0.999"
    description = "Graphical frontend for SANE scanners"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.com/sane-project/frontend/xsane"
    url = "https://gitlab.com/sane-project/frontend/xsane"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    _source_url = "https://gitlab.com/sane-project/frontend/xsane/-/archive/0.999/xsane-0.999.tar.gz"
    _source_sha256 = "05359707effe1547ff123bb34443a95a4c54bd4888b91a3556c69875b64989b6"

    def build_requirements(self):
        self.tool_requires("autotools-dev/20240727.1-nmu1")
        self.tool_requires("pkgconf/3.0.5")

    def requirements(self):
        self.requires("sane-backends/1.2.1")
        self.requires("gtk2/2.24.33")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            url=self._source_url,
            sha256=self._source_sha256,
            strip_root=True,
        )

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-sanetest",
            "--disable-gtktest",
            "--disable-nls",
            "--disable-gimp",
            "--disable-jpeg",
            "--disable-png",
            "--disable-tiff",
            "--disable-lcms",
        ])
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-linux-gnu",
                "--host=aarch64-linux-ohos",
            ])
        tc.generate()

    def build(self):
        self._stage_autotools_aux_files()
        self._make_configure_executable()
        self._patch_configure_tmpdir()
        self._write_ohos_mktemp_wrapper()

        with self._build_environment().vars(self).apply():
            autotools = Autotools(self)
            if str(self.settings.os) == "OHOS":
                self._configure_for_ohos(autotools)
                self._patch_mkinstalldirs()
                stub_a = self._build_intl_stub()
                self._append_intl_stub_to_libs(stub_a)
                # 不在命令行覆盖 LDFLAGS:依赖库的 -L 路径在环境变量里,
                # 覆盖会导致 -lsane/-lcurl 等找不到。桩库经 LIBS 行尾注入,
                # 链接行中 LIBS 位于目标文件之后,静态库符号才会被拉入。
                self.run("umask 000 && make -j1", cwd=self.source_folder)
            else:
                autotools.configure()
                autotools.make(args=["-j1"])

    def package(self):
        with self._build_environment().vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self.run(
                    f"umask 000 && make install DESTDIR={shlex.quote(self.package_folder)}",
                    cwd=self.source_folder,
                )
            else:
                Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    def _stage_autotools_aux_files(self):
        misc = os.path.join(self.dependencies.build["autotools-dev"].package_folder, "share", "misc")
        copy(self, "config.guess", src=misc, dst=self.source_folder)
        copy(self, "config.sub", src=misc, dst=self.source_folder)

    def _make_configure_executable(self):
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            os.chmod(configure, 0o755)

    def _patch_configure_tmpdir(self):
        # 与 gtk2 配方同款修复:HMDFS 对 mktemp -d(umask 077 -> 0700,组/
        # 其他位全零)目录拒绝写入且静默忽略 chmod;autoconf 2.71 还把临时
        # 目录硬编码在 cwd。改写 configure 使其落在 ${TMPDIR:-.} 且不用 077,
        # 生成的 config.status 继承同一补丁(其内嵌的 tmpdir 逻辑同样改写)。
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, encoding="utf-8", errors="replace") as h:
            content = h.read()
        replaced = [
            ('tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
             'tmp=`(umask 000 && mktemp -d "${TMPDIR:-.}/confXXXXXX") 2>/dev/null` && { chmod 777 "$tmp" 2>/dev/null || true; } &&'),
            ("tmp=./conf$$-$RANDOM",
             "tmp=${TMPDIR:-.}/conf$$-$RANDOM"),
        ]
        optional = [
            ("(umask 077 && mkdir \"$tmp\")",
             "(umask 000 && mkdir \"$tmp\")"),
        ]
        changed = False
        for old, new in replaced:
            if new in content:
                continue
            if old not in content:
                raise ConanException(f"configure tmpdir pattern not found: {old[:50]}")
            content = content.replace(old, new, 1)
            changed = True
        for old, new in optional:
            if old in content and new not in content:
                content = content.replace(old, new, 1)
                changed = True
        if changed:
            with open(configure, "w", encoding="utf-8", newline="\n") as h:
                h.write(content)
            self.output.info("patched configure tmpdir to ${TMPDIR:-.} umask-000")

    def _build_environment(self):
        env = Environment()
        pkgconf_bin = os.path.join(self.dependencies.build["pkgconf"].package_folder, "bin")
        sane_pkg = self.dependencies["sane-backends"].package_folder
        gtk2_pkg = self.dependencies["gtk2"].package_folder
        if str(self.settings.os) == "OHOS":
            env.prepend_path("PATH", self._ohos_wrapper_dir())
        env.prepend_path("PATH", pkgconf_bin)
        env.prepend_path("PATH", os.path.join(gtk2_pkg, "bin"))
        env.prepend_path("PATH", os.path.join(sane_pkg, "bin"))
        env.prepend_path("PATH", os.path.join(sane_pkg, "sbin"))
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        env.define("PKG_CONFIG", os.path.join(pkgconf_bin, "pkgconf"))
        if str(self.settings.os) == "OHOS":
            env.define("CONFIG_SHELL", "/system/bin/sh")
            env.define("SHELL", "/system/bin/sh")
            env.define("SANE_CONFIG", f"/system/bin/sh {os.path.join(sane_pkg, 'bin', 'sane-config')}")
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler_executables = dict(compiler_executables or {})
        if str(self.settings.os) == "OHOS":
            compiler_executables.setdefault("c", "/data/service/hnp/bin/clang")
            compiler_executables.setdefault("cpp", "/data/service/hnp/bin/clang++")
        if compiler_executables.get("c"):
            env.define("CC", compiler_executables["c"])
        if compiler_executables.get("cpp"):
            env.define("CXX", compiler_executables["cpp"])
        self._define_ohos_binary_tools(env, compiler_executables)
        tmpdir = os.path.join(self.source_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        return env

    def _ohos_wrapper_dir(self):
        return os.path.join(self.source_folder, ".conan-ohos-bin")

    def _write_ohos_mktemp_wrapper(self):
        if str(self.settings.os) != "OHOS":
            return

        wrapper_dir = self._ohos_wrapper_dir()
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper = os.path.join(wrapper_dir, "mktemp")
        save(
            self,
            wrapper,
            "\n".join([
                "#!/system/bin/sh",
                'out=$(/system/bin/mktemp "$@" 2>/dev/null || /data/service/hnp/bin/mktemp "$@") || exit 1',
                "# HMDFS denies writes into mktemp dirs whose group/other bits are",
                "# all zero (mktemp -d -> 0700) and silently ignores chmod there;",
                "# recreate via mkdir at the same path so the mode bits are",
                "# inherited (umask 000 builds -> writable).",
                'if [ -d "$out" ]; then rmdir "$out" 2>/dev/null && mkdir "$out" 2>/dev/null; fi',
                'chmod 0755 "$out" 2>/dev/null || true',
                'echo "$out"',
                "",
            ]),
        )
        os.chmod(wrapper, 0o755)

    def _define_ohos_binary_tools(self, env, compiler_executables):
        if str(self.settings.os) != "OHOS":
            return

        compiler = compiler_executables.get("c")
        tool_dir = os.path.dirname(compiler) if compiler else "/data/service/hnp/bin"
        for env_name, tool_name in {
            "AR": "llvm-ar",
            "NM": "llvm-nm",
            "RANLIB": "llvm-ranlib",
            "STRIP": "llvm-strip",
        }.items():
            candidate = os.path.join(tool_dir, tool_name)
            if os.path.isfile(candidate):
                env.define(env_name, candidate)

    def _build_intl_stub(self):
        # OHOS 无 libintl,且 xsane 源码在 --disable-nls 下仍直接引用
        # bind_textdomain_codeset(ld.lld: undefined symbol)。提供直通桩
        # (不做翻译,构建验证足够),经 LDFLAGS 注入最终链接。
        stub_c = os.path.join(self.build_folder, "intl-stub.c")
        stub_o = os.path.join(self.build_folder, "intl-stub.o")
        stub_a = os.path.join(self.build_folder, "libintl-stub.a")
        save(self, stub_c, "\n".join([
            "char *gettext(const char *m) { return (char *)m; }",
            "char *dgettext(const char *d, const char *m) { return (char *)m; }",
            "char *dcgettext(const char *d, const char *m, int c) { return (char *)m; }",
            "char *textdomain(const char *d) { return (char *)d; }",
            "char *bindtextdomain(const char *d, const char *dir) { return (char *)dir; }",
            "char *bind_textdomain_codeset(const char *d, const char *c) { return (char *)c; }",
        ]))
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c") or "clang"
        self.run(f'"{cc}" -fPIC -c "{stub_c}" -o "{stub_o}"')
        ar = os.path.join(os.path.dirname(cc) if cc and os.path.sep in cc else "", "llvm-ar")
        if not os.path.isfile(ar):
            ar = "llvm-ar"
        self.run(f'"{ar}" rcs "{stub_a}" "{stub_o}"')
        return stub_a

    def _patch_mkinstalldirs(self):
        # OHOS 按文件签名强制脚本执行:mkinstalldirs 的 #!/bin/sh shebang
        # 直接执行会 EACCES(gtk2 的老 Makefile 经 $(SHELL) 调用所以没事,
        # xsane 的自制 Makefile 直接执行)。改写为显式经 /system/bin/sh 调用。
        for mk in glob.glob(os.path.join(self.source_folder, "Makefile")) + \
                  glob.glob(os.path.join(self.source_folder, "*", "Makefile")):
            with open(mk, encoding="utf-8", errors="replace") as h:
                text = h.read()
            new, n = re.subn(
                r"(?m)^((?:MKDIR|MKINSTALLDIRS|mkinstalldirs)\s*=\s*)(.+mkinstalldirs.*)$",
                r"\1/system/bin/sh \2",
                text,
            )
            if n and new != text:
                with open(mk, "w", encoding="utf-8", newline="\n") as h:
                    h.write(new)
                self.output.info(f"patched mkinstalldirs via /system/bin/sh: {os.path.basename(os.path.dirname(mk)) or '.'}")

    def _append_intl_stub_to_libs(self, stub_a):
        mk = os.path.join(self.source_folder, "src", "Makefile")
        with open(mk, encoding="utf-8", errors="replace") as h:
            text = h.read()
        if stub_a in text:
            return
        new, n = re.subn(r"(?m)^(LIBS\s*=.*)$", r"\1 " + stub_a, text, count=1)
        if n != 1:
            raise ConanException("src/Makefile LIBS line not found for intl stub")
        with open(mk, "w", encoding="utf-8", newline="\n") as h:
            h.write(new)

    def _configure_for_ohos(self, autotools):
        shell = "/system/bin/sh"
        configure = os.path.join(self.source_folder, "configure")
        configure_args = autotools._configure_args or ""
        self.run(
            f"umask 000 && {shlex.quote(shell)} {shlex.quote(configure)} {configure_args}",
            cwd=self.source_folder,
        )

