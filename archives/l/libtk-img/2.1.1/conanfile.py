#!/usr/bin/env python3
"""Conan recipe for libtk-img 2.1.1 (上游工程名 TkImg，发行包 Img-<ver>.tar.gz)。

Img 是 Tcl/Tk 的图像格式扩展，用 TEA（Tcl Extension Architecture）autotools 构建。
产物是**一组 Tcl 可 load 的动态库**（`libtcl9tkimg<fmt>2.1.1.so` 等），装在运行期目录
`<prefix>/lib/Img2.1.1/`，由合并后的 `pkgIndex.tcl` 暴露 `package require Img`
与 `img::<fmt>`。包内 `compat/` 自带 zlib/libpng/libtiff/libjpeg 源码，随包编译后
静态并入各格式处理器 —— 因此外部依赖只有 tcl + tk + X11 一族。

OHOS 适配要点（全部实测，见 archives/l/libtk-img/2.1.1/notes.md）：

1. **uname shim** —— `uname -s` 在 OHOS 返回 `HarmonyOS`，`compat/libtiff` 与
   `compat/libjpeg` 自带的 `config.guess` 不识别 → `cannot guess build type`，
   导致 `tif_config.h` / `tiffconf.h` / `jconfig.h` 不生成 → 编译报
   `fatal error: 'tif_config.h' file not found`。前置 shim 让 `-s` 报 `Linux`、
   `-r` 报 `6.6`、`-m` 报 `aarch64`（与仓库内 tcl/tk 配方同款手法）。
2. **`tcl_cv_sys_version=Linux-6.6` + `ac_cv_prog_cc_works=yes`** —— TEA 的
   `SHLIB_LD` 探测需要，否则生成错误的共享库链接命令。
3. **`umask 077` → `umask 022`（E011）** —— HMDFS 拒绝 0600 临时目录。
4. **只用 `AutotoolsToolchain`，不用 `AutotoolsDeps`** —— 后者会把
   `LIBS=-ltcl9tk9.0 -ltcl9.0 …` 注入每个 conftest 的链接命令，宿主上直接
   `configure: error: cannot run C compiled programs`（conftest 加载 libtcl 失败）。
5. **`tkConfig.sh` 发行内容不可直接用** —— 它带
   `TK_LIB_SPEC='-L//lib -ltcl9tk9.0'`、`TK_STUB_LIB_SPEC='-L//lib -ltkstub'`、
   `TK_INCLUDE_SPEC='-I//include'`，而 tclConfig.sh 带 `TCL_PREFIX='${TCL_ROOT}'`
   → `ld.lld: unable to find library -ltclstub / -ltkstub`。须改写生成的 Makefile。
6. **X11** —— `TEA_PATH_X` 在本平台找不到 X11，退化为裸 `-lX11`，须补
   `-L<libx11包>/lib`；且链接进 `libX11.so.6` 后运行期还需要 `libxcb.so.1`
   （→ 依赖 libx11，它会带来 libxcb/libxau/libxdmcp）。
7. **`X11/Xproto.h`** —— `window/window.c` 直接 `#include "X11/Xproto.h"`，
   该头既不在 libx11 包也不在 tk 包里 → 依赖 header-library `xorgproto`
   并把它的 `include` 加进 `CPPFLAGS`。
8. **上游测试** —— `tests/all.tcl`（tcltest）真实执行；`tclsh9.0` 来自 tcl 包。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, replace_in_file,
                               save)
from conan.tools.gnu import Autotools, AutotoolsToolchain

# 顶层 configure.ac 里 TEA_CONFIG_SUBDIR 声明的**全部**子目录，顺序即构建顺序。
# compat 的四个库在最前（其余处理器静态链接它们）。
SUBDIRS = (
    "zlib", "libpng", "libtiff", "libjpeg",
    "base", "bmp", "gif", "ico", "jpeg", "pcx", "pixmap", "png", "ppm",
    "ps", "sgi", "sun", "tga", "tiff", "window", "xbm", "xpm",
    "dted", "raw", "flir",
)

# 无缓冲包装器：OHOS 上重定向到文件时 stdio 是块缓冲，若解释器在退出路径被环境
# 问题拖住而外层 timeout 强杀，块缓冲中的结果会丢；同时强制 tcltest 逐用例输出。
_UNBUFFERED_RUNNER = """\
# 由 libtk-img conanfile.py 生成 —— 上游测试无缓冲包装器。
fconfigure stdout -buffering none
fconfigure stderr -buffering none
set _script [lindex $argv 0]
set argv [concat [lrange $argv 1 end] [list -verbose "pass skip fail error"]]
source $_script
"""


def _find_first(folder, name):
    """在 folder 下按名查找文件，返回其所在目录（找不到返回 None）。"""
    for root, _dirs, files in os.walk(folder):
        if name in files:
            return root
    return None


class LibtkImgConan(ConanFile):
    name = "libtk-img"
    version = "2.1.1"
    package_type = "shared-library"
    license = "BSD-2-Clause"
    homepage = "https://sourceforge.net/projects/tkimg/"
    description = ("Img (TkImg) — Tcl/Tk image format extension: BMP/GIF/ICO/JPEG/"
                   "PCX/PNG/PPM/PS/SGI/SUN/TGA/TIFF/XBM/XPM/DTED/RAW/FLIR handlers")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    # ------------------------------------------------------------------ 校验
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libtk-img 目前只适配 Linux / OHOS，收到 os={self.settings.os}")

    # ---------------------------------------------------------------- 依赖
    def requirements(self):
        # tk 自动带 tcl；两个包都提供 tclConfig.sh / tkConfig.sh（TEA 必需）
        self.requires("tk/9.0.3.2")
        # window / xpm 处理器链接 -lX11；运行期还需 libxcb（libx11 的传递依赖）
        self.requires("libx11/1.8.13")
        # window/window.c 需要 X11/Xproto.h —— 只有 xorgproto 提供（header-library）
        self.requires("xorgproto/2025.1")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------- 关键路径小工具
    @property
    def _stage_dir(self):
        """install-libraries 的 INSTALL_ROOT —— 在 build_folder 内做一次完整安装，
        供上游测试（需要可 `package require Img` 的 pkgIndex.tcl）与 package() 使用。"""
        return os.path.join(self.build_folder, "_stage")

    def _dep(self, name):
        try:
            return self.dependencies[name].package_folder
        except Exception:
            return None

    @property
    def _img_runtime_dir(self):
        """TEA 的 `LIB_RUNTIME_DIR = $(libdir)/$(PACKAGE_NAME)$(PACKAGE_VERSION)`，
        配合 `--prefix=/`（conan 默认）即 `<INSTALL_ROOT>/lib/Img2.1.1`。"""
        return os.path.join(self._stage_dir, "lib", "Img%s" % self.version)

    def _x11_runtime_lib_dirs(self):
        dirs = []
        for dep in ("tcl", "tk", "libx11", "libxcb", "libxau", "libxdmcp"):
            folder = self._dep(dep)
            if not folder:
                continue
            lib = os.path.join(folder, "lib")
            if os.path.isdir(lib) and lib not in dirs:
                dirs.append(lib)
        return dirs

    # ------------------------------------------------------------ generate
    def generate(self):
        tc = AutotoolsToolchain(self)
        # TEA configure 通过 --with-tcl/--with-tk 探测 tclConfig.sh / tkConfig.sh
        tcl_lib = _find_first(self._dep("tcl"), "tclConfig.sh")
        tk_lib = _find_first(self._dep("tk"), "tkConfig.sh")
        if not tcl_lib:
            raise ConanException("未在 tcl 包中找到 tclConfig.sh")
        if not tk_lib:
            raise ConanException("未在 tk 包中找到 tkConfig.sh")
        tc.configure_args.append(f"--with-tcl={tcl_lib}")
        tc.configure_args.append(f"--with-tk={tk_lib}")
        # 见模块 docstring 第 2 点
        tc.configure_args.append("tcl_cv_sys_version=Linux-6.6")
        tc.configure_args.append("ac_cv_prog_cc_works=yes")
        tc.generate()

    # --------------------------------------------------------------- build
    def build(self):
        apply_conandata_patches(self)
        self._drop_umask_077()
        self._install_uname_shim()
        self._stub_vendored_config_guess()

        autotools = Autotools(self)
        autotools.configure()
        self._fix_generated_makefiles()
        # 顶层 all: 递归（`for sub in $(SUBDIRS); do cd $sub && make all; done`）
        # 在本平台实测可用 —— 前提是 configure 已完整跑完（子目录 Makefile 齐备）。
        autotools.make()
        self._install_libraries()
        self._run_upstream_tests()

    def _drop_umask_077(self):
        """E011：HMDFS 拒绝 0600 临时目录，configure 内的 `umask 077` 改为 022。

        用 Conan 官方 `replace_in_file` 做文本替换（仓库内 445 个 recipe 同款惯用法），
        而非手写 open/read/write。这是一处 **build() 内的运行时修复**：G0
        clean-verify 只跑裸 `./configure`、不执行 `build()`，因此无法复现它
        —— `clean_verify.py` 正是据此把本类 recipe 的 configure 失败判为「预期行为」。
        """
        n = 0
        for cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"),
                             recursive=True):
            try:
                with open(cfg, encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                replace_in_file(self, cfg, "umask 077", "umask 022",
                                strict=False, encoding="utf-8")
                n += 1
        self.output.info(f"umask 077→022：改写 {n} 个 configure")

    def _install_uname_shim(self):
        """见模块 docstring 第 1 点：让 config.guess 认出 OHOS 宿主。"""
        shim = os.path.join(self.build_folder, "_uname_shim")
        os.makedirs(shim, exist_ok=True)
        uname = os.path.join(shim, "uname")
        save(self, uname,
             '#!/bin/sh\n'
             'case "${1:-}" in\n'
             '  -s|"") echo Linux ;;\n'
             '  -r) echo 6.6 ;;\n'
             '  -m) echo aarch64 ;;\n'
             '  *) exec /system/bin/uname "$@" 2>/dev/null '
             '|| exec /bin/uname "$@" ;;\n'
             'esac\n')
        os.chmod(uname, 0o755)
        os.environ["PATH"] = shim + os.pathsep + os.environ.get("PATH", "")
        self.output.info(f"uname shim 已注入 PATH 头部: {shim}")

    def _stub_vendored_config_guess(self):
        """把 `compat/**` 里 vendored 的 `config.guess` 换成固定输出的桩。

        见模块 docstring 第 1 点。为什么不能只靠 uname shim：conan 的
        `conanbuild.sh` 会把 profile 的 buildenv PATH（`usr/local/bin`、hnp `bin`）
        前置到脚本内 PATH，可能盖住 build() 里注入的 shim；vendored
        `config.guess` 一旦拿到 `HarmonyOS` 就报 `cannot guess build type`。
        桩化后结果确定：`aarch64-unknown-linux-gnu`（与 shim 生效时一致，
        且四个 config.sub 都认这个三元组）。
        """
        n = 0
        for cg in glob.glob(os.path.join(self.source_folder, "compat", "**",
                                         "config.guess"), recursive=True):
            save(self, cg, "#!/bin/sh\necho aarch64-unknown-linux-gnu\n")
            os.chmod(cg, 0o755)
            n += 1
        self.output.info(f"compat/**/config.guess 桩替换: {n} 个 → aarch64-unknown-linux-gnu")

    def _fix_generated_makefiles(self):
        """见模块 docstring 第 5、6、7 点。三处路径改写 + CPPFLAGS 注入 X11 协议头。"""
        tcl_lib = os.path.join(self._dep("tcl"), "lib")
        tk_lib = os.path.join(self._dep("tk"), "lib")
        x11_lib = os.path.join(self._dep("libx11"), "lib")
        xproto_inc = os.path.join(self._dep("xorgproto"), "include")

        n = 0
        for mk in glob.glob(os.path.join(self.build_folder, "**", "Makefile"),
                            recursive=True):
            try:
                with open(mk, encoding="utf-8", errors="replace") as f:
                    data = f.read()
            except OSError:
                continue
            new = data
            new = new.replace("-L${TCL_ROOT}/lib", f"-L{tcl_lib}")
            new = new.replace("-L//lib", f"-L{tk_lib}")
            if f"-L{x11_lib} -lX11" not in new:
                new = new.replace("-lX11", f"-L{x11_lib} -lX11")
            if xproto_inc not in new:
                out = []
                for line in new.split("\n"):
                    if line.startswith("CPPFLAGS") and "=" in line:
                        head, _, tail = line.partition("=")
                        line = f"{head}= -I{xproto_inc} {tail.lstrip()}"
                    out.append(line)
                new = "\n".join(out)
            if new != data:
                with open(mk, "w", encoding="utf-8") as f:
                    f.write(new)
                n += 1
        self.output.info(
            f"Makefile 修正完成（{n} 个）：tcl/tk stub 路径 + '-L{x11_lib} -lX11' "
            f"+ '-I{xproto_inc}'")

    def _install_libraries(self):
        """`make install-libraries` = collate（生成合并 pkgIndex.tcl + Img/ 暂存）
        + 拷贝到 `$(INSTALL_ROOT)$(LIB_RUNTIME_DIR)` 与 `$(INSTALL_ROOT)$(libdir)`。"""
        os.makedirs(self._stage_dir, exist_ok=True)
        autotools = Autotools(self)
        autotools.make(target="install-libraries",
                       args=[f'INSTALL_ROOT="{self._stage_dir}"'])
        if not os.path.isdir(self._img_runtime_dir):
            raise ConanException(
                f"install-libraries 未产出运行期目录: {self._img_runtime_dir}")
        n_so = len(glob.glob(os.path.join(self._img_runtime_dir, "*.so")))
        self.output.info(f"安装完成: {self._img_runtime_dir}（{n_so} 个 .so）")

    # -------------------------------------------------- 层 1：上游官方测试
    def _run_upstream_tests(self):
        """docs/TEST_QUALITY_SPEC §3.1 —— 在 build() 末尾真实执行上游测试套件。

        上游入口即顶层 Makefile 的 `tcltests` 目标（`cd tests && tclsh all.tcl`）。
        这里调用同一个入口脚本 `tests/all.tcl`，但包一层无缓冲包装器：
        `tclsh` 不在 PATH 上（来自 tcl conan 包），且 OHOS 上重定向时 stdio 为
        块缓冲，需要保证 timeout 强杀时不丢结果。
        """
        tcl_pkg = self._dep("tcl")
        tclsh = os.path.join(tcl_pkg, "bin", "tclsh9.0")
        if not os.path.isfile(tclsh):
            raise ConanException(f"tcl 包中未找到 tclsh9.0: {tclsh}")

        tests_dir = os.path.join(self.build_folder, "tests")
        all_tcl = os.path.join(tests_dir, "all.tcl")
        if not os.path.isfile(all_tcl):
            raise ConanException(f"上游测试入口缺失: {all_tcl}")

        wrapper = os.path.join(self.build_folder, "_unbuffered_all_tcl.tcl")
        save(self, wrapper, _UNBUFFERED_RUNNER)

        log = os.path.join(self.build_folder, "upstream-tests.log")
        ld = ":".join(self._x11_runtime_lib_dirs())
        tcllib = " ".join([self._img_runtime_dir,
                           os.path.join(tcl_pkg, "lib"),
                           os.path.join(self._dep("tk"), "lib")])
        timeout_bin = "/bin/timeout" if os.path.exists("/bin/timeout") else "timeout"

        cmd = (f'cd "{tests_dir}" && '
               f'LD_LIBRARY_PATH="{ld}" TCLLIBPATH="{tcllib}" '
               f'{timeout_bin} 2400 "{tclsh}" "{wrapper}" "{all_tcl}" '
               f'> "{log}" 2>&1')
        self.output.info(f"上游测试命令（日志 {log}）")
        rc = self.run(cmd, ignore_errors=True)

        # tcltest 汇总行示例： all.tcl:\tTotal\t315\tPassed\t297\tSkipped\t18\tFailed\t0
        summary, total, passed, skipped, failed = "", 0, 0, 0, 0
        try:
            with open(log, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("all.tcl:"):
                        summary = line.strip()
                        cols = line.rstrip("\n").split("\t")
                        vals = {}
                        for i, token in enumerate(cols):
                            if token.strip() in ("Total", "Passed", "Skipped", "Failed"):
                                vals[token.strip()] = int(cols[i + 1])
                        total = vals.get("Total", 0)
                        passed = vals.get("Passed", 0)
                        skipped = vals.get("Skipped", 0)
                        failed = vals.get("Failed", 0)
        except OSError:
            pass

        self.output.info(f"上游测试结果: {summary or '(无汇总行)'}")
        if rc != 0 or failed > 0 or total == 0:
            raise ConanException(
                "上游测试未通过（rc=%s，Total=%d Passed=%d Skipped=%d Failed=%d）"
                "，完整日志: %s" % (rc, total, passed, skipped, failed, log))
        self.output.info(
            f"上游测试通过: Total={total} Passed={passed} "
            f"Skipped={skipped} Failed={failed}")

    # ------------------------------------------------------------- package
    def package(self):
        if not os.path.isdir(os.path.join(self._stage_dir, "lib")):
            # 理论上 build() 已装过；这里只做兜底（例如 source-only 复用）
            self._install_libraries()
        copy(self, "license.terms", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*", src=self._stage_dir, dst=self.package_folder)

    def package_info(self):
        # Img 通过 dlopen / pkgIndex.tcl 使用，不导出可链接的 libs
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        # 消费方定位 Img 运行期目录的便捷变量（Tcl 通过 auto_path/TCLLIBPATH 找它）
        self.cpp_info.bindirs = []
        self.runenv_info.define_path("IMG_LIB_DIR",
                                     os.path.join("lib", "Img%s" % self.version))
