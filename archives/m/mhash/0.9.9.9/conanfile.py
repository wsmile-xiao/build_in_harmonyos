#!/usr/bin/env python3
"""Conan recipe for mhash 0.9.9.9."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MhashConan(ConanFile):
    name = "mhash"
    version = "0.9.9.9"
    description = "Hash algorithm and key generation library"
    license = "LGPL-2.0-or-later"
    homepage = "https://mhash.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mhash requires a POSIX C target")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._remove_stale_configure_outputs()

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=/")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        if str(self.settings.os) == "OHOS":
            prefix = os.environ.get("DEFAULT_PREFIX", os.path.expanduser("~/usr/local"))
            tc.extra_cflags.append(f"-I{os.path.join(self.build_folder, 'include')}")
            tc.extra_cflags.append(f"-I{os.path.join(self.source_folder, 'include')}")
            tc.extra_cflags.append(f"-I{os.path.join(prefix, 'include')}")
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
        env.vars(self).save_script("mhash_deps")

    def build(self):
        apply_conandata_patches(self)
        self._patch_autotools_config_scripts()
        self._fix_autotools_umask()
        self._fix_autotools_helper_shells()
        self._fix_test_shell()
        if str(self.settings.os) == "OHOS":
            for folder in {self.source_folder, self.build_folder}:
                configure = os.path.join(folder, "configure")
                if os.path.exists(configure):
                    os.chmod(configure, 0o755)
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            self._configure_with_shell(autotools)
        else:
            autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(args=["-j1", "check"])

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        if not self.options.shared:
            for root, _, files in os.walk(self.package_folder):
                for filename in files:
                    if filename.endswith((".so", ".so.0", ".so.0.8.18", ".dylib", ".dll")):
                        os.remove(os.path.join(root, filename))

    def package_info(self):
        self.cpp_info.libs = ["mhash"]
        self.cpp_info.set_property("cmake_file_name", "mhash")
        self.cpp_info.set_property("cmake_target_name", "mhash::mhash")

    def _configure_with_shell(self, autotools):
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure):
            configure = os.path.join(self.build_folder, "configure")
        configure_args = getattr(autotools, "_configure_args", "") or ""
        command = 'config_shell="${{CONFIG_SHELL:-${{SHELL:-sh}}}}"; CONFIG_SHELL="$config_shell" "$config_shell" {0} {1}'.format(
            shlex.quote(configure),
            configure_args,
        )
        self.run(command, cwd=self.build_folder, env=["conanbuild", "mhash_deps"])

    def _remove_stale_configure_outputs(self):
        for filename in ("config.status", "config.cache", "config.log", "libtool"):
            path = os.path.join(self.source_folder, filename)
            if os.path.exists(path):
                os.remove(path)

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

    def _fix_test_shell(self):
        if str(self.settings.os) != "OHOS":
            return
        shell = self._ohos_test_shell()
        path = os.path.join(self.source_folder, "src", "hash_test.sh")
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            content = handle.read()
        fixed = self._replace_shell_shebang(content, shell)
        python = shutil.which("python3") or shutil.which("python") or "python3"
        million_a = f"{shlex.quote(python)} -c 'import sys; sys.stdout.write(\"a\" * 1000000)'"
        fixed = fixed.replace("perl -e 'print \"a\"x1000000'", million_a)
        if fixed != content:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(fixed)
        os.chmod(path, 0o755)

    def _fix_autotools_helper_shells(self):
        if str(self.settings.os) != "OHOS":
            return
        shell = self._ohos_test_shell()
        for filename in ("install-sh", "depcomp", "missing"):
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
