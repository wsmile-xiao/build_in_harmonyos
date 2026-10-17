#!/usr/bin/env python3
"""Conan recipe for the Avahi core libraries, version 0.9_rc5.

Builds libavahi-common and libavahi-core, the base mDNS/DNS-SD libraries.
Only these two in-tree subdirectories are built; the Avahi daemon, client,
GLib/GObject wrappers, utilities, and language bindings are excluded (they
live in sibling packages such as avahi-glib).

The GitHub tag archive ships no generated configure script, so the recipe
runs autogen.sh with Conan-provided automake, libtool, and gettext tools.
The OHOS/HMFS bootstrap workarounds are shared with the avahi-glib recipe
built from the same v0.9-rc5 source.
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


class AvahiConan(ConanFile):
    required_conan_version = ">=2.28"
    name = "avahi"
    version = "0.9_rc5"
    description = "Avahi core mDNS/DNS-SD libraries for service discovery"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/avahi/avahi"
    url = "https://github.com/avahi/avahi"
    package_type = "library"

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
        env = Environment()
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
        env.define("_lt_pkgdatadir", "")
        # gettextize 0.22.5 bakes the gettext build machine's absolute
        # datadir into the script; point it at the relocatable Conan package.
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

    def _configure_args(self):
        args = [
            f"--prefix={self.package_folder}",
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--with-distro=none",
            # XML is only used by avahi-daemon, which is outside this package.
            "--with-xml=none",
            "--disable-glib",
            "--disable-gobject",
            # OHOS has no system libintl; core libraries need no translations.
            "--disable-nls",
            "--disable-dbus",
            "--disable-introspection",
            "--disable-compat-libdns_sd",
            "--disable-compat-howl",
            "--disable-libevent",
            "--disable-qt3",
            "--disable-qt4",
            "--disable-qt5",
            "--disable-gtk",
            "--disable-gtk3",
            "--disable-python",
            "--disable-mono",
            "--disable-autoipd",
            "--disable-doxygen-doc",
            "--disable-manpages",
            "--disable-xmltoman",
            "--disable-gdbm",
            "--disable-libdaemon",
            "--disable-libsystemd",
            "--with-systemdsystemunitdir=no",
        ]
        if not self.options.shared:
            args.extend(["--disable-shared", "--enable-static"])
        else:
            args.extend(["--enable-shared", "--disable-static"])
        return args

    def _patch_generated_configure(self, configure):
        """HMFS workaround (E011/E112/E118): strip ``umask 077`` from the
        AS_TMPDIR temp-dir creation in the generated configure so config.status
        can write into the mktemp directory that HMFS otherwise refuses."""
        with open(configure, "r", encoding="utf-8") as handle:
            text = handle.read()
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
        # HMFS: HNP bash fails getcwd in the work dir; use the injected
        # SHELL=/bin/sh to interpret scripts (never hardcode bash).
        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")
        # The tarball has no configure: generate it via autogen.sh.
        self.run(
            f"NOCONFIGURE=1 CONFIG_SHELL={shell} SHELL={shell} {shell} autogen.sh",
            cwd=src, env=env)
        if not os.path.exists(os.path.join(src, "configure")):
            raise ConanException("autogen.sh did not produce configure")
        self._patch_generated_configure(os.path.join(src, "configure"))
        self.run(
            f"CONFIG_SHELL={shell} SHELL={shell} {shell} configure "
            + " ".join(self._configure_args()),
            cwd=src, env=env)
        # Build in dependency order: common first, then core.
        self.run("make -C avahi-common -j1", cwd=src, env=env)
        self.run("make -C avahi-core -j1", cwd=src, env=env)

    def _write_install_shim(self):
        """HMBS install shim only accepts single-file two-arg calls; automake
        batch header installs (install -c -m 644 f1..fN dir/) exit 64. Write a
        cp/mkdir shim and redirect the Makefile INSTALL variable to it."""
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    "set -eu\n"
                    "mode=\n"
                    "while [ $# -gt 0 ]; do\n"
                    "  case \"$1\" in\n"
                    "    -p|-c) shift ;;\n"
                    "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
                    "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
                    "    --) shift; break ;;\n"
                    "    -*) shift ;;\n"
                    "    *) break ;;\n"
                    "  esac\n"
                    "done\n"
                    "[ $# -ge 2 ] || exit 2\n"
                    "dest=\n"
                    "for arg in \"$@\"; do dest=$arg; done\n"
                    "count=$(($# - 1))\n"
                    "if [ \"$count\" -gt 1 ]; then\n"
                    "  mkdir -p \"$dest\"\n"
                    "else\n"
                    "  mkdir -p \"$(dirname \"$dest\")\"\n"
                    "fi\n"
                    "i=1\n"
                    "for src in \"$@\"; do\n"
                    "  [ $i -gt $count ] && break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
                    "  if [ -n \"$mode\" ]; then\n"
                    "    if [ -d \"$dest\" ]; then\n"
                    "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                    "    else\n"
                    "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
                    "    fi\n"
                    "  fi\n"
                    "  i=$((i + 1))\n"
                    "done\n"
                )
        except Exception:  # noqa: BLE001
            os.close(fd)
            raise
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass
        return install

    def _redirect_install_to_shim(self, root, shim_install):
        for _root, _, _files in os.walk(root):
            if "Makefile" not in _files:
                continue
            _mp = os.path.join(_root, "Makefile")
            try:
                with open(_mp, "r", encoding="utf-8", errors="ignore") as _f:
                    _content = _f.read()
            except OSError:
                continue
            if "INSTALL =" not in _content:
                continue
            _lines = []
            _changed = False
            for _line in _content.splitlines(True):
                _stripped = _line.lstrip()
                if _stripped.startswith("INSTALL = ") and "/install" in _stripped:
                    _indent = _line[:len(_line) - len(_stripped)]
                    _lines.append(f"{_indent}INSTALL = {shim_install}\n")
                    _changed = True
                else:
                    _lines.append(_line)
            if _changed:
                with open(_mp, "w", encoding="utf-8") as _f:
                    _f.write("".join(_lines))

    def package(self):
        env = ["conanbuild", "conanrun", "avahi_env"]
        shim = self._write_install_shim()
        self._redirect_install_to_shim(self.source_folder, shim)
        for subdir in ("avahi-common", "avahi-core"):
            self.run(f"make -C {subdir} install", cwd=self.source_folder, env=env)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Static by default: avahi-core depends on avahi-common, so the
        # dependent library follows so linkers resolve symbols left to right.
        self.cpp_info.libs = ["avahi-core", "avahi-common"]
        self.cpp_info.set_property("cmake_file_name", "avahi")
        self.cpp_info.set_property("cmake_target_name", "avahi::avahi")
        self.cpp_info.set_property("pkg_config_name", "avahi-core")
