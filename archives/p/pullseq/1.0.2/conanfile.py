"""Conan recipe for pullseq 1.0.2 (FASTA/FASTQ sequence extraction tools).

Upstream is an autotools project whose GitHub tag tarball ships configure.ac
without a generated configure, so build_requirements() pulls automake for
autoreconf.  pcre is a hard dependency (unconditional #include <pcre.h> in
pull_by_re.c / pullseq.c / search_header.c); zlib is probed by configure and
enables gzip input support (kseq.h guarded by HAVE_LIBZ), and is declared so
the feature-complete build is what gets packaged.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, chmod, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PullseqConan(ConanFile):
    name = "pullseq"
    version = "1.0.2"
    description = "pullseq: extract sequences from fasta/fastq files by name, regex, or length"
    license = "MIT"
    homepage = "https://github.com/bcthomas/pullseq"
    url = ""
    topics = ("bioinformatics", "fasta", "fastq", "sequences")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # GitHub tag tarball has configure.ac but no generated configure.
        self.tool_requires("automake/1.18")

    def requirements(self):
        self.requires("pcre/8.45")
        self.requires("zlib/1.3.1")

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pullseq supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # ⚠ 本机 conan 2.29 的 tc.generate(env=X) 是**整体替换**工具链环境而非
        # 合并（实测 conanautotoolstoolchain.sh 只含 X 的内容，CFLAGS/CPPFLAGS
        # 全丢，编译期 pcre.h not found）。正确姿势：先取 tc.environment()，
        # 在其上定义/追加，再交回 generate()。
        tc = AutotoolsToolchain(self)
        # 上游 2014 年代码用多 TU 共享全局的 tentative definition
        # （QUALITY_SCORE 同时定义在 hash.c / size_filter.c）；GCC 默认 -fcommon
        # 会合并，clang 15 默认 -fno-common → ld.lld duplicate symbol
        # （aris/2.2 同模式）。⚠ 必须在 tc.environment() 之前设置。
        tc.extra_cflags.append("-fcommon")
        tc.extra_cxxflags.append("-fcommon")
        env = tc.environment()
        # E386 / 经验汇总 §12.38①：压掉 hnp bash 的 CONFIG_SHELL/SHELL
        # （HMDFS 上 getcwd() 必挂，configure 初始化即 "working directory
        # cannot be determined"）。
        env.define("CONFIG_SHELL", "/bin/sh")
        env.define("SHELL", "/bin/sh")
        # conan 2 的 AutotoolsToolchain 不会自动把依赖 include/lib 写进
        # CPPFLAGS/LDFLAGS（pullseq 的 configure 是裸 -lpcre/pcre.h 探测，无
        # pkg-config），必须注入（abook/0.6.1 同模式）。cpp_info 路径可能是
        # 相对的，需拼 package_folder 绝对路径。
        for dep in self.dependencies.values():
            cpp = dep.cpp_info
            for d in (cpp.includedirs or []):
                p = d if os.path.isabs(d) else os.path.join(dep.package_folder or "", d)
                env.append("CPPFLAGS", "-I" + p)
            for d in (cpp.libdirs or []):
                p = d if os.path.isabs(d) else os.path.join(dep.package_folder or "", d)
                env.append("LDFLAGS", "-L" + p)
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.autoreconf()
        # E490：autoreconf 刚生成的 helper 在 HMDFS 上可能丢执行位，恢复已知
        # autotools 脚本模式（G0 警告项）。
        for helper in ("configure", "config.guess", "config.sub",
                       "install-sh", "missing", "compile", "depcomp"):
            path = os.path.join(self.source_folder, helper)
            if os.path.isfile(path):
                chmod(self, path, 0o755)
        # E011/HMDFS：autoreconf 生成的 configure/config.status 带 `umask 077`
        # 安全临时目录包裹，HMDFS 上写 confXXXXXX/subs1.awk 报 Permission denied
        # （argp-standalone/1.5.0 同模式）。⚠ 必须在 autoreconf 之后打——自举会
        # 重新生成 configure，提前改等于白改。
        import glob as _glob
        for _cfg in _glob.glob(os.path.join(self.source_folder, "**", "configure"),
                               recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        # E386 §12.38①：命令内联再压一道 CONFIG_SHELL/SHELL（环境变量就近
        # 覆盖 buildenv），并用 sh 显式执行 configure（绕开 shebang 执行位问题）。
        # automake/1.18 的 config.guess 在 OHOS 设备上猜不出 build type
        # （§12.1），显式给 --build 跳过探测；不传 --host，保持 native 构建
        # （uperf 交接已实证：给了 --host 会让 configure 找带前缀的交叉编译器）。
        configure_path = os.path.join(self.source_folder, "configure")
        self.run(
            f'CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh "{configure_path}" '
            f"--prefix=/ "
            f"--build=aarch64-unknown-linux-gnu "
            f"'--bindir=${{prefix}}/bin' "
            f"'--sbindir=${{prefix}}/bin' "
            f"'--libdir=${{prefix}}/lib' "
            f"'--includedir=${{prefix}}/include' "
            f"'--oldincludedir=${{prefix}}/include' ",
            env="conanbuild",
            cwd=self.build_folder,
        )
        autotools.make(args=["-j1", "SHELL=/bin/sh"])

    def package(self):
        sf = self.source_folder
        # 本 conan 版本 basic_layout 的 build_folder 是独立子目录
        # （b/build-release），out-of-tree 构建的二进制在 <build>/src/，
        # 不在源码树。
        bf = self.build_folder
        copy(self, "pullseq", os.path.join(bf, "src"), os.path.join(self.package_folder, "bin"))
        copy(self, "seqdiff", os.path.join(bf, "src"), os.path.join(self.package_folder, "bin"))
        for f in ("pullseq", "seqdiff"):
            p = os.path.join(self.package_folder, "bin", f)
            if os.path.isfile(p):
                os.chmod(p, 0o755)
        copy(self, "COPYING", sf, os.path.join(self.package_folder, "licenses"))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # E077: HarmonyOS XPM requires signed executables; the hnp tools
        # resolve libc++ via their own location, so LD_LIBRARY_PATH must not
        # leak into the signer invocation.
        if self.settings.os != "OHOS":
            return
        import glob

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in sorted(glob.glob(os.path.join(self.package_folder, "bin", "*"))):
            if not os.path.isfile(f) or os.path.islink(f) or not self._is_elf(f):
                continue
            self.run(
                'env -u LD_LIBRARY_PATH {oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f)
            )
            self.run(
                'env -u LD_LIBRARY_PATH {sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f)
            )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
