#!/usr/bin/env python3
"""Conan recipe — libitl-gobject 0.3 (GObject bindings for libitl).

上游 https://github.com/aelmahmoudy/libitl-gobject 的 tag 归档**不含任何生成好的
Autotools 文件**（无 configure / Makefile.in / aclocal.m4 / ltmain.sh / m4/），
上游 README 明确要求先跑 `autoreconf -f -i`。因此：

1. build_requirements 引入 automake/1.18 + libtool/2.5.4（制品仓已发布）；
2. `_run_autogen()` **分步**调用各生成器——OHOS HMDFS 下整条 `autoreconf` 存在
   autoconf.m4f 加载冲突（同款处理见 archives/a/abiword-plugin-gdict/3.0.8）；
3. `m4/` 目录随配方 vendoring：configure.ac 用了 `PKG_CHECK_MODULES`（pkg.m4）与
   `GOBJECT_INTROSPECTION_CHECK`（introspection.m4），二者不在构建机的默认 aclocal
   搜索路径里，缺失会让 autoconf 直接报 "possibly undefined macro"。

阶段一（本配方）只交付库本体 libitl_gobject.so，introspection 关闭：
configure.ac 的 `GOBJECT_INTROSPECTION_CHECK` 默认 enable_introspection=auto，在
PKG_CONFIG_PATH 找不到 gobject-introspection-1.0 时自动把 HAVE_INTROSPECTION 置为
false，src/Makefile.am 的 gir/typelib 块随之整体跳过；此处再显式传
`--disable-introspection` 让结果确定。

其它上游问题由 patches/ 修正：
- 0001: src/Makefile.am 硬编码 Debian 系统路径 `-I/usr/include/itl`；
- 0002: libitl-gobject.pc.in 的链接名写成 `-litl-gobject`，而实际库文件是 libitl_gobject.so；
- 0003: src/Makefile.am 两条手写 glib-mkenums 规则的输入缺 `$(srcdir)/`，在
  basic_layout 的 VPATH（out-of-tree）构建下 make 找不到 itl-gobject-enums.*.in；
- 0004: itl-gobject.h 的 `#include <hijri.h>` / `<prayer.h>` 补上 `itl/` 前缀。

关于头文件：上游把 libitl 与 libitl-gobject 的头文件都装进同一个
`$(includedir)/itl`，而在 Conan 下二者是两个独立 prefix，所以
`include/itl/` 既要在本配方的 CPPFLAGS 里显式给出（供本包自己的源码编译），
也要在 package_info 的 includedirs 里导出（供下游解析），并由补丁 0004 让
头文件内部改用带前缀的包含路径——三者缺一不可。
"""
import glob
import os
import re
import shutil
import stat
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


_AUTOTOOLS_SCRIPTS = (
    "configure", "config.guess", "config.sub", "install-sh", "missing",
    "compile", "depcomp", "ltmain.sh", "test-driver", "ylwrap",
)

# E007 §1.2 — recognised by `case $UNAME_SYSTEM in` before the NetBSD arm.
_HARMONYOS_GUESS_BLOCK = (
    '    *:HarmonyOS:*:*)\n'
    '\tcase "$UNAME_MACHINE" in\n'
    '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
    '\t    armv7*|armv8*) MACHINE=arm ;;\n'
    '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
    '\t    i?86)         MACHINE=i686 ;;\n'
    '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
    '\tesac\n'
    '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
    '\t;;\n\n'
)


def _restore_autotools_script_modes(conanfile):
    """Re-add the execute bit to freshly generated Autotools scripts.

    OHOS/HMDFS does not preserve the executable bit across the m4/autoconf
    pipeline (the generated `configure` lands as 0660/0770 depending on the
    writer's umask), so `execve()` on it fails with EACCES. Same workaround as
    archives/p/pcre2/10.45.1.1.
    """
    for root in (conanfile.source_folder, conanfile.build_folder):
        if not root or not os.path.isdir(root):
            continue
        for current, _, files in os.walk(root):
            for name in _AUTOTOOLS_SCRIPTS:
                if name not in files:
                    continue
                path = os.path.join(current, name)
                try:
                    mode = os.stat(path).st_mode
                    os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP
                             | stat.S_IXOTH)
                except OSError:
                    pass


def _drop_umask_077(conanfile, path):
    """Neutralise the private-temp-dir dance autoconf emits (E011/E114).

    The generated `configure` (and the `config.status` it writes) creates its
    scratch directory with `umask 077 && mktemp -d ./confXXXXXX`. On HMDFS that
    directory ends up as 2700 and is not writable even by its own owner, so
    config.status dies with "cannot create ./confXXXXXX/subs1.awk: Permission
    denied". Relaxing the umask keeps the machinery intact but leaves the
    directory traversable — the same treatment as
    archives/a/abiword-plugin-gdict/3.0.8 and archives/l/libiodbc2/3.52.16.
    """
    if not os.path.isfile(path):
        return
    replace_in_file(conanfile, path, "umask 077", "umask 022", strict=False)


class LibitlGobjectConan(ConanFile):
    name = "libitl-gobject"
    version = "0.3"
    description = ("GObject bindings for libitl — Hijri/Gregorian conversion, "
                   "Muslim prayer times and Qibla direction")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/aelmahmoudy/libitl-gobject"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)
        # configure.ac consumes macros that live outside the default aclocal
        # search path on the build host (pkg.m4, introspection.m4).
        macro_dir = os.path.join(self.recipe_folder, "m4")
        if os.path.isdir(macro_dir):
            shutil.copytree(
                macro_dir,
                os.path.join(self.export_sources_folder, "m4"),
                dirs_exist_ok=True,
            )

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libitl-gobject is packaged for Linux/OHOS")
        if self.settings.os == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "libitl-gobject supports OHOS armv8 only")

    def requirements(self):
        # configure.ac: AC_CHECK_LIB([itl], [getNorthQibla])
        self.requires("libitl/0.8.0", transitive_headers=True,
                      transitive_libs=True)
        # configure.ac: PKG_CHECK_MODULES(GOBJECT, gobject-2.0 >= 2.2.0)
        # 与 gobject-introspection/1.78.1.1 自身依赖的 glib 版本保持一致，
        # 避免后续开启 introspection 时 typelib 版本错配。
        self.requires("glib/2.84.0.1", transitive_headers=True,
                      transitive_libs=True)

    def build_requirements(self):
        # The GitHub tag archive ships no configure/Makefile.in/aclocal.m4.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _dependency_paths(self):
        includes = []
        libdirs = []
        for dep in self.dependencies.values():
            package_folder = getattr(dep, "package_folder", None)
            if not package_folder:
                continue
            for include in dep.cpp_info.includedirs:
                includes.append(include if os.path.isabs(include)
                                else os.path.join(package_folder, include))
            for libdir in dep.cpp_info.libdirs:
                libdirs.append(libdir if os.path.isabs(libdir)
                               else os.path.join(package_folder, libdir))

        # libitl installs its public headers below include/itl/ while its
        # aggregate Conan metadata only exports include/. itl-gobject.h includes
        # <hijri.h>/<prayer.h> without the itl/ prefix, so that nested directory
        # has to be added explicitly.
        nested_includes = {
            "libitl": (os.path.join("include", "itl"),),
        }
        for dep_name, paths in nested_includes.items():
            try:
                package_folder = self.dependencies[dep_name].package_folder
            except KeyError:
                continue
            if not package_folder:
                continue
            for path in paths:
                include = os.path.join(package_folder, path)
                if os.path.isdir(include) and include not in includes:
                    includes.append(include)
        return includes, libdirs

    def _glib_mkenums(self):
        """Return a host-runnable glib-mkenums wrapper path, or None.

        src/Makefile.am calls the bare `glib-mkenums` name (twice) to generate
        itl-gobject-enums.{c,h}. The glib package ships it as a Python script,
        so a wrapper invoked with the build interpreter is used and its
        directory is prepended to PATH (same approach as
        archives/a/atk/2.28.0.1).
        """
        tool_path = None
        for dependency in self.dependencies.host.values():
            candidate = os.path.join(dependency.package_folder, "bin",
                                     "glib-mkenums")
            if os.path.isfile(candidate):
                tool_path = candidate
                break
        if not tool_path:
            return None
        wrapper_dir = os.path.join(self.generators_folder, "glib-tools-bin")
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper_path = os.path.join(wrapper_dir, "glib-mkenums")
        with open(wrapper_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                f"#!{sys.executable}\n"
                "import runpy\n"
                "import sys\n"
                f"sys.argv = [{tool_path!r}] + sys.argv[1:]\n"
                f"runpy.run_path({tool_path!r}, run_name='__main__')\n"
            )
        os.chmod(wrapper_path, 0o755)
        return wrapper_dir

    # ------------------------------------------------------------------
    # generate
    # ------------------------------------------------------------------

    def generate(self):
        PkgConfigDeps(self).generate()

        # src/Makefile.am invokes the bare `glib-mkenums` command, and the host
        # PATH already carries a /data/service/hnp/bin/glib-mkenums whose
        # `#!/usr/bin/perl` shebang points at a path that does not exist
        # ("bad interpreter: Permission denied", make Error 126). Put the
        # runpy wrapper in front of it — this must happen *before*
        # VirtualBuildEnv snapshots buildenv_info into conanbuildenv-*.sh.
        glib_tools_bin = self._glib_mkenums()
        if glib_tools_bin:
            self.buildenv_info.prepend_path("PATH", glib_tools_bin)
            self.output.info(
                "libitl-gobject: prepend glib tools to PATH: %s" % glib_tools_bin)

        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            # Phase 1: library only. Upstream .gir/.typelib generation needs a
            # working g-ir-scanner, which is a separate workstream.
            "--disable-introspection",
        ])

        includes, libdirs = self._dependency_paths()
        if includes:
            tc.configure_args.append(
                "CPPFLAGS=" + " ".join(f"-I{path}" for path in includes))
        if libdirs:
            # LDFLAGS carries the search paths only — never a linkable object.
            # `LDFLAGS` applies to every configure probe link, so naming a
            # concrete .so here would make the throwaway conftest binaries
            # depend on it; when the loader cannot find it (no run env during
            # configure) the probe dies with exit 127 and configure misreports
            # "cannot run C compiled programs" (E064/E505). The real library
            # gets -lintl from glib-2.0.pc, which expands Requires and Libs
            # into GOBJECT_LIBS anyway.
            tc.configure_args.append(
                "LDFLAGS=" + " ".join(f"-L{path}" for path in libdirs))
        tc.generate()

        if str(self.settings.os) == "OHOS":
            self._export_toolchain_env(glib_tools_bin)

    def _export_toolchain_env(self, glib_tools_bin=None):
        """Expose the OHOS toolchain helpers the Autotools generators need.

        The conanbuild environment does not carry `ar`/`ranlib`/`nm` absolute
        paths nor a usable `M4`/`PKG_CONFIG`; the same shims are used by
        archives/a/abiword-plugin-gdict/3.0.8. This script is sourced last by
        conanbuild.sh, so it is also the reliable place to put the glib-mkenums
        wrapper at the front of PATH, and it deliberately does *not* re-prepend
        /data/service/hnp/bin — that directory is already on the base PATH and
        pushing it forward would shadow the wrapper.
        """
        tools = self.conf.get("tools.build:compiler_executables",
                              default={}, check_type=dict)
        tool_dir = os.path.dirname(tools.get("c", "")) or ""
        env = Environment()
        for variable, executable in {
            "LD": "ld.lld",
            "AR": "llvm-ar",
            "NM": "llvm-nm",
            "RANLIB": "llvm-ranlib",
            "STRIP": "llvm-strip",
            "OBJDUMP": "llvm-objdump",
        }.items():
            path = os.path.join(tool_dir, executable) if tool_dir else ""
            if path and os.path.exists(path):
                env.define_path(variable, path)
        perl = shutil.which("perl") or "/data/service/hnp/bin/perl"
        if os.path.isfile(perl):
            env.define_path("PERL", perl)
        for pattern, variable in (
            ("/data/service/hnp/autoconf.org/autoconf_*/bin/autoconf", None),
            ("/data/service/hnp/m4.org/m4_*/bin/m4", "M4"),
        ):
            candidates = sorted(glob.glob(pattern), reverse=True)
            if candidates:
                env.prepend_path("PATH", os.path.dirname(candidates[0]))
                if variable:
                    env.define_path(variable, candidates[0])
        pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        if pkg_config:
            env.define_path("PKG_CONFIG", pkg_config)
        if glib_tools_bin:
            env.prepend_path("PATH", glib_tools_bin)
        env.vars(self).save_script("libitl_gobject_toolchain")

    # ------------------------------------------------------------------
    # autotools bootstrap
    # ------------------------------------------------------------------

    def _stage_libtool_data(self):
        """Materialise the three directories libtoolize --install expects."""
        libtool_root = self.dependencies.build["libtool"].package_folder
        pkgdatadir = os.path.join(
            os.environ.get("TMPDIR", self.build_folder),
            "libitl-gobject-libtool-" + os.path.basename(self.build_folder),
        )
        for subdir in ("build-aux", "m4", "libltdl"):
            os.makedirs(os.path.join(pkgdatadir, subdir), exist_ok=True)

        source_aux = os.path.join(libtool_root, "share", "libtool", "build-aux")
        for filename in os.listdir(source_aux):
            shutil.copy2(os.path.join(source_aux, filename),
                         os.path.join(pkgdatadir, "build-aux", filename))

        source_m4 = os.path.join(libtool_root, "share", "aclocal")
        for filename in os.listdir(source_m4):
            if filename.endswith(".m4"):
                shutil.copy2(os.path.join(source_m4, filename),
                             os.path.join(pkgdatadir, "m4", filename))

        with open(os.path.join(pkgdatadir, "libltdl", "keep.txt"), "w") as handle:
            handle.write("x\n")
        return pkgdatadir

    def _aclocal_path(self):
        source = self.source_folder
        macro_dirs = [os.path.join(source, "m4")]
        for dep_name in ("libtool", "automake"):
            try:
                folder = self.dependencies.build[dep_name].package_folder
            except KeyError:
                continue
            candidate = os.path.join(folder, "share", "aclocal")
            if os.path.isdir(candidate):
                macro_dirs.append(candidate)
        return ":".join(macro_dirs) + ":$ACLOCAL_PATH"

    def _run_autogen(self):
        # Run the generators separately: this avoids the HMDFS
        # autoreconf/autoconf.m4f loading conflict on OHOS and keeps the
        # tool_requires environment explicit.
        source = self.source_folder
        aclocal_path = self._aclocal_path()
        ohos = str(self.settings.os) == "OHOS"
        libtool_data = self._stage_libtool_data() if ohos else None

        if ohos:
            aclocal_cmd = (
                'aclocal_dir="${ACLOCAL%/*}"; '
                'automake_prefix="${aclocal_dir%/*}"; '
                '"/data/service/hnp/bin/perl" "$aclocal_dir/.aclocal-real" '
                '--automake-acdir="$automake_prefix/share/aclocal-1.18" '
                '--system-acdir="$automake_prefix/share/aclocal" --force'
            )
        else:
            aclocal_cmd = '"${ACLOCAL:-aclocal}" --force'
        self.run(f'ACLOCAL_PATH="{aclocal_path}" ' + aclocal_cmd,
                 cwd=source, env="conanbuild")

        if ohos:
            self.run(
                'libtoolize="${LIBTOOLIZE:-libtoolize}"; '
                f'_lt_pkgdatadir="{libtool_data}" sh "$libtoolize"'
                ' --copy --force --install',
                cwd=source, env="conanbuild",
            )
        else:
            self.run('"${LIBTOOLIZE:-libtoolize}" --copy --force --install',
                     cwd=source, env="conanbuild")

        self.run("autoconf -o configure configure.ac", cwd=source,
                 env="conanbuild")

        if ohos:
            automake_cmd = (
                'automake_dir="${AUTOMAKE%/*}"; '
                'automake_prefix="${automake_dir%/*}"; '
                '"/data/service/hnp/bin/perl" "$automake_dir/.automake-real" '
                '--libdir="$automake_prefix/share/automake-1.18" '
                '--add-missing --copy --no-force'
            )
        else:
            automake_cmd = ('"${AUTOMAKE:-automake}" '
                            '--add-missing --copy --no-force')
        self.run(automake_cmd, cwd=source, env="conanbuild")

    # ------------------------------------------------------------------
    # E007 — teach the generated config.guess/config.sub about HarmonyOS
    # ------------------------------------------------------------------

    @staticmethod
    def _locate_autotools_patch_script():
        """Find scripts/patch-autotools-ohos.pl outside the Conan cache.

        `conan create` exports the recipe into the cache, so `recipe_folder`
        never points back into the repository tree; the skill's patch script is
        therefore located through the environment instead (CI_REPO_ROOT is set
        by ci/conan/*.sh, OHC_SKILL_ROOT by the local harness).
        """
        for variable in ("CI_REPO_ROOT", "OHC_SKILL_ROOT", "OHC_ROOT"):
            root = os.environ.get(variable, "")
            if not root:
                continue
            script = os.path.join(root, "scripts", "patch-autotools-ohos.pl")
            if os.path.isfile(script):
                return script
        return ""

    def _patch_harmonyos_config_scripts(self):
        """E007: make config.guess/config.sub recognise HarmonyOS.

        `uname -s` reports "HarmonyOS" and the FSF config.guess shipped by
        libtool/automake has no branch for it, so configure dies with
        "cannot guess build type; you must specify one" before anything is
        compiled. Iron rule R1 forbids papering over that with
        `--build`/`--host`: autoconf would then treat the build as a cross
        build and silently skip every AC_RUN_IFELSE, producing a wrong config.h.
        The generated detection scripts are patched instead. Anchors follow
        scripts/patch-autotools-ohos.pl; every edit is guarded, so toolchain
        versions whose config.sub already knows ohos are left untouched.
        """
        guess = os.path.join(self.source_folder, "config.guess")
        sub = os.path.join(self.source_folder, "config.sub")
        if not (os.path.isfile(guess) and os.path.isfile(sub)):
            raise ConanException(
                "config.guess/config.sub missing after autogen — the E007 "
                "HarmonyOS recognition fix cannot be applied")

        script = self._locate_autotools_patch_script()
        if script:
            self.output.info("E007: patching detection scripts with %s" % script)
            perl = shutil.which("perl") or "/data/service/hnp/bin/perl"
            subprocess.run([perl, script, guess, sub], check=True)
            return

        self.output.info(
            "E007: patch-autotools-ohos.pl not reachable, applying the "
            "in-recipe port (identical anchors, archives/a/addrwatch)")
        self._patch_config_guess_for_ohos(guess)
        self._patch_config_sub_for_ohos(sub)

    def _patch_config_guess_for_ohos(self, path):
        with open(path, encoding="utf-8") as handle:
            data = handle.read()
        original = data

        # §1.1 LIBC detection: HarmonyOS is a musl-based Linux userland.
        if "__OHOS__" not in data:
            data, replaced = re.subn(
                r"(?m)^([ \t]*#[ \t]*if[ \t]*defined\(__ANDROID__\)[ \t]*\n"
                r"[ \t]*LIBC=android)",
                lambda m: m.group(1) + "\n#elif defined(__OHOS__)\n    LIBC=ohos",
                data, count=1,
            )
            self.output.info("  [%s] __OHOS__ LIBC detection"
                             % ("ok" if replaced else "warn"))

        # §1.2 System identification — emit the canonical OHOS triplet.
        if "HarmonyOS" not in data:
            data, replaced = re.subn(
                r"(?m)^([ \t]+\*:NetBSD:\*:\*\)[ \t]*\n)",
                lambda m: _HARMONYOS_GUESS_BLOCK + m.group(1),
                data, count=1,
            )
            self.output.info("  [%s] HarmonyOS system identification"
                             % ("ok" if replaced else "warn"))

        if data != original:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(data)

    def _patch_config_sub_for_ohos(self, path):
        with open(path, encoding="utf-8") as handle:
            data = handle.read()
        original = data

        # §2.1 `ohos-linux` shorthand, emitted for the bare `arch-os` form.
        if "ohos-linux" not in data:
            def _insert_ohos_shorthand(match):
                return (match.group(1) + match.group(2) + match.group(4)
                        + match.group(6)
                        + "\tohos-linux)\n"
                        + match.group(3) + "basic_machine=$field1-unknown\n"
                        + match.group(5) + "basic_os=linux-ohos\n"
                        + match.group(6))

            data, replaced = re.subn(
                r"(?m)^([ \t]*android-linux\)[ \t]*\n)"
                r"(([ \t]*)basic_machine=\$field1-unknown[ \t]*\n)"
                r"(([ \t]*)basic_os=linux-android[ \t]*\n)"
                r"([ \t]*;;[ \t]*\n)",
                _insert_ohos_shorthand, data, count=1,
            )
            self.output.info("  [%s] ohos-linux triplet"
                             % ("ok" if replaced else "warn"))

        # §2.2 Accept `ohos*` as an OS type.
        if not re.search(r"gnu\*[ \t]*\|[ \t]*android\*[ \t]*\|[ \t]*ohos\*", data):
            data, replaced = re.subn(
                r"(gnu\*[ \t]*\|[ \t]*android\*)", r"\1 | ohos*", data, count=1)
            if replaced:
                self.output.info("  [ok] ohos* in the OS type list")

        # §2.3 Kernel-OS validation list.
        if "linux-ohos" not in data:
            data, replaced = re.subn(
                r"(linux-uclibc\*[/-]?[ \t]*)\)", r"\1| linux-ohos*)",
                data, count=1,
            )
            self.output.info("  [%s] linux-ohos in the kernel list"
                             % ("ok" if replaced else "warn"))

        if data != original:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(data)

    # ------------------------------------------------------------------
    # build / package
    # ------------------------------------------------------------------

    def build(self):
        apply_conandata_patches(self)
        self._run_autogen()
        self._patch_harmonyos_config_scripts()
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            # `configure` is produced by autoconf earlier in *this* build, and
            # on OHOS/HMDFS it materialises without the execute bit, so exec'ing
            # it straight away aborts with EACCES (ConanException: Error 126).
            # Repair the mode and drive it through an explicit `sh`, which only
            # requires read permission — the same treatment as
            # archives/p/pcre2/10.45.1.1 and archives/a/abiword-plugin-gdict.
            _restore_autotools_script_modes(self)
            _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
            self.run('sh "{}/configure" {}'.format(
                self.source_folder, autotools._configure_args),
                cwd=self.build_folder, env="conanbuild")
        else:
            autotools.configure()
        self._make(autotools, args=["-j1"])
        # Layer 1 of the test quality spec: upstream test target. This project
        # registers no upstream tests (no TESTS in any Makefile.am), so the
        # target is a no-op guard against a broken check machinery; functional
        # coverage lives in test_package/.
        autotools.make(target="check")

    def _make(self, autotools, args=None):
        """Layer 1 build step.

        On HarmonyOS this runs `make` with its stdout/stderr bound to a file
        rather than inheriting whatever descriptor Conan handed the build
        process. When that descriptor is a *pipe*, the first clang invocation
        launched through libtool dies with exit status 1 without printing a
        single diagnostic: the log jumps straight from libtool's echoed compile
        line to "make[2]: *** [Makefile:483: libitl_gobject_la-itl-gobject.lo]
        Error 1", `V=1` adds nothing, and re-running the very same command in
        the identical, untouched build tree succeeds as soon as it is written
        to a file instead (which is how `conan create > log` behaves). A
        zero-delay retry does not help, so it is the descriptor type that
        changes the outcome.

        The captured log is echoed back afterwards so nothing is hidden, and
        the make exit status is preserved.
        """
        if str(self.settings.os) != "OHOS":
            autotools.make(args=args)
            return
        make_program = self.conf.get("tools.gnu:make_program", default="make")
        log = os.path.join(self.build_folder, "make-ohos.log")
        self.run(
            '{make} {options} > "{log}" 2>&1; rc=$?; cat "{log}"; exit $rc'.format(
                make=make_program, options=" ".join(args or []), log=log),
            cwd=self.build_folder, env="conanbuild")

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        for la_file in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la_file)

    def package_info(self):
        self.cpp_info.libs = ["itl_gobject"]
        # src/Makefile.am: libitl_gobject_ladir = $(includedir)/itl, and the
        # shipped .pc advertises `Cflags: -I${includedir}/itl`; itl-gobject.h
        # itself does `#include <hijri.h>`. Both directories are exported so
        # consumers can write either <itl-gobject.h> or <itl/itl-gobject.h>
        # (same idiom as archives/a/aflplusplus, archives/a/apr).
        self.cpp_info.includedirs = ["include", "include/itl"]
        self.cpp_info.requires = [
            "libitl::libitl",
            "glib::glib-2.0",
            "glib::gobject-2.0",
        ]
        self.cpp_info.set_property("cmake_file_name", "libitl-gobject")
        self.cpp_info.set_property("cmake_target_name",
                                   "libitl-gobject::libitl-gobject")
        self.cpp_info.set_property("pkg_config_name", "libitl-gobject")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
