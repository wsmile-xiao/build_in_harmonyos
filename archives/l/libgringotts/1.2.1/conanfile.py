#!/usr/bin/env python3
"""Conan recipe for libgringotts 1.2.1 (HarmonyOS PC aarch64 adaptation)."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibgringottsConan(ConanFile):
    name = "libgringotts"
    version = "1.2.1"
    description = "Thread-safe C library that encapsulates data in an encrypted and compressed file"
    license = "GPL-2.0-or-later"
    homepage = "https://directory.fsf.org/wiki/LibGringotts"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libgringotts requires a POSIX C target")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("libmcrypt/2.5.8")
        self.requires("mhash/0.9.9.9")
        self.requires("zlib/1.3.1")
        self.requires("bzip2/1.0.8")

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
            for include_dir in (
                self.build_folder,
                os.path.join(self.build_folder, "include"),
                self.source_folder,
                os.path.join(self.source_folder, "include"),
                os.path.join(prefix, "include"),
            ):
                tc.extra_cflags.append(f"-I{include_dir}")
            tc.extra_ldflags.append(f"-L{os.path.join(prefix, 'lib')}")
        # All custom env vars are injected into the AutotoolsToolchain environment
        # so they land in conanautotoolstoolchain.sh (reliably applied by conanbuild).
        env = tc.environment()
        if str(self.settings.os) == "OHOS":
            prefix = os.environ.get("DEFAULT_PREFIX", os.path.expanduser("~/usr/local"))
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
            cxx = self._compiler_command(
                "cpp", f"{os.path.join(prefix, 'bin', 'clang-15')} --driver-mode=g++"
            )
            env.define("CPP", self._preprocessor_command(cc, sysroot))
            env.define("CXXCPP", self._preprocessor_command(cxx, sysroot))
            tmpdir = os.path.expanduser("~/tmp")
            os.makedirs(tmpdir, exist_ok=True)
            env.define_path("TMPDIR", tmpdir)
        tc.generate(env=env)

        # AutotoolsDeps injects every dependency's include/lib/-l flags into the
        # build environment. Without it, AutotoolsToolchain alone does NOT add
        # dependency cpp_info, so configure cannot locate libbz2/libmhash/etc.
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        self._patch_autotools_config_scripts()
        self._fix_autotools_umask()
        self._fix_autotools_helper_shells()
        self._patch_libmcrypt_config_check()
        if str(self.settings.os) == "OHOS":
            for folder in {self.source_folder, self.build_folder}:
                configure = os.path.join(folder, "configure")
                if os.path.exists(configure):
                    os.chmod(configure, 0o755)

        tc = AutotoolsToolchain(self)
        configure_args = list(tc.configure_args)
        configure_args += self._configure_args_list()
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure):
            configure = os.path.join(self.build_folder, "configure")
        shell = self._ohos_test_shell() if str(self.settings.os) == "OHOS" else "sh"
        configure_cmd = (
            f'CONFIG_SHELL="$config_shell" "$config_shell" '
            f'{shlex.quote(configure)} {shlex.join(configure_args)}'
        ).replace("$config_shell", shell)
        self._run_logged(configure_cmd, self.build_folder, "configure.log")
        self._run_logged("make -j1", self.build_folder, "make.log")
        self._run_logged(
            f'make install DESTDIR="{self.package_folder}"',
            self.build_folder,
            "install.log",
        )

    def _patch_libmcrypt_config_check(self):
        """Bypass the upstream `libmcrypt-config` binary gate in configure.

        The conan libmcrypt package does not ship a `libmcrypt-config` script,
        and injecting one via PATH is unreliable under the OHOS profile's env
        activation. AutotoolsDeps already injects libmcrypt's include/lib/-l
        flags into CPPFLAGS/LDFLAGS/LIBS, so we make the check always pass and
        derive MCRYPT_CFLAGS/MCRYPT_LIBS from the environment conan provides.
        """
        if str(self.settings.os) != "OHOS":
            return
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure):
            return
        with open(configure, "r", encoding="utf-8", errors="ignore") as handle:
            content = handle.read()
        orig = content
        content = content.replace(
            "if libmcrypt-config --libs > /dev/null 2>&1", "if true"
        )
        content = content.replace(
            "MCRYPT_CFLAGS=`libmcrypt-config --cflags`", 'MCRYPT_CFLAGS="$CPPFLAGS"'
        )
        content = content.replace(
            "MCRYPT_LIBS=`libmcrypt-config --libs`", 'MCRYPT_LIBS="-lmcrypt"'
        )
        content = content.replace(
            "MCRYPT_CFLAGS=$(libmcrypt-config --cflags)", 'MCRYPT_CFLAGS="$CPPFLAGS"'
        )
        content = content.replace(
            "MCRYPT_LIBS=$(libmcrypt-config --libs)", 'MCRYPT_LIBS="-lmcrypt"'
        )
        if content != orig:
            with open(configure, "w", encoding="utf-8") as handle:
                handle.write(content)

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if not self.options.shared:
            for root, _, files in os.walk(self.package_folder):
                for filename in files:
                    if filename.endswith((".so", ".so.2", ".so.2.0.0", ".dylib", ".dll")):
                        os.remove(os.path.join(root, filename))

    def package_info(self):
        self.cpp_info.libs = ["gringotts"]
        self.cpp_info.set_property("cmake_file_name", "libgringotts")
        self.cpp_info.set_property("cmake_target_name", "libgringotts::libgringotts")
        self.cpp_info.set_property("pkg_config_name", "libgringotts")

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _configure_args_list(self):
        args = ["--prefix=/"]
        if self.options.shared:
            args.extend(["--enable-shared", "--disable-static"])
        else:
            args.extend(["--disable-shared", "--enable-static"])
        return args

    def _run_logged(self, cmd, cwd, log_name):
        log = os.path.join(self.build_folder, log_name)
        rcfile = log + ".rc"
        full = f'( {cmd} ) > "{log}" 2>&1; echo $? > "{rcfile}"'
        self.run(full, cwd=cwd, env=["conanbuild"])
        with open(rcfile, "r", errors="ignore") as handle:
            rc = int(handle.read().strip() or "1")
        if rc != 0:
            with open(log, "r", errors="ignore") as handle:
                tail = "".join(handle.readlines()[-50:])
            raise ConanException(
                f"Command failed (rc={rc}): {cmd}\n--- tail of {log} ---\n{tail}"
            )

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

    def _remove_stale_configure_outputs(self):
        for filename in ("config.status", "config.cache", "config.log", "libtool"):
            path = os.path.join(self.source_folder, filename)
            if os.path.exists(path):
                os.remove(path)

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
