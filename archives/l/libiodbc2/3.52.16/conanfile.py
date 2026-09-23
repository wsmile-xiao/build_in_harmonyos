#!/usr/bin/env python3
"""Conan recipe — libiodbc2 3.52.16 (iODBC Driver Manager, autotools).

Upstream project is iODBC (OpenLink).  `libiodbc2` is the Debian
source-package name for the same code base: the produced shared library is
`libiodbc.so.2` ("2" is the SONAME major, not a product name).

OHOS adaptation notes:
  - the GitHub release tarball ships no `configure` (only configure.ac +
    Makefile.am), so build() bootstraps with `autoreconf -fi`;
  - the build host (CI sandbox / minimal OHOS image) only ships the autoconf
    suite, so automake/libtool come in as tool_requires (same pattern as
    argp-standalone / avahi-glib);
  - E443: HMFS cross-UID policy rejects direct shebang execution of scripts,
    both for the tools materialised inside the Conan cache
    (`Can't exec ".../aclocal": Permission denied`, exit 13) and for the OHOS
    SDK compiler, which ships as a `#!/bin/sh` wrapper around clang-15.
    `autoreconf` therefore gets task-local native launchers that exec the SDK
    perl / /bin/sh with the packaged script, and the SDK compiler is resolved
    to the underlying ELF binary.
  - configure is handed an explicit `aarch64-unknown-linux-ohos` triplet
    because config.guess cannot identify HarmonyOS
    (uname -s = "HarmonyOS", kernel "HongMeng Kernel");
  - E114: the generated configure drops `umask 077` — HMDFS forces setgid on
    directories and turns the 0700 config.status temp dir into a directory
    that is not writable even by its owner;
  - E074: make runs with -j1 — the HMDFS jobserver fifo reports EPERM
    (`make: jobserver mkfifo: Operation not permitted`, reproduced locally);
  - E490: the exec bits of the helper scripts are restored before they run;
  - GUI extensions (iodbcadm-gtk) are disabled: there is no GTK on OHOS.
"""
import json
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

OHOS_TRIPLET = "aarch64-unknown-linux-ohos"
# The packaged Automake/Libtool scripts carry this interpreter in their
# shebang; the SDK perl is the one the SDK autoreconf/autom4te expect
# (an OHOS-built perl would carry a conflicting XS runtime).
SDK_PERL = "/data/service/hnp/bin/perl"
SDK_SHELL = "/bin/sh"

_EXEC_HELPERS = (
    "configure", "config.guess", "config.sub", "install-sh", "missing",
    "compile", "depcomp", "mkinstalldirs", "ylwrap", "ltmain.sh",
)


def _perl_usable_tmpdir(path):
    """Tell whether autoconf's Perl helpers would accept `path` as TMPDIR.

    File::Spec->tmpdir() (used by autoheader/autom4te) drops every candidate
    that fails its stat-based -d/-w test and silently falls back to the
    current directory.  On an OHOS worker whose /storage mount is uid-mapped,
    files created below the build folder are reported as owned by a foreign
    uid, so that test fails for the whole tree; autoheader then puts its
    scratch files in the build folder and misjudges the file it has just
    written as unreadable
    (`autoheader: warning: cannot read <tmp>/config.hin`) -> exit 1, because
    it could not resolve a single template.  Only offer Perl a temp dir it
    will actually keep.
    """
    perl = shutil.which("perl")
    if not perl:
        return True
    import subprocess

    probe = subprocess.run(
        [perl, "-e", "exit(-d $ARGV[0] && -w $ARGV[0] ? 0 : 1)", path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return probe.returncode == 0


def _resolve_real_tool(path):
    """E443: the OHOS SDK ships its compilers as `#!/bin/sh` wrappers that
    re-exec the real binary (`exec -a <name> <real> "$@"`).  Executing such a
    script by shebang is rejected on HMFS, so resolve the underlying ELF."""
    real = os.path.realpath(path)
    try:
        with open(real, "r", encoding="utf-8", errors="ignore") as handle:
            head = handle.read(4096)
    except OSError:
        return real
    if not head.startswith("#!"):
        return real
    match = re.search(r'exec[^\n]*?(\S+)\s+"\$@"', head)
    if match:
        candidate = match.group(1)
        if os.path.isfile(candidate):
            return candidate
    return real


def _prepare_autotools_env():
    """Point AUTOCONF/AUTOHEADER/AUTOM4TE/SED at real executables.

    The packaged automake/libtool scripts hardcode install-time paths that do
    not exist in this environment."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(conanfile, path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Remove `umask 077` (and the now-orphaned parentheses) so config.status
    can create its temp dir."""
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as handle:
        data = handle.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(data)


def _restore_exec_bits(conanfile):
    """E490: HMDFS does not always preserve POSIX execute mode bits, so the
    autotools helpers in the source tree can fail with EACCES.  Restore the
    execute bit for the known helpers before autoreconf/configure run."""
    for root in (conanfile.source_folder, conanfile.build_folder):
        if not root or not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                if name not in _EXEC_HELPERS:
                    continue
                path = os.path.join(dirpath, name)
                try:
                    os.chmod(path, os.stat(path).st_mode | 0o111)
                except OSError:
                    pass


class Libiodbc2Conan(ConanFile):
    name = "libiodbc2"
    version = "3.52.16"
    description = ("iODBC Driver Manager — an ODBC 3.x driver manager "
                   "(Debian source package libiodbc2)")
    license = "LGPL-2.1-or-later"
    homepage = "https://www.iodbc.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def build_requirements(self):
        # The GitHub archive ships no `configure`, so build() runs
        # `autoreconf -fi` to bootstrap it.  The build host (CI sandbox /
        # minimal OHOS image) lacks automake/aclocal/libtoolize (only the
        # autoconf suite is present under /data/service/hnp/bin), so pull
        # them in as tool_requires (same approach as argp-standalone).
        # tool_requires are resolved with the *build* profile, so both
        # -pr:h and -pr:b must be passed to conan create.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libiodbc2 is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # ── E443: task-local interpreter bridges for the packaged tools ──────
    def _prepare_tmpdir(self):
        """clang/make need a writable temp dir; the ambient TMPDIR can point
        at a read-only or missing location, so the build-local one comes
        first.  It is not automatically usable though: autoconf's Perl helpers
        resolve TMPDIR through File::Spec->tmpdir(), which discards any
        candidate whose -d/-w test fails on the worker's filesystem and then
        silently falls back to the current directory (see
        _perl_usable_tmpdir).  Only keep a directory that both we and Perl
        accept; otherwise fall back to the ambient candidates."""
        tmpdir = None
        candidates = [os.path.join(self.build_folder, "tmp")]
        candidates += [os.environ.get(var) for var in ("TMPDIR", "TMP", "TEMP")]
        for candidate in candidates:
            if not candidate:
                continue
            try:
                os.makedirs(candidate, exist_ok=True)
            except OSError:
                continue
            if (os.access(candidate, os.W_OK)
                    and _perl_usable_tmpdir(candidate)):
                tmpdir = candidate
                break
        if tmpdir is None:
            # Last resort: the historical choice, so a broken probe still
            # yields a concrete error instead of silently using /tmp.
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmpdir
        return tmpdir

    def _compiler(self, key):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}) or {}
        compiler = compilers.get(key) or shutil.which(key)
        if not compiler:
            raise ConanException(
                f"{key} compiler not found in tools.build:compiler_executables")
        return _resolve_real_tool(compiler)

    def _run_compiler(self, command):
        """Compile a launcher.  The compiling tool is itself resolved to a
        real binary, never to a shebang wrapper."""
        import subprocess

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = dict(os.environ)
        for var in ("TMPDIR", "TMP", "TEMP"):
            env[var] = tmpdir
        proc = subprocess.run(command, shell=True, env=env,
                              cwd=self.build_folder,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = proc.stdout.decode("utf-8", "replace").strip()
        if proc.returncode != 0:
            raise ConanException("launcher compile failed (rc={}):\n{}\n{}".format(
                proc.returncode, output, command))
        if output:
            self.output.info("launcher: " + output)

    def _build_perl_tool_launcher(self, launcher, script, fixed_args):
        """Native launcher that execs the SDK perl with the packaged script."""
        source = f"{launcher}-runner.c"
        fixed = ", ".join(json.dumps(value) for value in fixed_args)
        fixed = f"{fixed}, " if fixed else ""
        with open(source, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#include <stdio.h>\n"
                "#include <stdlib.h>\n"
                "#include <unistd.h>\n"
                f"static const char *perl_path = {json.dumps(SDK_PERL)};\n"
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
        self._run_compiler(f'"{self._compiler("c")}" "{source}" -o "{launcher}"')
        os.chmod(launcher, 0o755)

    def _build_shell_tool_launcher(self, launcher, script):
        """Native launcher that execs /bin/sh with the staged script."""
        source = f"{launcher}-runner.c"
        with open(source, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#include <stdio.h>\n"
                "#include <stdlib.h>\n"
                "#include <unistd.h>\n"
                f"static const char *shell_path = {json.dumps(SDK_SHELL)};\n"
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
        self._run_compiler(f'"{self._compiler("c")}" "{source}" -o "{launcher}"')
        os.chmod(launcher, 0o755)

    def _stage_automake_tools(self):
        """Native perl launchers for aclocal/automake (E443)."""
        package = self.dependencies.build["automake"].package_folder
        tools_dir = os.path.join(self.build_folder, ".automake-tools")
        os.makedirs(tools_dir, exist_ok=True)
        for name, real_name, arguments in (
            ("aclocal", ".aclocal-real", (
                "--automake-acdir=" + os.path.join(package, "share", "aclocal-1.18"),
                "--system-acdir=" + os.path.join(package, "share", "aclocal"),
            )),
            ("automake", ".automake-real", (
                "--libdir=" + os.path.join(package, "share", "automake-1.18"),
            )),
        ):
            real_script = os.path.join(package, "bin", real_name)
            if not os.path.isfile(real_script):
                raise ConanException(
                    f"automake package lacks required script: {real_script}")
            self._build_perl_tool_launcher(
                os.path.join(tools_dir, name), real_script, arguments)
        return tools_dir

    def _stage_libtoolize(self):
        """Relocate libtoolize's install-time paths and wrap it (E443)."""
        package = self.dependencies.build["libtool"].package_folder
        tools_dir = os.path.join(self.build_folder, ".libtool-tools")
        scripts_dir = os.path.join(tools_dir, "scripts")
        os.makedirs(scripts_dir, exist_ok=True)

        source = os.path.join(package, "bin", "libtoolize")
        if not os.path.isfile(source):
            raise ConanException(f"libtool package lacks: {source}")
        script = os.path.join(scripts_dir, "libtoolize")
        shutil.copy2(source, script)

        share = os.path.join(package, "share")
        libtool = os.path.join(share, "libtool")
        replacements = {
            '  prefix="/"': f"  prefix={json.dumps(package)}",
            '  datadir="//share"': f"  datadir={json.dumps(share)}",
            '  pkgauxdir="//share/libtool/build-aux"':
                f"  pkgauxdir={json.dumps(os.path.join(libtool, 'build-aux'))}",
            '  pkgltdldir="//share/libtool"':
                f"  pkgltdldir={json.dumps(libtool)}",
            '  aclocaldir="//share/aclocal"':
                f"  aclocaldir={json.dumps(os.path.join(share, 'aclocal'))}",
            # The libtool package's own buildenv sets _lt_pkgdatadir to
            # <prefix>/share/libtool-conan, which holds no build-aux/libltdl;
            # that would override the relocated paths patched above.
            '  if test -n "$_lt_pkgdatadir"; then':
                '  _lt_pkgdatadir=""; if test -n "$_lt_pkgdatadir"; then',
        }
        with open(script, "r", encoding="utf-8") as handle:
            text = handle.read()
        for old, new in replacements.items():
            if text.count(old) != 1:
                raise ConanException(
                    f"libtoolize has an unexpected installation path: {old}")
            text = text.replace(old, new, 1)
        with open(script, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)

        launcher = os.path.join(tools_dir, "libtoolize")
        self._build_shell_tool_launcher(launcher, script)
        return tools_dir

    def generate(self):
        _prepare_autotools_env()
        tmpdir = self._prepare_tmpdir()
        tc = AutotoolsToolchain(self)
        # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS",
        # kernel "HongMeng Kernel"), so hand build/host explicitly; config.sub
        # knows `*-linux-ohos` (linux-gnu would route through the GNU path and
        # miss the OHOS headers).
        tc.configure_args.append("--build=" + OHOS_TRIPLET)
        tc.configure_args.append("--host=" + OHOS_TRIPLET)
        # No GTK on OHOS -> do not build iodbcadm-gtk / drvproxy-gtk.
        tc.configure_args.append("--disable-gui")
        # Do not install the extra libodbc.so/libodbc.a convenience aliases:
        # the install hook creates them with `ln -s`, which HMDFS rejects
        # (`ln: cannot create symbolic link ... Permission denied`), and the
        # package exposes the real libiodbc/libiodbcinst names.
        tc.configure_args.append("--disable-libodbc")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")

        env = tc.environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        # E443: CC/CXX must be real ELF binaries, not the SDK's shebang
        # wrappers (direct shebang execution is rejected on HMFS).
        env.define("CC", self._compiler("c"))
        env.define("CXX", self._compiler("cpp"))
        for variable, tool in (("AUTOCONF", "autoconf"),
                               ("AUTOHEADER", "autoheader"),
                               ("AUTOM4TE", "autom4te")):
            path = shutil.which(tool)
            if path:
                env.define(variable, path)

        # E443: run the packaged automake/libtool scripts through native
        # interpreter bridges staged in the build folder.
        automake_tools = self._stage_automake_tools()
        env.prepend_path("PATH", automake_tools)
        env.define("ACLOCAL", os.path.join(automake_tools, "aclocal"))
        env.define("AUTOMAKE", os.path.join(automake_tools, "automake"))
        libtool_tools = self._stage_libtoolize()
        env.prepend_path("PATH", libtool_tools)
        env.define("LIBTOOLIZE", os.path.join(libtool_tools, "libtoolize"))
        # The staged script carries concrete relocated paths; disable the
        # tool package's own (non-standard) relocation root.
        env.define("_lt_pkgdatadir", "")

        tc.generate(env=env)

    def _bootstrap_autotools(self):
        """Drive the autotools bootstrap with the staged interpreter bridges.

        E443: `autoreconf` resolves aclocal/automake/libtoolize through PATH
        and picks up the raw scripts from the Conan cache, whose shebang
        cannot be executed on HMFS (`Can't exec ".../aclocal": Permission
        denied`, exit 13).  Invoking the staged launchers explicitly keeps the
        bootstrap deterministic.  The SDK's own autoconf/autoheader/autom4te
        are fine to call directly.
        """
        tools = os.path.join(self.build_folder, ".automake-tools")
        ltools = os.path.join(self.build_folder, ".libtool-tools")
        autoconf = shutil.which("autoconf") or "autoconf"
        autoheader = shutil.which("autoheader") or "autoheader"
        steps = (
            f'"{os.path.join(ltools, "libtoolize")}" --force --copy',
            f'"{os.path.join(tools, "aclocal")}" -I admin',
            f'"{autoheader}"',
            f'"{os.path.join(tools, "automake")}" --copy --add-missing',
            f'"{autoconf}"',
        )
        for step in steps:
            self.run(step, cwd=self.source_folder, env="conanbuild")

    def _configure_dir(self):
        """Directory holding the generated configure/Makefile."""
        for root in (self.build_folder, self.source_folder):
            if os.path.isfile(os.path.join(root, "configure")):
                return root
        raise ConanException("configure was not generated")

    def _configure_via_shell(self, autotools):
        """Run the generated `configure` through the shell.

        E443: executing the freshly generated configure script directly is
        rejected on HMFS (`/system/bin/sh: .../configure: Permission denied`,
        exit 126), the same shebang-execution boundary as the packaged
        autotools tools.  Handing the script to /bin/sh bypasses it.
        """
        config_dir = self._configure_dir()
        configure = os.path.join(config_dir, "configure")
        command = " ".join(
            part for part in (shlex.quote(configure), autotools._configure_args)
            if part)
        self.run(f'"{SDK_SHELL}" {command}', cwd=config_dir, env="conanbuild")
        return config_dir

    def build(self):
        _prepare_autotools_env()
        self._prepare_tmpdir()
        # E490: HMDFS may have dropped the execute bits of the source-tree
        # helpers -> autoreconf/configure EACCES.
        _restore_exec_bits(self)
        # The GitHub archive ships no `configure`: bootstrap it.
        self._bootstrap_autotools()
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        # The freshly generated helpers inherit the same E490 problem.
        _restore_exec_bits(self)
        autotools = Autotools(self)
        config_dir = self._configure_via_shell(autotools)
        # E074: parallel make hits the HMDFS jobserver fifo EPERM.  make runs
        # from the directory that holds the generated Makefile.
        self.run("make -j1", cwd=config_dir, env="conanbuild")
        # Upstream ships no test suite (`make check` is a no-op) -> nothing to
        # run here; the L1 consumer test lives in test_package/ (R34/R51).

    def package(self):
        config_dir = self._configure_dir()
        self.run('make install DESTDIR=' + shlex.quote(self.package_folder),
                 cwd=config_dir, env="conanbuild")
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        # Only the libraries are packaged: iodbc-config/iodbctest are sample
        # CLI tools and the package is a pure library (same choice as the
        # sibling unixodbc recipe, which also drops bin/).
        rm(self, "*", os.path.join(self.package_folder, "bin"), recursive=True)
        rmdir(self, os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["iodbc", "iodbcinst"]
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "libiodbc2")
        self.cpp_info.set_property("cmake_target_name", "libiodbc2::libiodbc2")
        self.cpp_info.set_property("pkg_config_name", "libiodbc")
