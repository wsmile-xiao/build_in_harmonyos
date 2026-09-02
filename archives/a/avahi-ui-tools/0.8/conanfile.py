#!/usr/bin/env python3
"""Conan recipe for avahi-ui-tools 0.8 (application package).

Builds the upstream avahi source tree's avahi-ui/ subdirectory, which
emits bin_PROGRAMS=bssh (the SSH/VNC service browser) together with the
in-tree avahi-common, avahi-client and avahi-glib libraries it links
against.  Only these four subdirectories are built; the daemon, core,
utilities, and unrelated bindings are excluded.  The bssh binary is
packaged as bssh with bvnc/bshell symlink aliases; no libraries are
published (package_type=application).

The GitHub tag archive has no generated configure script, so the recipe runs
autogen.sh with Conan-provided automake, libtool, and gettext tools. D-Bus,
glib-2.0, and gtk+-3.0 pkg-config metadata comes from Conan dependencies.
"""
import json
import os
import re
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class AvahiUiToolsConan(ConanFile):
    required_conan_version = ">=2.28"
    name = "avahi-ui-tools"
    version = "0.8"
    description = ("Avahi SSH/VNC service browser front-ends: bssh with "
                   "bvnc/bshell aliases (GTK3)")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/avahi/avahi"
    url = "https://github.com/avahi/avahi"
    package_type = "application"

    # bin_PROGRAMS of avahi-ui/Makefile.am plus the aliases created by its
    # install-exec-local rule (bssh → bvnc/bshell).
    _PROGRAMS = ("bssh",)
    _ALIASES = {
        "bssh": ("bvnc", "bshell"),
    }

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "glib/2.84.0.1",
            transitive_headers=True,
            transitive_libs=True)
        # libavahi-ui-gtk3 links avahi-client, which talks to the daemon over
        # D-Bus, and renders its service dialog with GTK+ 3.  Headers and libs
        # are propagated transitively so consumers (and the test package) can
        # include <gtk/gtk.h> without declaring gtk themselves.
        self.requires("dbus/1.14.10")
        self.requires(
            "gtk/3.24.43",
            transitive_headers=True,
            transitive_libs=True)
        # Pin the repository's OHOS-native expat revision instead of the
        # conancenter recipe selected through dbus' transitive requirement.
        self.requires("expat/2.8.2.1", override=True)

    def build_requirements(self):
        # The GitHub tag archive has no generated configure; autogen.sh needs
        # gettextize (gettext), libtoolize (libtool), aclocal/automake.
        # autoconf and m4 are provided by the SDK (/data/service/hnp/bin).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("gettext/0.22.5.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        PkgConfigDeps(self).generate()
        # configure.ac runs PKG_CHECK_MODULES(DBUS, [dbus-1 >= 0.34]); the
        # dbus Conan package does not install a dbus-1.pc itself, so generate
        # a pkg-config shim pointing at the package folders.
        dbus = self.dependencies["dbus"]
        pc_dir = os.path.join(self.build_folder, "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        pc = os.path.join(pc_dir, "dbus-1.pc")
        with open(pc, "w", encoding="utf-8") as handle:
            handle.write(f"prefix={dbus.package_folder}\n")
            handle.write("exec_prefix=${prefix}\n")
            handle.write("libdir=${prefix}/lib\n")
            handle.write("includedir=${prefix}/include\n")
            handle.write("Name: dbus\n")
            handle.write("Description: D-Bus message bus\n")
            handle.write("Version: 1.14.10\n")
            handle.write("Libs: -L${libdir} -ldbus-1\n")
            handle.write("Cflags: -I${includedir}/dbus-1.0 -I${includedir}\n")
        env = Environment()
        if str(self.settings.os) == "OHOS":
            # Some CI workers have a static GLib below /usr/local. Libtool can
            # resolve plain -lglib-2.0 to that archive even though Conan's
            # pkg-config file puts its shared library directory first, mixing
            # the Conan headers with a different GLib binary. Pin the shared
            # objects by absolute path so the worker-global search path cannot
            # affect the Avahi libraries or their upstream test executable.
            glib = self.dependencies["glib"]
            glib_libdir = os.path.join(glib.package_folder, "lib")
            glib_so = os.path.join(glib_libdir, "libglib-2.0.so")
            gobject_so = os.path.join(glib_libdir, "libgobject-2.0.so")
            intl_so = os.path.join(glib_libdir, "libintl.so")
            required = (glib_so, gobject_so, intl_so)
            missing = [path for path in required if not os.path.isfile(path)]
            if missing:
                raise ConanException(
                    "glib package lacks required OHOS shared objects: "
                    + ", ".join(missing))
            include_dirs = (
                os.path.join(glib.package_folder, "include"),
                os.path.join(glib.package_folder, "include", "glib-2.0"),
                os.path.join(glib.package_folder, "lib", "glib-2.0", "include"),
            )
            cflags = " ".join(f"-I{json.dumps(path)}" for path in include_dirs)
            system_libs = " -lm -lpthread -ldl"
            env.define("GLIB20_CFLAGS", cflags)
            env.define(
                "GLIB20_LIBS",
                f"{json.dumps(glib_so)} {json.dumps(intl_so)}{system_libs}")
            env.define("GOBJECT_CFLAGS", cflags)
            env.define(
                "GOBJECT_LIBS",
                f"{json.dumps(gobject_so)} {json.dumps(glib_so)} "
                f"{json.dumps(intl_so)}{system_libs}")
            # bssh 用 GTK30_LIBS 链接（来自 gtk+-3.0.pc 的依赖闭包）；CI worker
            # /usr/local/lib 下可能预装全局 libcairo-gobject.so，其引用
            # g_libintl_* 符号（E508/E107）。追加 conan glib 的 libintl.so
            # 绝对路径到 LIBS，保证链接时 g_libintl_* 有定义（本地 conan-verify
            # 因无全局 cairo 干扰不触发，CI 上必需）。
            env.append("LIBS", intl_so)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}) or {}
        for variable, key in (("CC", "c"), ("CXX", "cpp")):
            compiler = compilers.get(key)
            if not compiler:
                raise ConanException(
                    f"{variable} missing from tools.build:compiler_executables")
            env.define(variable, compiler)
        automake_tools = self._stage_automake_tools()
        env.prepend_path("PATH", automake_tools)
        env.define("ACLOCAL", os.path.join(automake_tools, "aclocal"))
        env.define("AUTOMAKE", os.path.join(automake_tools, "automake"))
        bootstrap_tools = self._stage_bootstrap_tools()
        env.prepend_path("PATH", bootstrap_tools)
        env.define("GETTEXTIZE", os.path.join(bootstrap_tools, "gettextize"))
        env.define("LIBTOOLIZE", os.path.join(bootstrap_tools, "libtoolize"))
        # The libtool tool package exports a non-standard relocation root.
        # Keep the concrete paths patched into our staged script instead.
        env.define("_lt_pkgdatadir", "")
        # avahi-gobject invokes these tools by their literal command names.
        # The GLib package installs them as Python scripts, whose shebang
        # execution is rejected on HMFS. Stage native launchers ahead of the
        # dependency bin directory so make can invoke them normally.
        env.prepend_path("PATH", self._stage_glib_python_tools())
        env.prepend_path("PKG_CONFIG_PATH", pc_dir)
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # gettextize 0.22.5 把 gettext_datadir（及 gettext m4 宏目录）硬编码为
        # gettext 制品构建机的绝对路径（@datadir@ 在 gettext 构建期展开），而
        # Conan 制品可重定位：预检机 conan-home 与构建机不同 → baked 路径不存在，
        # gettextize 报 "gettext source directory '...' doesn't exist" 并以
        # "*** Stop." 中止（R19 真机预检失败；已用 gettext-0.22.5 的 gettextize.in
        # 本机模拟精确复现）。gettextize 支持 $gettext_datadir 环境覆盖
        # （脚本首部 `: ${gettext_datadir=...}`），aclocal 支持 $ACLOCAL_PATH：
        # 指向真实工具包目录即可，无需修改上游 autogen.sh。
        gettext_pkg = self.dependencies.build["gettext"].package_folder
        gettext_datadir = os.path.join(gettext_pkg, "share", "gettext")
        if os.path.isdir(gettext_datadir):
            env.define("gettext_datadir", gettext_datadir)
        else:
            self.output.warning(
                f"gettext package lacks share/gettext: {gettext_datadir}")
        gettext_aclocal = os.path.join(gettext_pkg, "share", "aclocal")
        if os.path.isdir(gettext_aclocal):
            env.prepend_path("ACLOCAL_PATH", gettext_aclocal)
        else:
            self.output.warning(
                f"gettext package lacks share/aclocal: {gettext_aclocal}")
        env.vars(self).save_script("avahi_env")

    def _stage_bootstrap_tools(self):
        """Stage native launchers for Gettext and Libtool shell scripts."""
        tools_dir = os.path.join(self.build_folder, ".bootstrap-tools")
        scripts_dir = os.path.join(tools_dir, "scripts")
        os.makedirs(scripts_dir, exist_ok=True)
        for name, dependency in (
            ("gettextize", "gettext"),
            ("libtoolize", "libtool"),
        ):
            package = self.dependencies.build[dependency].package_folder
            source = os.path.join(package, "bin", name)
            if not os.path.isfile(source):
                raise ConanException(
                    f"{dependency} package lacks required script: {source}")
            script = os.path.join(scripts_dir, name)
            shutil.copy2(source, script)
            with open(script, "r", encoding="utf-8") as handle:
                text = handle.read()
            if name == "gettextize":
                replacements = {
                    'prefix="/"': f"prefix={json.dumps(package)}",
                }
            else:
                share = os.path.join(package, "share")
                libtool = os.path.join(share, "libtool")
                replacements = {
                    '  prefix="/"': f"  prefix={json.dumps(package)}",
                    '  datadir="//share"':
                        f"  datadir={json.dumps(share)}",
                    '  pkgauxdir="//share/libtool/build-aux"':
                        f"  pkgauxdir={json.dumps(os.path.join(libtool, 'build-aux'))}",
                    '  pkgltdldir="//share/libtool"':
                        f"  pkgltdldir={json.dumps(libtool)}",
                    '  aclocaldir="//share/aclocal"':
                        f"  aclocaldir={json.dumps(os.path.join(share, 'aclocal'))}",
                }
            for old, new in replacements.items():
                if text.count(old) != 1:
                    raise ConanException(
                        f"{name} has an unexpected installation path: {old}")
                text = text.replace(old, new, 1)
            with open(script, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            launcher = os.path.join(tools_dir, name)
            if name == "gettextize":
                shutil.copy2(script, launcher)
                os.chmod(launcher, 0o755)
            else:
                self._build_shell_tool_launcher(launcher, script)
        return tools_dir

    def _build_shell_tool_launcher(self, launcher, script):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}) or {}
        compiler = compilers.get("c")
        if not compiler:
            raise ConanException(
                "C compiler not found in tools.build:compiler_executables")
        source = f"{launcher}-runner.c"
        shell = "/bin/sh"
        with open(source, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#include <stdio.h>\n"
                "#include <stdlib.h>\n"
                "#include <unistd.h>\n"
                f"static const char *shell_path = {json.dumps(shell)};\n"
                f"static const char *script_path = {json.dumps(script)};\n"
                "int main(int argc, char **argv) {\n"
                "    char **args = (char **)calloc((size_t)argc + 2, sizeof(char *));\n"
                "    if (!args) return 126;\n"
                "    args[0] = (char *)shell_path;\n"
                "    args[1] = (char *)script_path;\n"
                "    for (int i = 1; i < argc; ++i) args[i + 1] = argv[i];\n"
                "    args[argc + 1] = NULL;\n"
                "    execv(shell_path, args);\n"
                "    perror(\"execv\");\n"
                "    return 127;\n"
                "}\n"
            )
        self.run(f'"{compiler}" "{source}" -o "{launcher}"')
        os.chmod(launcher, 0o755)

    def _stage_automake_tools(self):
        """Create native launchers for cross-UID Conan cache scripts."""
        package = self.dependencies.build["automake"].package_folder
        tools_dir = os.path.join(self.build_folder, ".automake-tools")
        os.makedirs(tools_dir, exist_ok=True)
        for name, real_name, arguments in (
            ("aclocal", ".aclocal-real", (
                f"--automake-acdir={os.path.join(package, 'share', 'aclocal-1.18')}",
                f"--system-acdir={os.path.join(package, 'share', 'aclocal')}",
            )),
            ("automake", ".automake-real", (
                f"--libdir={os.path.join(package, 'share', 'automake-1.18')}",
            )),
        ):
            real_script = os.path.join(package, "bin", real_name)
            if not os.path.isfile(real_script):
                raise ConanException(
                    f"Automake package lacks required script: {real_script}")
            self._build_perl_tool_launcher(
                os.path.join(tools_dir, name), real_script, arguments)
        return tools_dir

    def _build_perl_tool_launcher(self, launcher, script, fixed_args):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}) or {}
        compiler = compilers.get("c")
        if not compiler:
            raise ConanException(
                "C compiler not found in tools.build:compiler_executables")
        source = f"{launcher}-runner.c"
        # OHOS PC arm64 SDK 的 Perl 固定在 /data/service/hnp/bin/perl（与
        # ci/conan/profiles/ohos-aarch64 的工具链目录一致）；本工具仅用于
        # 跨 UID 缓存脚本的本机解释器包装，编译期解析，运行期无 Perl 依赖。
        perl = "/data/service/hnp/bin/perl"
        fixed = ", ".join(json.dumps(value) for value in fixed_args)
        fixed = f"{fixed}, " if fixed else ""
        with open(source, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#include <stdio.h>\n"
                "#include <stdlib.h>\n"
                "#include <unistd.h>\n"
                f"static const char *perl_path = {json.dumps(perl)};\n"
                f"static const char *script_path = {json.dumps(script)};\n"
                f"static const char *fixed_args[] = {{{fixed}NULL}};\n"
                "int main(int argc, char **argv) {\n"
                "    size_t fixed_count = (sizeof(fixed_args) / sizeof(fixed_args[0])) - 1;\n"
                "    char **args = (char **)calloc((size_t)argc + fixed_count + 2, sizeof(char *));\n"
                "    if (!args) return 126;\n"
                "    args[0] = (char *)perl_path;\n"
                "    args[1] = (char *)script_path;\n"
                "    for (size_t i = 0; i < fixed_count; ++i) args[i + 2] = (char *)fixed_args[i];\n"
                "    for (int i = 1; i < argc; ++i) args[fixed_count + i + 1] = argv[i];\n"
                "    args[fixed_count + argc + 1] = NULL;\n"
                "    execv(perl_path, args);\n"
                "    perror(\"execv\");\n"
                "    return 127;\n"
                "}\n"
            )
        self.run(f'"{compiler}" "{source}" -o "{launcher}"')
        os.chmod(launcher, 0o755)

    def _stage_glib_python_tools(self):
        tools_dir = os.path.join(self.build_folder, ".glib-tools")
        scripts_dir = os.path.join(tools_dir, "scripts")
        os.makedirs(scripts_dir, exist_ok=True)
        glib_bin = os.path.join(
            self.dependencies["glib"].package_folder, "bin")
        for name in ("glib-genmarshal", "glib-mkenums"):
            source = os.path.join(glib_bin, name)
            if not os.path.isfile(source):
                raise ConanException(f"GLib package lacks required tool: {source}")
            script = os.path.join(scripts_dir, name)
            shutil.copy2(source, script)
            os.chmod(script, 0o755)
            launcher = os.path.join(tools_dir, name)
            if str(self.settings.os) == "OHOS":
                self._build_python_tool_launcher(launcher, script)
            else:
                shutil.copy2(script, launcher)
                os.chmod(launcher, 0o755)
        return tools_dir

    def _build_python_tool_launcher(self, launcher, script):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}) or {}
        compiler = compilers.get("c")
        if not compiler:
            raise ConanException(
                "C compiler not found in tools.build:compiler_executables")
        source = f"{launcher}-runner.c"
        python = os.path.realpath(sys.executable)
        with open(source, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#include <stdio.h>\n"
                "#include <stdlib.h>\n"
                "#include <unistd.h>\n"
                f"static const char *python_path = {json.dumps(python)};\n"
                f"static const char *script_path = {json.dumps(script)};\n"
                "int main(int argc, char **argv) {\n"
                "    char **args = (char **)calloc((size_t)argc + 2, sizeof(char *));\n"
                "    if (!args) return 126;\n"
                "    args[0] = (char *)python_path;\n"
                "    args[1] = (char *)script_path;\n"
                "    for (int i = 1; i < argc; ++i) args[i + 1] = argv[i];\n"
                "    args[argc + 1] = NULL;\n"
                "    execv(python_path, args);\n"
                "    perror(\"execv\");\n"
                "    return 127;\n"
                "}\n"
            )
        self.run(f'"{compiler}" "{source}" -o "{launcher}"')
        os.chmod(launcher, 0o755)

    def _configure_args(self):
        args = [
            f"--prefix={self.package_folder}",
            # 项目固定目标 OHOS PC arm64（profile os=OHOS, arch=armv8）。
            # autoconf 三元组显式声明以避免工具链探测歧义（avahi-tools 同款）。
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--with-distro=none",
            # XML is only used by avahi-daemon, which is outside this package.
            "--with-xml=none",
            # avahi-ui's Makefile.am only emits libavahi-ui-gtk3 when GLib,
            # D-Bus and a GTK+ version are all enabled (BUILD_UI gate).
            "--enable-glib",
            "--enable-gtk3",
            "--enable-tests",
            # GTK2 support builds libavahi-ui against gtk+-2.0; the gtk2
            # Conan package is not published, so only the GTK3 variant is
            # produced and GTK2 is disabled explicitly.
            "--disable-gtk",
            # OHOS has no system libintl; the selected libraries do not require
            # translated runtime messages.
            "--disable-nls",
            "--disable-introspection",
            "--disable-compat-libdns_sd",
            "--disable-compat-howl",
            "--disable-libevent",
            "--disable-qt3",
            "--disable-qt4",
            "--disable-qt5",
            "--disable-python",
            "--disable-mono",
            "--disable-autoipd",
            "--disable-core-docs",
            "--disable-manpages",
            "--disable-xmltoman",
            "--disable-gdbm",
            "--disable-libdaemon",
        ]
        if not self.options.shared:
            args.extend(["--disable-shared", "--enable-static"])
        else:
            args.extend(["--enable-shared", "--disable-static"])
        return args

    def _patch_generated_configure(self, configure):
        """HMFS workaround (E011/E112/E118): strip ``umask 077`` from the
        AS_TMPDIR temp-dir creation in the *generated* configure.

        config.status aborts with ``can't create ./confXXXXXX/subs1.awk:
        Permission denied`` because ``(umask 077 && mktemp -d ...)``
        creates a drwx--S--- (2700 + setgid) directory that HMFS refuses
        to write into even for its creator.  Removing ``umask 077``
        (aaphoto/abiword/acl proven) lets mktemp use the default umask so
        the temp dir is writable.  avahi ships no configure (autogen.sh
        generates it), so the patch is applied in build() right after
        autogen, before configure runs.  config.status is written from a
        heredoc embedded in configure, so patching configure covers both
        scripts; the ``umask 077 && mktemp -d`` / ``umask 077 && mkdir``
        substrings contain no ``$``/backticks and match in both the live
        code and the heredoc template (including its backslash-escaped copy).
        """
        with open(configure, "r", encoding="utf-8") as handle:
            text = handle.read()
        # autoconf 的 AS_TMPDIR 里 mktemp 行拼写是 `umask 077`，而 mkdir
        # fallback 行是 autoconf 自带的拼写错误 `umash 077`（aaphoto/abiword
        # 补丁均为 `umash 077 && mkdir`），两种拼写都要覆盖。
        patched, n_mktemp = re.subn(
            r"um(?:ask|ash) 077 && mktemp -d", "mktemp -d", text)
        patched, n_mkdir = re.subn(
            r"um(?:ask|ash) 077 && mkdir", "mkdir", patched)
        if n_mktemp == 0 and n_mkdir == 0:
            self.output.warning(
                "generated configure has no AS_TMPDIR 'umask 077' pattern; "
                "HMFS workaround not applied")
            return
        with open(configure, "w", encoding="utf-8") as handle:
            handle.write(patched)
        self.output.info(
            "patched generated configure AS_TMPDIR: removed 'umask 077 && ' "
            f"(mktemp:{n_mktemp}, mkdir:{n_mkdir})")

    def build(self):
        apply_conandata_patches(self)
        env = ["conanbuild", "conanrun", "avahi_env"]
        src = self.source_folder
        # HMFS 工作目录下 HNP bash 启动即 getcwd 失败（[shell_getcwd]：cannot
        # access parent directories: Not supported），平台诊断要求改用 HMBS 注入的
        # SHELL=/bin/sh（并同步 CONFIG_SHELL）解释脚本，禁止硬编码 bash。
        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")
        # The tarball has no configure: generate it via autogen.sh.
        # NOCONFIGURE=1 prevents autogen.sh from running configure itself
        # (it would exec the script via shebang, which HarmonyOS refuses).
        self.run(
            f"NOCONFIGURE=1 CONFIG_SHELL={shell} SHELL={shell} {shell} autogen.sh",
            cwd=src, env=env)
        if not os.path.exists(os.path.join(src, "configure")):
            raise ConanException("autogen.sh did not produce configure")
        # HMFS 安全机制拒绝写入 mktemp -d 的 2700+setgid 临时目录，导致
        # config.status 报 "can't create ./confXXXXXX/subs1.awk: Permission
        # denied"（E011/E112/E118）。configure 由 autogen.sh 动态生成，无法打
        # 归档补丁；这里直接在运行前文本 patch 生成的 configure（aaphoto/
        # abiword/acl 同款方案，不依赖可执行位/env），覆盖 configure 本体与
        # 其内嵌的 config.status heredoc 模板。
        self._patch_generated_configure(os.path.join(src, "configure"))
        # Run configure explicitly via sh (bypass HarmonyOS script-exec limit).
        self.run(
            f"CONFIG_SHELL={shell} SHELL={shell} {shell} configure "
            + " ".join(self._configure_args()),
            cwd=src, env=env)
        # Build in dependency order: avahi-ui links avahi-common,
        # avahi-client and avahi-glib.
        self.run("make -C avahi-common -j1", cwd=src, env=env)
        self.run("make -C avahi-client -j1", cwd=src, env=env)
        self.run("make -C avahi-glib -j1", cwd=src, env=env)
        self.run("make -C avahi-ui -j1", cwd=src, env=env)

        # Upstream tests. avahi-ui/ declares no TESTS target; the pure unit
        # tests live in avahi-common and do not need avahi-daemon.  avahi-client
        # tests (client-test, srv-test, ...) all require a live avahi-daemon and
        # are therefore not runnable in the CI sandbox.
        self._run_upstream_tests(shell, src, env)

    def _run_upstream_tests(self, shell, src, env):
        log = os.path.join(self.build_folder, "make-check.log")
        entries = []
        programs = (
            ("strlst-test", "avahi-common"),
            ("domain-test", "avahi-common"),
            ("alternative-test", "avahi-common"),
            ("timeval-test", "avahi-common"),
            ("utf8-test", "avahi-common"),
            ("glib-watch-test", "avahi-glib"),
        )
        with open(log, "w", encoding="utf-8", newline="\n") as handle:
            for program, subdir in programs:
                handle.write(f"# {program}\n")
                try:
                    self.run(f"{shell} -c './{program}'", cwd=os.path.join(src, subdir),
                             env=env, stdout=handle, stderr=handle)
                    entries.append((program, "PASS"))
                except ConanException:
                    entries.append((program, "FAIL"))
        with open(log, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        passed = sum(1 for _, st in entries if st == "PASS")
        failed = sum(1 for _, st in entries if st == "FAIL")
        upstream = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "upstream unit tests (avahi-common/avahi-glib)",
            "command": "; ".join(f"make -C {s} && ./{p}"
                                 for p, s in entries) or "none",
            "discovered": len(entries),
            "executed": len(entries),
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        if failed > 0:
            raise ConanException(
                f"upstream tests failed: {passed} passed, {failed} failed\n{text}")

    def package(self):
        # Application package: do not run make install (the upstream rules
        # would also install the libraries and .desktop data files).  Collect
        # the bssh binary straight from the build tree by its ELF magic and
        # recreate the bvnc/bshell aliases the upstream install-exec-local
        # rule builds (rm -f first: HMFS forbids ln -sf over an existing
        # name; on symlink failure fall back to an independent copy).
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        ui_dir = os.path.join(self.source_folder, "avahi-ui")
        for name in self._PROGRAMS:
            binary = self._find_program_binary(ui_dir, name)
            shutil.copy2(binary, os.path.join(bin_dir, name))
        for target, aliases in self._ALIASES.items():
            target_path = os.path.join(bin_dir, target)
            for alias in aliases:
                alias_path = os.path.join(bin_dir, alias)
                if os.path.lexists(alias_path):
                    os.remove(alias_path)
                try:
                    os.symlink(target, alias_path)
                except OSError:
                    shutil.copy2(target_path, alias_path)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as binary:
                return binary.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_program_binary(self, ui_dir, name):
        # libtool 把真实可执行文件放在 .libs/，顶层可能是 wrapper 脚本；
        # 用 ELF 魔数挑出真身，两种布局都兼容（avahi-tools 同款）。
        candidates = (
            os.path.join(ui_dir, ".libs", name),
            os.path.join(ui_dir, name),
        )
        for candidate in candidates:
            if os.path.isfile(candidate) and self._is_elf(candidate):
                return candidate
        raise ConanException(
            f"built program {name} not found under {ui_dir} "
            "(looked in .libs/ and top level)")

    def package_info(self):
        # Application package: only the bssh/bvnc/bshell executables are
        # published (R38 — bindirs for tool discovery).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "avahi-ui-tools")
        self.cpp_info.set_property("cmake_target_name", "avahi-ui-tools::avahi-ui-tools")
        self.cpp_info.set_property("pkg_config_name", "avahi-ui-tools")
