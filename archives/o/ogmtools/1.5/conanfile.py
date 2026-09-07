#!/usr/bin/env python3
"""Conan recipe — ogmtools 1.5 (autotools, OGG media stream tools).

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
from conan.tools.files import get, save, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
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
    name = "ogmtools"
    version = "1.5"
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

    def build(self):
        apply_conandata_patches(self)
        # 1) mktemp shim：HMDFS mktemp -d 目录不可写（E126 变体），PATH 前缀仅本包生效
        shimdir = os.path.join(self.build_folder, "_ohc_shim")
        os.makedirs(shimdir, exist_ok=True)
        shim_path = os.path.join(shimdir, "mktemp")
        save(self, shim_path, _MKTEMP_SHIM)
        os.chmod(shim_path, 0o755)
        os.environ["PATH"] = shimdir + os.pathsep + os.environ.get("PATH", "")

        # 2) XIPH 宏与 AC_TRY_RUN 需要显式 prefix + 运行时库可见
        ogg_root = self.dependencies["libogg"].package_folder
        vorbis_root = self.dependencies["libvorbis"].package_folder
        dvdread_root = self.dependencies["libdvdread"].package_folder
        extra = [
            f"--with-ogg-prefix={ogg_root}",
            f"--with-vorbis-prefix={vorbis_root}",
            f"--with-dvdread-prefix={dvdread_root}",
        ]
        deps_ld = os.pathsep.join(
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
                cpp_flags.append(f"-I{p}")
            for d in agg.libdirs:
                p = d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
                ld_flags.append(f"-L{p}")
        os.environ["CPPFLAGS"] = " ".join(cpp_flags) + " " + os.environ.get("CPPFLAGS", "")
        os.environ["LDFLAGS"] = " ".join(ld_flags) + " " + os.environ.get("LDFLAGS", "")

        # 5) Makefile.am 的 -Iavilib 是相对路径：out-of-tree 构建（conan basic_layout,
        #    CWD=build-release）下解析不到 srcdir/avilib/avilib.h，补绝对路径。
        os.environ["CPPFLAGS"] = f"{os.environ['CPPFLAGS']} -I{os.path.join(self.source_folder, 'avilib')}"

        autotools = Autotools(self)
        autotools.configure(args=extra)
        # 3) -j1：HMDFS 不支持 jobserver mkfifo
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 工具集：无公开库 ABI，仅声明 bindirs 供 CI L4/L5 产物检查
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
