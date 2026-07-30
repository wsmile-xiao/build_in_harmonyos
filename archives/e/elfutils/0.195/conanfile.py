#!/usr/bin/env python3
"""Conan recipe — elfutils 0.195 (autotools)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout



class ElfutilsConan(ConanFile):
    name = "elfutils"
    version = "0.195"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"


    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("zstd/1.5.7")
        self.requires("bzip2/1.0.8")
        self.requires("xz/5.6.2")
        self.requires("argp-standalone/1.5.0")
        self.requires("musl-fts/1.2.7")
        self.requires("musl-obstack/1.2.3")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-werror")
        tc.configure_args.append("--enable-libdebuginfod=dummy")
        tc.configure_args.append("--disable-debuginfod")
        tc.configure_args.append("--with-zstd")
        tc.configure_args.append("--program-prefix=eu-")
        # musl 需要的三项（与 Alpine 的 elfutils APKBUILD 一致）：
        #   _GNU_SOURCE      —— musl 在此宏下才暴露 program_invocation_short_name
        #                       （lib/color.c、src/{elflint,readelf,elfcmp}.c 都用它）
        #   FNM_EXTMATCH=0   —— musl 的 fnmatch.h 没这个宏（探针实测）
        #   -Wno-error       —— musl 与 glibc 的细节差异会触发若干告警，
        #                       上游 --disable-werror 只管它自己的 -Werror
        tc.extra_cflags.append("-D_GNU_SOURCE")
        tc.extra_cflags.append("-DFNM_EXTMATCH=0")
        tc.extra_cflags.append("-Wno-error")
        tc.extra_cxxflags.append("-D_GNU_SOURCE")
        tc.extra_cxxflags.append("-Wno-error")

        # ── 依赖的 -I / -L / -l 必须经环境变量喂给 configure ──
        # elfutils 的 configure 用 AC_CHECK_LIB 类探测（如 --with-zstd 会试链 -lzstd），
        # 不给路径就报 `configure: error: missing -lzstd for --with-zstd`。
        # 走 os.environ 而非 AutotoolsToolchain.extra_* —— 后者实测不一定落到 configure
        # 的编译/链接探测里（本仓 autotools-dep-header-missing 规则的既有结论）。
        import os
        _inc, _lib, _l = [], [], []
        for _ref, _dep in self.dependencies.items():
            ci = _dep.cpp_info
            for _p in ci.includedirs or []:
                _inc.append("-I" + _p)
            for _p in ci.libdirs or []:
                _lib.append("-L" + _p)
            for _n in ci.libs or []:
                _l.append("-l" + _n)
        os.environ["CPPFLAGS"] = " ".join(_inc) + " " + os.environ.get("CPPFLAGS", "")
        os.environ["LDFLAGS"] = " ".join(_lib) + " " + os.environ.get("LDFLAGS", "")
        # 三个 musl 垫片（argp / fts / obstack）提供的是 glibc 才有的符号，
        # elfutils 的源码直接调它们，故必须显式进 LIBS，否则链接期 undefined。
        os.environ["LIBS"] = " ".join(_l) + " " + os.environ.get("LIBS", "")
        self.output.info("CPPFLAGS=%s" % os.environ["CPPFLAGS"][:200])
        self.output.info("LDFLAGS=%s" % os.environ["LDFLAGS"][:200])
        self.output.info("LIBS=%s" % os.environ["LIBS"][:200])
        # configure 会**编译并运行**探测程序（"checking whether we are cross compiling"）。
        # 我们把 musl-fts / musl-obstack 这两个**共享库**放进了 LIBS，
        # 探测程序链上它们后运行时找不到 .so → `configure: error: cannot run C compiled programs.`
        #
        # 关键：**不能用 -Wl,-rpath 解决** —— 那会把 conan cache 绝对路径烤进
        # 产物的 RPATH，正是本仓一直在修的「安装产物里烤死构建期路径」那个病。
        # 用 LD_LIBRARY_PATH：只影响构建期的进程执行，不进任何产物。
        _ldpath = ":".join(_p for _dep in
                           (d for _r, d in self.dependencies.items())
                           for _p in (_dep.cpp_info.libdirs or []))
        if _ldpath:
            os.environ["LD_LIBRARY_PATH"] = _ldpath + ":" + os.environ.get("LD_LIBRARY_PATH", "")
            self.output.info("构建期 LD_LIBRARY_PATH=%s" % os.environ["LD_LIBRARY_PATH"][:200])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # 发布 tarball（ftp.gnu.org 那类）里带现成的 configure，直接用；
        # 但 **GitHub 的 archive tarball 从不含 configure**（它只是 git tree 的快照，
        # configure 是 autoreconf 的产物、不进版本库），此时必须先自举。
        # 判在运行期而非生成期：同一份配方两种源都能用。
        import os as _os
        if not _os.path.isfile(_os.path.join(self.source_folder, "", "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            autotools.autoreconf()
        # ⚠️ umask / uname 这类对 configure 脚本本身的修补**必须在 autoreconf 之后**：
        # 自举会重新生成 configure，放在前面等于白改（改的是不存在的文件，
        # 或改完又被覆盖）。
        import glob, os
        for _cfg in glob.glob(os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报 Permission denied /
        # Operation not permitted（cmake/SDK-toolchain 产的自签无效，且 conan install 复制会破坏链接器自签）。
        # ① lib/ 的 .so  ② bin/ 的 ELF 可执行文件（llvm-config/xxx CLI 等）——产可执行文件的包必须签 bin。
        import glob, os
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        explicit_libs = ['elf', 'dw', 'asm']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "elfutils")
        self.cpp_info.set_property("cmake_target_name", "elfutils::elfutils")
        pkg = "" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        import os
        for _env in []:
            _k, _v = _env.split("=", 1)
            self.runenv_info.define_path(_k, os.path.join(self.package_folder, _v))

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
