#!/usr/bin/env python3
"""Conan recipe for libmcrypt 2.5.8."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmcryptConan(ConanFile):
    name = "libmcrypt"
    version = "2.5.8"
    description = "Thread-safe symmetric encryption algorithm library"
    license = "LGPL-2.1-or-later"
    homepage = "https://mcrypt.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libmcrypt requires a POSIX C target")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._remove_stale_configure_outputs()

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._libmcrypt_configure_args())
        if str(self.settings.os) == "OHOS":
            prefix = os.environ.get("DEFAULT_PREFIX", os.path.expanduser("~/usr/local"))
            for include_dir in (
                self.build_folder,
                os.path.join(self.build_folder, "include"),
                self.source_folder,
                os.path.join(self.source_folder, "include"),
                os.path.join(self.source_folder, "lib"),
                os.path.join(prefix, "include"),
            ):
                tc.extra_cflags.append(f"-I{include_dir}")
            tc.extra_ldflags.append(f"-L{os.path.join(prefix, 'lib')}")
        tc.generate()

        env = Environment()
        if str(self.settings.os) == "OHOS":
            prefix = os.environ.get("DEFAULT_PREFIX", os.path.expanduser("~/usr/local"))
            env.prepend_path("PATH", os.path.join(prefix, "bin"))
            for variable, tool in {
                "AR": "llvm-ar",
                "RANLIB": "llvm-ranlib",
                "NM": "llvm-nm",
                "LD": "ld.lld",
                "STRIP": "llvm-strip",
            }.items():
                tool_path = os.path.join(prefix, "bin", tool)
                if os.path.exists(tool_path):
                    env.define_path(variable, tool_path)
            sysroot = os.path.join(prefix, "sysroot")
            cc = self._compiler_command("c", os.path.join(prefix, "bin", "clang-15"))
            cxx = self._compiler_command("cpp", f"{os.path.join(prefix, 'bin', 'clang-15')} --driver-mode=g++")
            env.define("CPP", self._preprocessor_command(cc, sysroot))
            env.define("CXXCPP", self._preprocessor_command(cxx, sysroot))
            tmpdir = os.path.expanduser("~/tmp")
            os.makedirs(tmpdir, exist_ok=True)
            env.define_path("TMPDIR", tmpdir)
        env.vars(self).save_script("libmcrypt_deps")

    def build(self):
        self._patch_autotools_config_scripts()
        self._fix_autotools_umask()
        self._fix_autotools_helper_shells()
        if str(self.settings.os) == "OHOS":
            for folder in {self.source_folder, self.build_folder}:
                configure = os.path.join(folder, "configure")
                if os.path.exists(configure):
                    os.chmod(configure, 0o755)
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            self._configure_with_shell()
        else:
            autotools.configure()
        self._prepare_out_of_source_build_files()
        autotools.make(args=["-j1"])
        autotools.make(args=["-j1", "check"])

    def package(self):
        copy(self, "COPYING.LIB", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        if not self.options.shared:
            for root, _, files in os.walk(self.package_folder):
                for filename in files:
                    if filename.endswith((".so", ".so.4", ".so.4.4.8", ".dylib", ".dll")):
                        os.remove(os.path.join(root, filename))

    def package_info(self):
        self.cpp_info.libs = ["mcrypt"]
        self.cpp_info.set_property("cmake_file_name", "libmcrypt")
        self.cpp_info.set_property("cmake_target_name", "libmcrypt::libmcrypt")

    def _libmcrypt_configure_args(self):
        args = ["--prefix=/", "--disable-dynamic-loading"]
        if self.options.shared:
            args.extend(["--enable-shared", "--disable-static"])
        else:
            args.extend(["--disable-shared", "--enable-static"])
        return args

    def _autotools_configure_args(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._libmcrypt_configure_args())
        return tc.configure_args

    def _configure_with_shell(self):
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure):
            configure = os.path.join(self.build_folder, "configure")
        configure_args = shlex.join(self._autotools_configure_args())
        command = 'config_shell="${{CONFIG_SHELL:-${{SHELL:-sh}}}}"; CONFIG_SHELL="$config_shell" "$config_shell" {0} {1}'.format(
            shlex.quote(configure),
            configure_args,
        )
        self.run(command, cwd=self.build_folder, env=["conanbuild", "libmcrypt_deps"])

    def _remove_stale_configure_outputs(self):
        for filename in ("config.status", "config.cache", "config.log", "libtool"):
            path = os.path.join(self.source_folder, filename)
            if os.path.exists(path):
                os.remove(path)

    def _prepare_out_of_source_build_files(self):
        source = os.path.join(self.source_folder, "lib", "libmcrypt.sym")
        destination = os.path.join(self.build_folder, "lib", "libmcrypt.sym")
        if os.path.exists(source) and not os.path.exists(destination):
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.copy2(source, destination)
        if os.path.abspath(self.source_folder) != os.path.abspath(self.build_folder):
            self._prepare_mcrypt_symbol_sources()
            self._fix_mcrypt_symbol_makefile()
            self._fix_mcrypt_static_module_makefile()

    def _prepare_mcrypt_symbol_sources(self):
        target_root = os.path.join(self.build_folder, "lib", "mcrypt_symb_sources")
        for category in ("algorithms", "modes"):
            source_dir = os.path.join(self.source_folder, "modules", category)
            target_dir = os.path.join(target_root, category)
            if not os.path.isdir(source_dir):
                continue
            os.makedirs(target_dir, exist_ok=True)
            for filename in os.listdir(source_dir):
                if filename.endswith(".c"):
                    shutil.copy2(os.path.join(source_dir, filename), os.path.join(target_dir, filename))

        algorithm_dir = os.path.join(target_root, "algorithms")
        for target, source in {
            "threeway.c": "3-way.c",
            "safer-sk64.c": "safer64.c",
            "safer-sk128.c": "safer128.c",
        }.items():
            source_path = os.path.join(algorithm_dir, source)
            if os.path.exists(source_path):
                shutil.copy2(source_path, os.path.join(algorithm_dir, target))

    def _fix_mcrypt_symbol_makefile(self):
        makefile = os.path.join(self.build_folder, "lib", "Makefile")
        if not os.path.exists(makefile):
            return
        with open(makefile, "r", encoding="utf-8", errors="ignore") as handle:
            content = handle.read()
        fixed = content.replace(
            "../modules/algorithms/$$i.c",
            "mcrypt_symb_sources/algorithms/$$i.c",
        ).replace(
            "../modules/modes/$$i.c",
            "mcrypt_symb_sources/modes/$$i.c",
        )
        if fixed != content:
            with open(makefile, "w", encoding="utf-8") as handle:
                handle.write(fixed)

    def _fix_mcrypt_static_module_makefile(self):
        module_objects = []
        for category, variable in (
            ("modes", "NOINSTALL_MODE_MODULES"),
            ("algorithms", "NOINSTALL_ALGORITHM_MODULES"),
        ):
            makefile = os.path.join(self.build_folder, "modules", category, "Makefile")
            assignments = self._makefile_assignments(makefile)
            modules = assignments.get(variable) or assignments.get("noinst_LTLIBRARIES", "")
            for module in modules.split():
                if not module.endswith(".la"):
                    continue
                target = module[:-3]
                object_variable = "{}_la_OBJECTS".format(
                    "".join(character if character.isalnum() else "_" for character in target)
                )
                objects = self._expand_makefile_value(assignments.get(object_variable, ""), assignments)
                for obj in objects.split():
                    if obj.endswith(".lo"):
                        module_objects.append("../modules/{}/{}".format(category, obj))
        if not module_objects:
            return

        makefile = os.path.join(self.build_folder, "lib", "Makefile")
        with open(makefile, "r", encoding="utf-8", errors="ignore") as handle:
            lines = handle.readlines()
        replacement = "libmcrypt_la_LIBADD = {}\n".format(" ".join(module_objects))
        changed = False
        for index, line in enumerate(lines):
            if line.startswith("libmcrypt_la_LIBADD ="):
                lines[index] = replacement
                changed = True
                break
        if changed:
            with open(makefile, "w", encoding="utf-8") as handle:
                handle.writelines(lines)

    def _makefile_assignments(self, makefile):
        if not os.path.exists(makefile):
            return {}
        logical_lines = []
        pending = ""
        with open(makefile, "r", encoding="utf-8", errors="ignore") as handle:
            for raw_line in handle:
                line = raw_line.rstrip("\n")
                if line.endswith("\\"):
                    pending += line[:-1] + " "
                else:
                    logical_lines.append(pending + line)
                    pending = ""
        if pending:
            logical_lines.append(pending)

        assignments = {}
        for line in logical_lines:
            if "=" not in line or line.startswith(("\t", "#")):
                continue
            key, value = line.split("=", 1)
            assignments[key.strip()] = value.strip()
        return assignments

    def _expand_makefile_value(self, value, assignments):
        expanded = []
        for token in value.split():
            if token.startswith("$(") and token.endswith(")"):
                expanded.append(self._expand_makefile_value(assignments.get(token[2:-1], ""), assignments))
            else:
                expanded.append(token)
        return " ".join(part for part in expanded if part)

    def _compiler_command(self, language, fallback):
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        command = compilers.get(language) or fallback
        if isinstance(command, (list, tuple)):
            return " ".join(shlex.quote(str(part)) for part in command)
        return str(command)

    def _preprocessor_command(self, compiler, sysroot):
        parts = [compiler, "-E"]
        if os.path.isdir(sysroot):
            parts.append(f"--sysroot={shlex.quote(sysroot)}")
        parts.append("-D__MUSL__")
        return " ".join(parts)

    def _fix_autotools_helper_shells(self):
        if str(self.settings.os) != "OHOS":
            return
        shell = self._ohos_test_shell()
        for filename in ("install-sh", "depcomp", "missing", "mkinstalldirs"):
            path = os.path.join(self.source_folder, filename)
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                content = handle.read()
            fixed = self._replace_shell_shebang(content, shell)
            if fixed != content:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(fixed)
            os.chmod(path, 0o755)

    def _replace_shell_shebang(self, content, shell):
        for shebang in ("#! /bin/sh\n", "#!/bin/sh\n"):
            if content.startswith(shebang):
                return f"#!{shell}\n{content[len(shebang):]}"
        return content

    def _ohos_test_shell(self):
        home = os.path.expanduser("~")
        candidates = (
            os.path.join(home, "usr", "local", "bin", "bash"),
            os.path.join(home, "usr", "local", "bin", "zsh"),
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("bash"),
            shutil.which("zsh"),
            shutil.which("sh"),
            "/bin/sh",
        )
        for candidate in candidates:
            if candidate and os.path.isabs(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return "/bin/sh"

    def _patch_autotools_config_scripts(self):
        if str(self.settings.os) != "OHOS":
            return
        for root, _, files in os.walk(self.source_folder):
            if "config.guess" in files:
                path = os.path.join(root, "config.guess")
                self._prepend_after_shebang(path, """# Conan OHOS config.guess hook
machine=`(uname -m) 2>/dev/null || echo aarch64`
system=`(uname -s) 2>/dev/null || echo unknown`
case "$system" in
    HarmonyOS|OHOS)
        echo "${machine}-unknown-linux-ohos"
        exit 0
        ;;
esac
""")
            if "config.sub" in files:
                path = os.path.join(root, "config.sub")
                self._prepend_after_shebang(path, """# Conan OHOS config.sub hook
case "$1" in
    *-linux-ohos|*-unknown-linux-ohos)
        echo "$1"
        exit 0
        ;;
esac
""")

    def _prepend_after_shebang(self, path, snippet):
        marker = snippet.splitlines()[0]
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            content = handle.read()
        if marker in content:
            return
        lines = content.splitlines(True)
        if lines and lines[0].startswith("#!"):
            content = lines[0] + snippet + "".join(lines[1:])
        else:
            content = snippet + content
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.chmod(path, 0o755)

    def _fix_autotools_umask(self):
        if str(self.settings.os) != "OHOS":
            return
        for root, _, files in os.walk(self.source_folder):
            for filename in ("configure", "config.guess", "config.sub"):
                if filename not in files:
                    continue
                path = os.path.join(root, filename)
                with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                    content = handle.read()
                fixed = content.replace("umask 077", "umask 022")
                if fixed == content:
                    continue
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(fixed)
                os.chmod(path, 0o755)
