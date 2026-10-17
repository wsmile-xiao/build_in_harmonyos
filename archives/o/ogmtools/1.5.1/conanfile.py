#!/usr/bin/env python3
"""Conan recipe — ogmtools 1.5.1 (upstream 1.5, autotools, OGG media stream tools).

ogmtools 是命令行工具集（ogmmerge/ogmdemux/ogminfo/ogmsplit/ogmcat/dvdxchap），
无对外公开库 ABI（avilib 为 noinst 内部静态库）。构建产物为可执行文件 → R38 需 commands.json。

OHOS 适配要点（E126 变体，2026-09-03 实测）：
- HMDFS 上 `mktemp -d` 创建的目录属主不可写（mode 被文件系统改写，drwx--S---，
  而普通 mkdir 目录 drwxrws--x 可写）→ config.status 的 confstat* 临时目录
  Permission denied，Makefile 静默缺失。configure 自带 fallback（mkdir 路径）
  因 mktemp 返回 0 而不触发。对策：build() 注入本地 mktemp shim（转译 mkdir+随机名），
  仅作用于本包构建目录 PATH 前缀，不影响系统。
- XIPH_PATH_OGG/VORBIS 宏经 --with-*-prefix 定位依赖；AC_TRY_RUN 测试程序运行期
  需 LD_LIBRARY_PATH 可见依赖 .so（conan 依赖包 package_folder/lib）。
- make -j1：HMDFS 不支持 jobserver mkfifo（Operation not permitted）。
- 老版 install.sh 对绝对 DESTDIR 双重拼接，conan prefix 直装不受影响。
"""
from conan import ConanFile
from conan.tools.files import get, save, load, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import re
import shlex
import os

_MKTEMP_SHIM = r"""#!/bin/sh
# ogmtools recipe-local mktemp shim (HMDFS: mktemp -d 目录不可写, mkdir 目录可写)
wantdir=0
tpl=""
for a in "$@"; do
  case "$a" in
    -d) wantdir=1 ;;
    *) case "$a" in -*) ;; *) tpl="$a" ;; esac ;;
  esac
done
if [ "$wantdir" = "1" ]; then
  [ -n "$tpl" ] || tpl="./tmpdir.XXXXXX"
  d=$(dirname "$tpl"); b=$(basename "$tpl"); s=${b%%X*}
  i=0
  while [ $i -lt 16 ]; do
    if [ -n "$RANDOM" ]; then r="$RANDOM$RANDOM$RANDOM"
    else r="$$$(date +%s 2>/dev/null || echo 0)"; fi
    cand="$d/${s}${r}"
    if (umask 077; mkdir "$cand" 2>/dev/null); then echo "$cand"; exit 0; fi
    i=$((i+1))
  done
  echo "mktemp: cannot create temp dir in $d" >&2
  exit 1
fi
if [ -x /usr/bin/mktemp ]; then exec /usr/bin/mktemp "$@"; fi
echo "mktemp: unsupported mode" >&2
exit 1
"""


class OgmtoolsConan(ConanFile):
    # Windows-hosted cross builds must invoke POSIX configure/make through the
    # task's configured Bash subsystem instead of cmd.exe.
    win_bash = True
    name = "ogmtools"
    version = "1.5.1"
    description = "Tools for manipulating Ogg multimedia streams (OGM): merge, demux, split, cat, info"
    license = "GPL-2.0-or-later"
    homepage = "https://www.bunkus.org/videotools/ogmtools/"
    url = "https://github.com/mleeman/ogmtools"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libogg/1.3.6")
        self.requires("libvorbis/1.3.7")
        self.requires("libdvdread/7.1.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()
        if str(self.settings_build.os).startswith("Windows"):
            # Conan's generated shell file can contain native backslashes,
            # which w64devkit interprets as escapes.
            toolchain_env = os.path.join(
                self.generators_folder, "conanautotoolstoolchain.sh"
            )
            if os.path.isfile(toolchain_env):
                content = load(self, toolchain_env).replace("\\", "/")
                content = re.sub(
                    r'"/([A-Za-z])/',
                    lambda match: '"%s:/' % match.group(1).upper(),
                    content,
                )
                save(self, toolchain_env, content)

    @staticmethod
    def _shell_path(path):
        # w64devkit accepts drive-letter paths with forward slashes; mapping
        # them to /f-style MSYS paths would make the task root unreachable.
        return os.fspath(path).replace("\\", "/")

    def _run_w64devkit(self, command):
        """Run one build command in the task-configured POSIX subsystem."""
        bash = self.conf.get("tools.microsoft.bash:path", check_type=str)
        compiler = (self.conf.get("tools.build:compiler_executables", default={}) or {}).get("c")
        compiler_dir = os.path.dirname(os.path.abspath(os.fspath(compiler))) if compiler else ""
        make = self.conf.get("tools.gnu:make_program", check_type=str)
        path_dirs = []
        for directory in (compiler_dir, os.path.dirname(os.path.abspath(os.fspath(make))),
                          os.path.dirname(os.path.abspath(os.fspath(bash)))):
            normalized = self._shell_path(directory)
            if normalized and normalized not in path_dirs:
                path_dirs.append(normalized)
        shimdir = getattr(self, "_ohc_shimdir", "")
        if shimdir:
            path_dirs.insert(0, self._shell_path(shimdir))
        env_script = self._shell_path(os.path.join(
            self.generators_folder, "conanautotoolstoolchain.sh"
        ))
        command_script = os.path.join(self.build_folder, "ogmtools-w64devkit-command.sh")
        shell_wrapper = self._shell_path(os.path.join(self.build_folder, "ogmtools-shell.sh"))
        save(self, os.path.join(self.build_folder, "ogmtools-shell.sh"),
             "#!/usr/bin/env bash\nset -euo pipefail\nexec \"%s\" \"$@\"\n" % self._shell_path(bash))
        path_value = ":".join(path_dirs)
        script = (
            # Conan emits literal ${prefix} placeholders in configure args;
            # nounset would abort before configure can normalize them.
            "set -e\n"
            "cd %s\n" % shlex.quote(self._shell_path(self.source_folder))
            + ". %s\n" % shlex.quote(env_script)
            + "export PATH=%s:$PATH\n" % shlex.quote(path_value)
            + "export MAKE=%s\n" % shlex.quote(self._shell_path(make))
            + "export SHELL=%s\n" % shlex.quote(shell_wrapper)
            + "export CONFIG_SHELL=%s\n" % shlex.quote(shell_wrapper)
            + "export CPPFLAGS=%s\n" % shlex.quote(getattr(self, "_ogm_cppflags", ""))
            + "export LDFLAGS=%s\n" % shlex.quote(getattr(self, "_ogm_ldflags", ""))
            + command + "\n"
        )
        save(self, command_script, script)
        previous = self.win_bash
        self.win_bash = None
        try:
            return self.run(
                '"%s" "%s"' % (bash, self._shell_path(command_script)),
                env=None,
                cwd=self.source_folder,
            )
        finally:
            self.win_bash = previous

    def build(self):
        apply_conandata_patches(self)
        # 1) mktemp shim：HMDFS mktemp -d 目录不可写（E126 变体），PATH 前缀仅本包生效
        shimdir = os.path.join(self.build_folder, "_ohc_shim")
        os.makedirs(shimdir, exist_ok=True)
        self._ohc_shimdir = shimdir
        shim_path = os.path.join(shimdir, "mktemp")
        save(self, shim_path, _MKTEMP_SHIM)
        os.chmod(shim_path, 0o755)
        os.environ["PATH"] = shimdir + os.pathsep + os.environ.get("PATH", "")

        # 2) XIPH 宏与 AC_TRY_RUN 需要显式 prefix + 运行时库可见
        ogg_root = self.dependencies["libogg"].package_folder
        vorbis_root = self.dependencies["libvorbis"].package_folder
        dvdread_root = self.dependencies["libdvdread"].package_folder
        is_windows_build = str(self.settings_build.os).startswith("Windows")
        extra = [
            "--with-ogg-prefix=%s" % (self._shell_path(ogg_root) if is_windows_build else ogg_root),
            "--with-vorbis-prefix=%s" % (self._shell_path(vorbis_root) if is_windows_build else vorbis_root),
            "--with-dvdread-includes=%s" % ("/usr" if is_windows_build else dvdread_root),
            "--with-dvdread-libs=%s" % (self._shell_path(dvdread_root) if is_windows_build else dvdread_root),
        ]
        path_separator = ":" if str(self.settings_build.os).startswith("Windows") else os.pathsep
        deps_ld = path_separator.join(
            [f"{ogg_root}/lib", f"{vorbis_root}/lib", f"{dvdread_root}/lib"]
        )
        # CI 环境中 sqlite_runtime.sh 可能设置 LD_LIBRARY_PATH 指向 Python sqlite 运行时目录，
        # 该目录可能包含与系统冲突的库，导致 configure 的编译器测试程序无法运行
        # (configure: error: C compiler cannot create executables)。
        # 构建期间只用依赖库路径，不继承已有 LD_LIBRARY_PATH。
        os.environ["LD_LIBRARY_PATH"] = deps_ld

        # 4) CPPFLAGS/LDFLAGS：conan autotools 不自动注入依赖 cpp_info 目录（实测 conan-create.log
        #    编译行仅含 --with-*-prefix 宏自产路径）。vorbis/codec.h 内部 #include <ogg/ogg.h>，
        #    XIPH 测试程序需同时可见三库头；AM_PATH_LIBDVDREAD 需 -L。
        cpp_flags, ld_flags = [], []
        for dep in (self.dependencies["libogg"], self.dependencies["libvorbis"],
                    self.dependencies["libdvdread"]):
            agg = dep.cpp_info.aggregated_components()
            for d in agg.includedirs:
                p = d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
                cpp_flags.append(f"-I{self._shell_path(p) if str(self.settings_build.os).startswith('Windows') else p}")
            for d in agg.libdirs:
                p = d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
                ld_flags.append(f"-L{self._shell_path(p) if str(self.settings_build.os).startswith('Windows') else p}")
        os.environ["CPPFLAGS"] = " ".join(cpp_flags) + " " + os.environ.get("CPPFLAGS", "")
        os.environ["LDFLAGS"] = " ".join(ld_flags) + " " + os.environ.get("LDFLAGS", "")
        self._ogm_cppflags = os.environ["CPPFLAGS"]
        self._ogm_ldflags = os.environ["LDFLAGS"]

        # 5) Makefile.am 的 -Iavilib 是相对路径：out-of-tree 构建（conan basic_layout,
        #    CWD=build-release）下解析不到 srcdir/avilib/avilib.h，补绝对路径。
        avilib = os.path.join(self.source_folder, "avilib")
        os.environ["CPPFLAGS"] = f"{os.environ['CPPFLAGS']} -I{self._shell_path(avilib) if str(self.settings_build.os).startswith('Windows') else avilib}"

        autotools = Autotools(self)
        if is_windows_build:
            configure = self._shell_path(os.path.join(self.source_folder, "configure"))
            configure_args = autotools._configure_args + " " + " ".join(shlex.quote(arg) for arg in extra)
            # Autoconf's AC_CHECK_FILE refuses cross compilation; this cache
            # result is valid because the dependency header is in the W0 package.
            configure_args += " ac_cv_file__usr_include_dvdread_dvd_reader_h=yes"
            self._run_w64devkit('"%s" %s' % (configure, configure_args))
            # HMDFS does not support the GNU make jobserver FIFO.
            make = self.conf.get("tools.gnu:make_program", check_type=str)
            self._run_w64devkit('"%s" -j1' % self._shell_path(make))
        else:
            autotools.configure(args=extra)
            # 3) -j1：HMDFS 不支持 jobserver mkfifo
            autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        if str(self.settings_build.os).startswith("Windows"):
            make = self.conf.get("tools.gnu:make_program", check_type=str)
            destdir = self._shell_path(self.package_folder)
            self._run_w64devkit(
                '"%s" install INSTALL=install DESTDIR=%s'
                % (self._shell_path(make), shlex.quote(destdir))
            )
        else:
            autotools.install()

    def package_info(self):
        # 工具集：无公开库 ABI，仅声明 bindirs 供 CI L4/L5 产物检查
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
