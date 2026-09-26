#!/usr/bin/env python3
"""Conan recipe — vgrabbj 0.9.9 (Autotools).

vgrabbj is a Video4Linux image grabber CLI tool (bin_PROGRAMS).

OHOS adaptation:
  * 依赖：v4l/1.32.0 + libjpeg/10 + 共享 libpng/1.6.58（+zlib 传递）。
  * 交叉编译（--build=aarch64-unknown-linux-gnu != --host=aarch64-unknown-linux-ohos）
    强制 autoconf cross_compiling=yes，使 AC_CHECK_LIB/AC_CHECK_HEADERS 只做链接/编译、
    不运行 conftest，规避「configure conftest 运行期加载不了共享库」的根因。
  * configure.ac 四个 AC_MSG_ERROR 硬检查按序：jpeg / m / png / z。其中 jpeg 与 z 均为
    静态 conan 库（libjpeg.a / libz.a，plain 文件无符号链接），configure 的
    AC_CHECK_LIB 链接探测可直接通过；png 本机只有静态归档（libpng.a / liblibpng16_static.a，
    无共享 .so），其 configure 期链接探测在本机不可解（缺传递 -lz）。vgrabbj 源码并不直接
    调用 zlib 函数，-lz 仅在 configure 期硬检查需要，静态 libz.a 可满足链接。
  * 方案（第五策略周期 + 库名对齐 aaphoto）：直接以 autoconf 缓存变量
    ac_cv_lib_png_png_create_info_struct 与 ac_cv_lib_z_crc32 短路 png/z 两个硬检查
    （标准交叉编译手法；libpng/libz 均为 conan 依赖闭包真实存在的库，非伪造）。
    configure 据缓存变量进 if-found 分支，把 -lpng（原生库名，aaphoto 已实证可解析）
    与 -lz 追加进 Makefile 的 LIBS，由 AutotoolsDeps 的 LDFLAGS(-L) 在最终 make 链接中
    解析；共享 libpng16.so 运行期由 conanbuild/conanrun 的 LD_LIBRARY_PATH 提供。
  * 库名：保留 configure 原生的 `-lpng`（不改写为 -lpng16）。已合入的 aaphoto/0.45
    在同一个真机、同一套 autotools.configure()+AutotoolsDeps+LDFLAGS(-L) 机制下链接
    `-lpng` 并成功（其 Makefile AM_LDFLAGS 即 `-ljpeg -lpng -lm`），实证 libpng 包在
    OHOS 上能以 `-lpng` 解析；而把库名改写为 `-lpng16` 后本库最终链接报
    `unable to find library -lpng16`（未版本化 libpng16.so 符号链接在 OHOS 上不可用）。
    故维持原生 -lpng，与 aaphoto 逐字节对齐。
  * generate()：AutotoolsDeps + PkgConfigDeps + 补写 libv4l1.pc（v4l 包 pkg_config_name=libv4l2，
    configure 硬性 PKG_CHECK_MODULES LIBV4L1/libv4l1 需 libv4l1.pc）+ 依赖 libdir 注入 build-scope
    LD_LIBRARY_PATH（最终运行/测试用）+ AutotoolsToolchain(--disable-timestamp --disable-ftp
    + ac_cv_lib_* 缓存变量)。
  * build()：autotools.configure() + autotools.make(-j1)。
  * source()：E490 恢复辅助脚本可执行位；umask 077→022；顶层 pwd 判定失败回退 $PWD。
"""
import os
import shutil
import subprocess

from conan import ConanFile

from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, chmod
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class VgrabbjConan(ConanFile):
    name = "vgrabbj"
    version = "0.9.9"
    description = "vgrabbj 0.9.9 - A video4linux framegrabber"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/vgrabbj/"
    url = "https://gitcode.com/gmanic/vgrabbj"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("v4l/1.32.0")
        self.requires("libjpeg/10")
        # 共享 libpng/1.6.58（标准 conan 配方，真机可直接取用，umask 处理不校验计数）。
        # zlib 由 libpng 传递引入（1.3.1.1），vgrabbj configure 的 AC_CHECK_LIB(z,...)
        # 由 AutotoolsDeps 注入的 -L/-lz 解析。
        self.requires("libpng/1.6.58")

    def configure(self):
        # 全部依赖保持各自缺省配置：
        #   - v4l/1.32.0 缺省 shared=True：ohpcd 远端已有 v4l 共享二进制，直接复用，
        #     避免从源码重建触发 meson（hmbs 预检环境 meson 不可用，
        #     真机报 `meson wrapper error: No module named 'mesonbuild'`）。
        #   - libpng/1.6.58 缺省共享（标准配方，umask 处理不校验计数，二进制可从
        #     ohpcd 远端取用）；不强制 shared=False——静态会走 libpng/1.6.58.3 定制
        #     配方 _relax_private_umask 的严格计数校验而失败。
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # OHOS 受限文件系统：config.status 用 umask 077 建临时目录后写入被拒，
        # 降为 umask 022（原配方在 build() 中 env="conanbuild" 跑 sed，去掉该写法）。
        configure = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure):
            chmod(self, configure, 0o755)
            self._patch_configure_umask(configure)
            self._patch_configure_pwd(configure)
        # E490: OHOS/HMDFS 可能丢失 autotools 辅助脚本 execute bit
        for helper in ("config.guess", "config.sub", "install-sh", "missing"):
            p = os.path.join(self.source_folder, helper)
            if os.path.exists(p):
                chmod(self, p, 0o755)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        self._write_libv4l1_pc()

        # 把全部依赖 libdir 注入 build-scope LD_LIBRARY_PATH（……配置期 conftest 运行
        # 与最终运行/测试解析共享 libpng16/libz 用）。注意：本真机上 configure 的
        # conftest 运行期并不总能拿到该 LD_LIBRARY_PATH（aaphoto 只是它的 -lpng 探测
        # 非致命才不被它绊倒）。因此本配方另以「交叉编译（--build != --host）」强制
        # autoconf 把 AC_CHECK_LIB 变为纯链接（不运行 conftest），见 AutotoolsToolchain。
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

        tc = AutotoolsToolchain(self)
        # 强制交叉编译：--build(gnu) != --host(ohos) -> autoconf 设 cross_compiling=yes，
        # AC_CHECK_LIB(jpeg/m/png/z) 与 AC_CHECK_HEADERS 均只做「链接/编译」不做「运行
        # conftest」。这绕开「configure conftest 运行期加载不了共享 libpng16.so.16」的
        # 运行期根因，但仍须「链接通过的 probe」才能在交叉期放行。
        # 三套件：host=aarch64-unknown-linux-ohos（OHOS 目标）；build=aarch64-unknown-linux-gnu
        # 使其与 host 不同以保证 cross_compiling=yes（aribb24 同款显式三套件，真机可接受）。
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # 禁用 timestamp/ftp：OHOS 无 libttf/libftp
        tc.configure_args.append("--disable-timestamp")
        tc.configure_args.append("--disable-ftp")

        # 【终局方案】交叉「只链接不运行」+ ac_cv 缓存变量短路 png/z 硬检查。
        # 根因（源码 configure.ac 实证，四个 AC_MSG_ERROR 硬检查按序）：
        #   AC_CHECK_LIB(jpeg, jpeg_set_defaults)   <- 通过（静态 libjpeg.a）
        #   AC_CHECK_LIB(m, main)                   <- 通过（系统库）
        #   AC_CHECK_LIB(png, png_create_info_struct) <- 硬错误（共享 libpng16.so）
        #   AC_CHECK_LIB(z, crc32)                  <- 硬错误（静态 libz.a，但本库源码不用 zlib）
        # png 的 configure 期链接探测在本机不可解：交叉只链接时 conftest 链接行只有
        # -L<libpng libdir> -lpng，且 OHOS 上 libpng16.so 未版本化符号链接不可靠，故以
        # ac_cv_lib_png_png_create_info_struct/ac_cv_lib_z_crc32 缓存变量短路（标准交叉
        # 编译手法；libpng/libz 均为 conan 依赖闭包真实存在的库，非伪造）。configure 据缓存
        # 变量进 if-found 分支，把原生 -lpng（aaphoto 实证可解析）与 -lz 追加进 Makefile
        # 的 LIBS，由 AutotoolsDeps 的 LDFLAGS(-L) 在最终 make 链接中解析；共享 libpng16.so
        # 运行期由 conanbuild/conanrun 的 LD_LIBRARY_PATH 提供。
        tc.configure_args.append("ac_cv_lib_png_png_create_info_struct=yes")
        tc.configure_args.append("ac_cv_lib_z_crc32=yes")
        tc.generate()

    def _write_libv4l1_pc(self):
        """为 configure 的 PKG_CHECK_MODULES([LIBV4L1], [libv4l1]) 提供修正版 libv4l1.pc。

        v4l/1.32.0 包的 pkg_config_name 是 libv4l2，PkgConfigDeps 只生成 libv4l2.pc；
        而 vgrabbj configure.ac 硬性检查的是 libv4l1。这里在 generators_folder（已在
        conanbuild 的 PKG_CONFIG_PATH 里）补一个 libv4l1.pc，用 v4l 包真实绝对路径，
        使 PKG_CHECK_MODULES 找到 .pc 并给出可链接的 -L/-l（共享 libv4l1，运行期由
        conanbuild LD_LIBRARY_PATH 解析）。
        """
        v4l = self.dependencies["v4l"]
        base = v4l.package_folder
        libdir = next(
            (d if os.path.isabs(d) else os.path.join(base, d)
             for d in (v4l.cpp_info.libdirs or ["lib"])),
            os.path.join(base, "lib"),
        )
        incdir = next(
            (d if os.path.isabs(d) else os.path.join(base, d)
             for d in (v4l.cpp_info.includedirs or ["include"])),
            os.path.join(base, "include"),
        )
        pc = (
            "prefix={base}\n"
            "exec_prefix=${{prefix}}\n"
            "libdir={libdir}\n"
            "includedir={incdir}\n"
            "\n"
            "Name: libv4l1\n"
            "Description: V4L1 compatibility library\n"
            "Version: 1.0\n"
            "Libs: -L${{libdir}} -lv4l1\n"
            "Cflags: -I${{includedir}}\n"
        ).format(base=base, libdir=libdir, incdir=incdir)
        target = os.path.join(self.generators_folder, "libv4l1.pc")
        with open(target, "w", encoding="utf-8") as f:
            f.write(pc)
        self.output.info(f"wrote {target}")


    @staticmethod
    def _patch_configure_umask(configure):
        """Keep config.status temp-script writes working on OHOS restricted FS."""
        with open(configure, encoding="utf-8") as f:
            contents = f.read()
        patched = contents.replace(
            "(umask 077 && mktemp -d \"./confXXXXXX\")",
            "(umask 022 && mktemp -d \"${TMPDIR:-.}/confXXXXXX\")",
        ).replace(
            "tmp=./conf$$-$RANDOM",
            "tmp=${TMPDIR:-.}/conf$$-$RANDOM",
        ).replace(
            "(umask 077 && mkdir \"$tmp\")",
            "(umask 022 && mkdir \"$tmp\")",
        )
        if patched == contents:
            # 更老的 autoconf 可能用其它结构，退化为整体 umask 替换。
            patched = contents.replace("umask 077", "umask 022")
        if patched != contents:
            with open(configure, "w", encoding="utf-8", newline="") as f:
                f.write(patched)
            os.utime(configure, None)

    @staticmethod
    def _patch_configure_pwd(configure):
        """让 configure 顶层 pwd 判定在 getcwd 失败时回退 $PWD（aribb24/adms/nspr 同款）。

        OHOS/HMDFS 深路径构建目录里 hnp bash 的 getcwd() 损坏，autoconf 生成的
        configure 顶部 `ac_pwd=`pwd``（2.70 风格）或 `if (pwd) >/dev/null...`（2.69
        风格）判定会直接报 "working directory cannot be determined"。build() 已
        os.chdir(build_folder) 并预置 $PWD；这里再 patch configure 脚本，让 pwd 失败
        时回退逻辑路径 $PWD，三重兜底确保 configure 能跑过顶层 cwd 检查。
        """
        with open(configure, encoding="utf-8", newline="") as f:
            contents = f.read()
        patched = contents
        # autoconf >= 2.70 风格：ac_pwd=`pwd` && test -n "$ac_pwd" &&（nspr/adms 同款改写）
        patched = patched.replace(
            "ac_pwd=`pwd` && test -n \"$ac_pwd\" &&",
            "ac_pwd=`pwd` 2>/dev/null || ac_pwd=\"$PWD\"\ntest -n \"$ac_pwd\" &&",
            1,
        )
        # autoconf 2.69 风格：if (pwd) >/dev/null 2>&1; then :; else ...（aribb24 同款改写）
        patched = patched.replace(
            "if (pwd) >/dev/null 2>&1; then :; else",
            "if (pwd) >/dev/null 2>&1 || test -n \"$PWD\"; then :; else",
        )
        if patched != contents:
            with open(configure, "w", encoding="utf-8", newline="") as f:
                f.write(patched)
            os.utime(configure, None)

    def _find_libpng_dep(self):
        """返回 libpng 依赖对象（兼容 ConanFileDependencies 的 dict/get/迭代访问）。"""
        libpng = None
        try:
            libpng = self.dependencies.get("libpng")
        except Exception:
            libpng = None
        if libpng is None:
            try:
                libpng = self.dependencies["libpng"]
            except Exception:
                libpng = None
        if libpng is None:
            for dep in self.dependencies:
                try:
                    if getattr(dep.ref, "name", None) == "libpng":
                        libpng = dep
                        break
                except Exception:
                    continue
        return libpng

    @staticmethod
    def _neon_stub_source():
        """返回补齐缺失 NEON 符号的 C 源码（功能安全的 no-op / 返回 0 标量回退）。

        真机诊断证实本机 libpng 静态归档（libpng.a / liblibpng16_static.a）都引用了这 4
        个 ARM NEON 符号（png_init_filter_functions_neon/png_riffle_palette_neon/
        png_do_expand_palette_rgba8_neon/png_do_expand_palette_rgb8_neon）却缺实现对象。
        我们以功能等价的安全 stub 补齐（libpng 1.6.x 源码实证所有调用点都有标量回退）：
          - png_init_filter_functions_neon：no-op —— png_init_filter_functions 先装标量
            滤波函数再经 PNG_FILTER_OPTIMIZATIONS(pp,bpp) 调 NEON，no-op 保持标量滤波。
          - png_riffle_palette_neon / png_do_expand_palette_*_neon：返回 0 / 不动作 ——
            png_do_expand_palette 里 NEON 返回已处理像素数 i，随后的标量 for(i; i<width)
            从初始 sp/dp 全宽展开，语义正确。
        符号名即链接契约（C 无 mangling）；参数用不透明 struct 指针，ABI 兼容。
        """
        return r'''/* png16-neon-stub.c - functional no-op stubs for libpng ARM NEON symbols
 * that are missing from the OHOS libpng static archives. Compile together with
 * vgrabbj so ld.lld can resolve these undefined symbols; all four call sites in
 * libpng have scalar fallbacks, so a no-op / return-0 stub is functionally safe
 * (disables the NEON optimization path only).
 */
typedef struct png_struct_def *png_structp;
typedef struct png_row_info_struct *png_row_infop;
typedef unsigned char *png_bytep;
typedef const unsigned char *png_const_bytep;
typedef png_bytep *png_bytepp;

__attribute__((weak))
void
png_init_filter_functions_neon(png_structp pp, unsigned int bpp)
{
   (void)pp; (void)bpp; /* keep scalar filter functions installed */
}

__attribute__((weak))
void
png_riffle_palette_neon(png_structp png_ptr)
{
   (void)png_ptr; /* palette stash not built; scalar expansion is used instead */
}

__attribute__((weak))
int
png_do_expand_palette_rgba8_neon(png_structp png_ptr, png_row_infop row_info,
   png_const_bytep row, png_bytepp ssp, png_bytepp ddp)
{
   (void)png_ptr; (void)row_info; (void)row; (void)ssp; (void)ddp;
   return 0; /* 0 pixels pre-processed -> scalar loop handles the full row */
}

__attribute__((weak))
int
png_do_expand_palette_rgb8_neon(png_structp png_ptr, png_row_infop row_info,
   png_const_bytep row, png_bytepp ssp, png_bytepp ddp)
{
   (void)png_ptr; (void)row_info; (void)row; (void)ssp; (void)ddp;
   return 0; /* 0 pixels pre-processed -> scalar loop handles the full row */
}
'''

    def _build_neon_stub(self):
        """写 stub.c 并用工具链编译归档成 build_folder/libpngneonstub.a。

        返回静态库绝对路径；编译/归档不可用时返回 None（宁缺毋假，仍继续构建让链接如实失败）。
        """
        stub_dir = self.build_folder
        src = os.path.join(stub_dir, "png16-neon-stub.c")
        obj = os.path.join(stub_dir, "png16-neon-stub.o")
        lib = os.path.join(stub_dir, "libpngneonstub.a")
        try:
            with open(src, "w", encoding="utf-8") as f:
                f.write(self._neon_stub_source())
        except OSError as e:
            self.output.warning("could not write NEON stub source: %s" % e)
            return None
        # 编译器：优先 build env 的 CC，否则 clang/cc
        cc = os.environ.get("CC") or (shutil.which("clang") or shutil.which("cc") or shutil.which("gcc"))
        if not cc:
            self.output.warning("no C compiler found to build NEON stub; link may fail with NEON undefined symbol")
            return None
        try:
            r = subprocess.run([cc, "-c", src, "-o", obj],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, timeout=120)
        except (OSError, subprocess.SubprocessError) as e:
            self.output.warning("NEON stub compile error: %s" % e)
            return None
        if r.returncode != 0 or not os.path.exists(obj):
            self.output.warning("NEON stub compile failed:\n%s" % r.stdout)
            return None
        # 归档器：AR / llvm-ar / ar
        ar = os.environ.get("AR") or (shutil.which("llvm-ar") or shutil.which("ar") or shutil.which("ar-new"))
        if not ar:
            self.output.warning("no archiver (ar) found to build NEON stub static lib")
            return None
        try:
            r = subprocess.run([ar, "rcs", lib, obj],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, timeout=120)
        except (OSError, subprocess.SubprocessError) as e:
            self.output.warning("NEON stub archive error: %s" % e)
            return None
        if r.returncode != 0 or not os.path.exists(lib):
            self.output.warning("NEON stub archive failed:\n%s" % r.stdout)
            return None
        self.output.info("built NEON stub static lib: %s" % lib)
        return lib

    def _describe_libpng_libdirs(self):
        """输出 libpng 包 libdir 的实际内容，供诊断。"""
        libpng = self._find_libpng_dep()
        if libpng is None:
            return "no libpng dependency found in build"
        base = libpng.package_folder or "?"
        lines = ["libpng package_folder=%s" % base]
        dirs = []
        for libdir in (libpng.cpp_info.libdirs or ["lib"]):
            d = libdir if os.path.isabs(libdir) else os.path.join(base, libdir)
            dirs.append(d)
        dirs += [os.path.join(base, "lib"), os.path.join(base, "lib64"), base]
        seen = set()
        for d in dirs:
            rd = os.path.realpath(d)
            if rd in seen:
                continue
            seen.add(rd)
            try:
                names = sorted(os.listdir(d))
            except OSError:
                lines.append("%s -> <unreadable>" % d)
                continue
            lines.append("%s -> %s" % (d, ", ".join(n for n in names if "png" in n) or "<no png entries>"))
        return "; ".join(lines)


    @staticmethod
    def _patch_makefile_libs(stub_flag, *search_dirs):
        """在 configure 已生成的各 Makefile 的 `LIBS = ...` 行末尾追加 NEON stub 链接项。

        与「patch configure 脚本源码文本」相比，这里直接改最终用于链接的生成 Makefile，
        不依赖 configure 内部 `LIBS="-lpng $LIBS"` 的具体写法（多轮证明该文本最脆弱、
        不同 autoconf 变体/缓存分支下补丁不落地就静默漏链）。configure 生成的每个
        Makefile 都由 `@LIBS@` 替换出 `LIBS = -lpng ...`，把
        `-L<dir> -lpngneonstub` 追加到该行末尾（保留原 -lpng 及其它库），最终 make 链接
        时 stub 出现在 -lpng 之后，ld.lld 多趟重扫归档会用 stub 补齐 libpng.a 引用的
        4 个 NEON 符号。返回是否命中了至少一个 Makefile 的 LIBS 行。
        """
        if not stub_flag:
            return False
        import re as _re
        search = [d for d in search_dirs if d and os.path.isdir(d)]
        if not search:
            return False
        li = _re.compile(r"^(LIBS[ \t]*=[ \t]*)(.*)$", _re.MULTILINE)
        hit = False
        seen = set()
        for root in search:
            for dirpath, _dirnames, filenames in os.walk(root):
                if "Makefile" not in filenames:
                    continue
                mk = os.path.join(dirpath, "Makefile")
                if os.path.realpath(mk) in seen:
                    continue
                seen.add(os.path.realpath(mk))
                try:
                    with open(mk, encoding="utf-8", newline="") as f:
                        contents = f.read()
                except OSError:
                    continue
                def _append(m):
                    val = m.group(2)
                    if "pngneonstub" in val:
                        return m.group(0)
                    return m.group(1) + val + " " + stub_flag
                patched = li.sub(_append, contents)
                if patched == contents:
                    continue
                try:
                    with open(mk, "w", encoding="utf-8", newline="") as f:
                        f.write(patched)
                    os.utime(mk, None)
                    hit = True
                except OSError:
                    continue
        return hit


    def build(self):
        apply_conandata_patches(self)

        # autotools.configure()：Conan 的 Autotools.configure() 固定调用
        # {source_folder}/configure（与 cwd 无关），经 conanbuild 环境把 AutotoolsDeps
        # 注入的依赖 -L/-I/-l 与 generate() 注入的 LD_LIBRARY_PATH 一并代入。
        # 本库以「交叉编译」（--build != --host，由 generate() 的 AutotoolsToolchain
        # 写入）强制 configure cross_compiling=yes，使 AC_CHECK_LIB/AC_CHECK_HEADERS
        # 只做链接/编译（不运行 conftest），规避共享库 conftest 运行期加载失败；对
        # configure 期本机不可解的 png/z 硬检查，generate() 直接以 ac_cv_lib_* 缓存变量
        # 短路（libpng/libz 均为依赖闭包真实存在的库）。库名保留 configure 原生的
        # -lpng（aaphoto 实证可解析；不改写为 -lpng16——libpng16.so 未版本化符号链接在
        # OHOS 上不可用），缓存短路后 LIBS 落地 -lpng，由 AutotoolsDeps -L 解析。
        # getcwd 兜底：build 期 cwd 默认即 build_folder，显式同步 PWD；source() 的
        # _patch_configure_pwd 让 configure 顶层 pwd 判定失败时回退 $PWD（无副作用）。
        os.environ["PWD"] = self.build_folder

        autotools = Autotools(self)
        autotools.configure()

        # 【final-link NEON 修复】真机诊断（hmbs hook + _describe_libpng_libdirs）证明本机
        # libpng 包 lib/ 里**两个静态归档都缺失** 4 个 ARM NEON 符号
        # （png_init_filter_functions_neon/png_riffle_palette_neon/
        # png_do_expand_palette_rgba8_neon/png_do_expand_palette_rgb8_neon）的实现对象
        # → `-lpng` 命中 libpng.a 时 ld.lld undefined symbol；本机亦无共享 .so 可改链
        # （诊断 `lib/ -> liblibpng16_static.a, libpng.a` 只有静态归档）。
        # 因此只能自行提供这 4 个符号：本配方编译功能安全的 NEON stub 静态库
        # （no-op / 返回 0，libpng 所有调用点有标量回退，禁用 NEON 优化路径），并在
        # configure 生成 Makefile 之后，把 `-L<dir> -lpngneonstub` 直接追加到各生成
        # Makefile 的 `LIBS =` 行末尾，使最终 make 链接必然带上 stub。
        # 之所以不再 patch configure 脚本源码文本：多轮证明那块文本
        # （LIBS="-lpng $LIBS"）在不同 autoconf 变体/缓存分支下写法不可靠，补丁不落地
        # 就静默漏链（真机仍报 undefined symbol）。改 patch 生成 Makefile 是确定性路线。
        _stub = self._build_neon_stub()
        if _stub:
            _stub_flag = "-L%s -lpngneonstub" % os.path.dirname(_stub)
            if self._patch_makefile_libs(
                _stub_flag, self.build_folder, self.source_folder
            ):
                self.output.info(
                    "appended NEON stub %s to generated Makefile LIBS" % _stub_flag
                )
            else:
                self.output.warning(
                    "no generated Makefile LIBS line found to append NEON stub %s; "
                    "final link may hit undefined NEON symbols" % _stub_flag
                )
        else:
            self.output.warning(
                "could not build NEON stub static lib; final link may hit undefined "
                "NEON symbols. libpng package scan: %s" % self._describe_libpng_libdirs()
            )

        # R9/-j1: OHOS 不支持 make jobserver（mkfifo）
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
