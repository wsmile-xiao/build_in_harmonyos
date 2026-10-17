#!/usr/bin/env python3
"""Conan recipe for kbd-vlock 2.8.0.

The upstream tarball is kbd 2.8.0; this package builds only the vlock
application and its private libcommon helper.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class KbdVlockConan(ConanFile):
    name = "kbd-vlock"
    version = "2.8.0"
    description = "vlock virtual console locking tool from the Linux kbd project"
    license = "GPL-2.0-or-later"
    homepage = "https://kbd-project.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kbd-vlock supports Linux and OHOS, got {self.settings.os}"
            )

    def requirements(self):
        self.requires("linux-pam/1.7.2")

    def build_requirements(self):
        self.tool_requires("flex/2.6.4")
        self.tool_requires("bison/3.8.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-vlock",
            "--disable-libkeymap",
            "--disable-libkfont",
            "--disable-compress",
            "--disable-tests",
            "--disable-nls",
        ])
        if str(self.settings.os) == "OHOS":
            self._create_tool_wrappers()
            tc.extra_defines.append("KBD_VLOCK_DISABLE_VT_IOCTL")
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

        self._local_environment().vars(self).save_script("kbd_vlock_env")
        self._patch_generated_env_scripts()

    def build(self):
        apply_conandata_patches(self)
        self._patch_configure_status_tmp()
        old_umask = os.umask(0o022)
        try:
            with self._build_environment().apply():
                autotools = Autotools(self)
                autotools.configure()
                autotools.make(args=["-C", "src/libcommon", "-j1"])
                autotools.make(args=["-C", "src/vlock", "-j1"])
        finally:
            os.umask(old_umask)

    def package(self):
        old_umask = os.umask(0o022)
        try:
            with self._build_environment().apply():
                autotools = Autotools(self)
                autotools.install(args=["-C", "src/vlock", "-j1"])
        finally:
            os.umask(old_umask)

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.vlock", src=os.path.join(self.source_folder, "src", "vlock"),
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

        bin_path = os.path.join(self.package_folder, "bin", "vlock")
        if os.path.isfile(bin_path):
            os.chmod(bin_path, 0o755)
        if str(self.settings.os) == "OHOS" and os.path.isfile(bin_path):
            self._sign_elf(bin_path)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        pam = self.dependencies["linux-pam"]
        libdirs = pam.cpp_info.libdirs or ["lib"]
        libdir = libdirs[0]
        if not os.path.isabs(libdir):
            libdir = os.path.join(pam.package_folder, libdir)
        self.runenv_info.append_path("LD_LIBRARY_PATH", libdir)

    def _build_environment(self):
        env = AutotoolsToolchain(self).environment()
        env.compose_env(VirtualBuildEnv(self).vars())
        env.compose_env(AutotoolsDeps(self).vars())
        env.compose_env(self._local_environment())
        return env.vars(self)

    def _patch_configure_status_tmp(self):
        if str(self.settings.os) != "OHOS":
            return
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            return

        with open(configure, "r", encoding="utf-8") as handle:
            content = handle.read()

        replacements = {
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&':
                'tmp=`(umask 022 && mktemp -d "${TMPDIR:-.}/confXXXXXX") 2>/dev/null` &&',
            'tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")':
                'tmp="${TMPDIR:-.}"/conf$$-$RANDOM\n  (umask 022 && mkdir -p "$tmp")',
            '"cannot create a temporary directory in ."':
                '"cannot create a temporary directory"',
        }
        changed = False
        for old, new in replacements.items():
            if old in content:
                content = content.replace(old, new)
                changed = True

        if changed:
            with open(configure, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            os.chmod(configure, 0o755)

    def _local_environment(self):
        env = Environment()
        shell = self._config_shell()
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)
        if str(self.settings.os) == "OHOS":
            tmpdir = self._ohos_tmpdir()
            include_dir, lib_dir = self._pam_paths()
            cflags = f"-I{include_dir}"
            lib_prefix = f"-L{lib_dir}"
            wrapper = os.path.join(self._wrapper_dir(), "pkg-config")
            cc = self._compiler_executable("c", "clang")
            cxx = self._compiler_executable("cpp", "clang++")
            env.define("TMPDIR", tmpdir)
            env.define("TMPPREFIX", os.path.join(tmpdir, "kbd-vlock-tmp-"))
            env.define("CC", cc)
            env.define("CXX", cxx)
            env.define("LD", self._tool_executable("ld.lld", "lld", "ld"))
            env.define("AR", self._tool_executable("llvm-ar", "ar"))
            env.define("RANLIB", self._tool_executable("llvm-ranlib", "ranlib"))
            env.define("NM", self._tool_executable("llvm-nm", "nm"))
            env.define("STRIP", self._tool_executable("llvm-strip", "strip"))
            env.define("PKG_CONFIG", f"{shell} {wrapper}")
            env.define("PAM_CFLAGS", cflags)
            env.define("PAM_MISC_CFLAGS", cflags)
            env.define("PAM_LIBS", f"{lib_prefix} -lpam -ldl")
            env.define("PAM_MISC_LIBS", f"{lib_prefix} -lpam_misc")
            env.prepend_path("LD_LIBRARY_PATH", lib_dir)
            env.prepend_path("PATH", self._wrapper_dir())
            for directory in (
                "/data/service/hnp/bin",
                "/storage/Users/currentUser/usr/local/bin",
                "/system/bin",
                "/usr/bin",
                "/bin",
            ):
                env.prepend_path("PATH", directory)
        return env

    def _ohos_tmpdir(self):
        configured = os.environ.get("TMPDIR")
        if configured and os.path.abspath(configured) != "/tmp":
            tmpdir = configured
        else:
            tmpdir = os.path.join(self.generators_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        return tmpdir

    def _config_shell(self):
        configured = os.environ.get("CONFIG_SHELL")
        if str(self.settings.os) == "OHOS":
            shell = self._find_executable(
                configured,
                "/system/bin/sh",
                "/bin/sh",
                shutil.which("sh"),
                "sh",
            )
            return shell or "/system/bin/sh"

        shell = self._find_executable(
            configured,
            shutil.which("bash"),
            shutil.which("sh"),
            "/bin/sh",
            "sh",
        )
        return shell or configured or "sh"

    @staticmethod
    def _find_executable(*candidates):
        for candidate in candidates:
            if not candidate:
                continue
            path = shutil.which(candidate) if not os.path.isabs(candidate) else candidate
            if path and os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        return None

    def _wrapper_dir(self):
        return os.path.join(self.generators_folder, "kbd-vlock-tools")

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured:
            configured_path = str(configured).split()[0].strip("\"'")
            if os.path.isfile(configured_path) and os.access(configured_path, os.X_OK):
                return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _tool_executable(self, *names):
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return names[0]

    def _pam_paths(self):
        pam = self.dependencies["linux-pam"]
        include_dirs = pam.cpp_info.includedirs or ["include"]
        lib_dirs = pam.cpp_info.libdirs or ["lib"]
        include_dir = include_dirs[0]
        lib_dir = lib_dirs[0]
        if not os.path.isabs(include_dir):
            include_dir = os.path.join(pam.package_folder, include_dir)
        if not os.path.isabs(lib_dir):
            lib_dir = os.path.join(pam.package_folder, lib_dir)
        return include_dir, lib_dir

    def _create_tool_wrappers(self):
        include_dir, lib_dir = self._pam_paths()
        os.makedirs(self._wrapper_dir(), exist_ok=True)
        script = os.path.join(self._wrapper_dir(), "pkg-config")
        content = f"""#!/system/bin/sh
case " $* " in
  *" --version "*|*" --modversion "*) echo 0.29.2; exit 0 ;;
  *" --atleast-pkgconfig-version "*) exit 0 ;;
esac

for arg in "$@"; do
  case "$arg" in
    pam|pam_misc|--exists|--print-errors|--short-errors|--cflags|--libs) ;;
    *) ;;
  esac
done

case " $* " in
  *" --exists "*) exit 0 ;;
esac

out=
case " $* " in
  *" --cflags "*) out="$out -I{include_dir}" ;;
esac
case " $* " in
  *" --libs "*)
    case " $* " in
      *" pam_misc "*) out="$out -L{lib_dir} -lpam_misc" ;;
      *" pam "*) out="$out -L{lib_dir} -lpam -ldl" ;;
      *) out="$out -L{lib_dir} -lpam -lpam_misc -ldl" ;;
    esac
    ;;
esac

if [ -n "$out" ]; then
  echo "$out"
fi
exit 0
"""
        with open(script, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.chmod(script, 0o755)
        prefixed = os.path.join(self._wrapper_dir(), "aarch64-unknown-linux-ohos-pkg-config")
        with open(prefixed, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.chmod(prefixed, 0o755)
        self._create_flex_wrapper()

    def _create_flex_wrapper(self):
        content = """#!/system/bin/sh
case " $* " in
  *" --version "*) echo "flex 2.6.4"; exit 0 ;;
esac
if [ "${1:-}" = "conftest.l" ]; then
  cat > lex.yy.c <<'EOF'
#ifdef YYTEXT_POINTER
char *yytext;
#else
char yytext[1];
#endif
int yylex(void) { return 0; }
int yywrap(void) { return 1; }
int main(void) { return !yylex(); }
EOF
  exit 0
fi
echo "kbd-vlock does not run flex for the selected component-only build" >&2
exit 1
"""
        for name in ("flex", "lex"):
            script = os.path.join(self._wrapper_dir(), name)
            with open(script, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            os.chmod(script, 0o755)

    def _patch_generated_env_scripts(self):
        if str(self.settings.os) != "OHOS":
            return
        marker = "# kbd-vlock OHOS PATH bootstrap"
        bootstrap = f"""{marker}
for d in /bin /usr/bin /system/bin /storage/Users/currentUser/usr/local/bin /data/service/hnp/bin {self._wrapper_dir()}; do
    case ":${{PATH:-}}:" in
        *":$d:"*) ;;
        *) PATH="$d${{PATH:+:$PATH}}" ;;
    esac
done
export PATH
"""
        for filename in os.listdir(self.generators_folder):
            if not filename.endswith(".sh"):
                continue
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
            if marker in content:
                continue
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(bootstrap + content)

    def _sign_elf(self, path):
        objcopy = self._find_tool("llvm-objcopy")
        signer = self._find_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException("OHOS ELF signing tools are unavailable")
        self.run(f'"{objcopy}" --remove-section .codesign "{path}"', ignore_errors=True)
        signed = path + ".signed"
        self.run(
            f'"{signer}" sign -inFile "{path}" -outFile "{signed}" -selfSign 1'
        )
        os.replace(signed, path)
        os.chmod(path, 0o755)

    @staticmethod
    def _find_tool(command):
        for directory in (
            os.environ.get("SIGN_TOOL_PATH"),
            "/data/service/hnp/bin",
            "/storage/Users/currentUser/usr/local/bin",
        ):
            if not directory:
                continue
            candidate = os.path.join(directory, command)
            if os.path.isfile(candidate):
                return candidate
        return shutil.which(command)
