from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
import json
import os

# ---------------------------------------------------------------------------
# ttyload 0.5-20131024-gitf949537 (upstream Version file: 0.5.3)
#
# Upstream is a 3-file, zero-dependency terminal load-average plotter driven by
# a hand-written Makefile.  Two facts drive this recipe:
#
#   1. The Makefile picks its platform back-end from an *architecture directory
#      whitelist*:  ARCH = 'uname -s | sed -e 's/ /-/g''  and
#                    OBJS = arch/$(ARCH)/getload.o arch/$(ARCH)/terminfo.o
#      The shipped tarball only carries FreeBSD / IRIX / Linux / SunOS, and
#      'uname -s' on HarmonyOS PC reports "HarmonyOS", so a stock build stops at
#      "No rule to make target 'arch/HarmonyOS/getload.o'".
#      Fixed by patches/0001-Makefile.patch, which uses upstream's *own* idiom
#      for "architectures that mimic each other" (the ARCHLINKS mechanism that
#      already maps Darwin and Isilon-OneFS onto FreeBSD) to map HarmonyOS onto
#      the Linux back-end.  That mapping is backed by measurement, not by hope:
#      arch/Linux/getload.c only reads /proc/loadavg and arch/Linux/terminfo.c
#      only needs ioctl(TIOCGWINSZ) -- both work on this platform (see notes.md).
#
#   2. The Makefile hard-codes 'CC=gcc -pedantic -Wall -Werror'.  HarmonyOS PC
#      build hosts expose the OHOS SDK clang only (no gcc, no cc), and -Werror
#      is fatal there for reasons that are not our patch's fault -- the OHOS
#      sysroot itself emits a #warning from <sys/fcntl.h>, and upstream's own
#      K&R prototypes in ttyload.h trip -Wstrict-prototypes.  So CC and
#      OTHER_FLAGS are handed to make on the command line (command-line
#      variables win over in-file assignments and propagate through the
#      upstream archbuild -> sub-make recursion).  UPSTREAM_WARNING_FLAGS keeps
#      every warning upstream asked for and prints it; only the "turn warnings
#      into errors" switch is dropped.
# ---------------------------------------------------------------------------

UPSTREAM_WARNING_FLAGS = "-pedantic -Wall -Wno-error"


class TtyloadConan(ConanFile):
    name = "ttyload"
    version = "0.5-20131024-gitf949537"
    description = ("Terminal load-average grapher: draws the 1/5/15 minute "
                   "system load averages as a live ASCII chart on any ANSI "
                   "terminal, without curses and without any external library.")
    license = "ISC"
    homepage = "https://github.com/lindes/ttyload"
    url = ""
    topics = ("monitor", "load-average", "terminal", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # ------------------------------------------------------------------ #
    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: platform tests must accept OHOS alongside Linux, never '== "Linux"'.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ttyload needs a Linux-compatible /proc/loadavg and "
                "ioctl(TIOCGWINSZ); got os=%s" % self.settings.os)

    # ------------------------------------------------------------------ #
    def _c_compiler(self):
        """Real C compiler for this build, resolved Conan-side (R33)."""
        executables = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict) or {}
        cc = executables.get("c")
        if not cc:
            cc = {"clang": "clang", "apple-clang": "clang", "gcc": "gcc",
                  "msvc": "cl"}.get(str(self.settings.compiler))
        if not cc:
            raise ConanException(
                "ttyload: cannot resolve a C compiler from "
                "tools.build:compiler_executables for compiler=%s"
                % self.settings.compiler)
        return cc

    def source(self):
        # 没有 layout()：source_folder == build_folder == 包根，上游 Makefile 用
        # -I${PWD} 且把 .o 就地生成，必须原位构建。tarball 顶层目录带加号形态
        # (ttyload-0.5+20131024+gitf949537)，strip_root 掉它，归档版本串保持
        # 平台侧的连字符形态，不做"归一化"。
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # Default target is "archbuild": it creates the arch/<arch> symlinks and
        # then sub-makes both programs (ttyload and upstream's own archtest).
        #
        # 带空格值的 make 变量必须自带引号：Autotools.make() 只是把 args 用空格
        # 拼成命令行再交给 shell，不做转义。少了引号就只有 OTHER_FLAGS 的第一个
        # word 能落到 make 里（B 机实测 -Wall -Wno-error 被吃掉，编译行只剩
        # -pedantic）。
        autotools.make(args=["-j1",
                             'CC="%s"' % self._c_compiler(),
                             'OTHER_FLAGS="%s"' % UPSTREAM_WARNING_FLAGS])
        # Upstream's platform self-check harness.  It is finite (unlike
        # 'make test', see MANIFEST.yml) and it is what actually proves that the
        # arch back-end we selected can read the load averages on this machine.
        # Autotools 对象没有 run()，这里用 self.run（R33：编译器/路径全部
        # Conan 侧解析，不读裸 shell 变量）。
        self.run('"%s"' % os.path.join(self.build_folder, "archtest"),
                 env="conanbuild")
        # 机器可读的上游测试台账（R51：清点 -> 实跑 -> 如实回填）。
        # discovered=2: 上游只有 'make test' 这一个测试目标 + archtest 这个架构
        #   自检程序（实物 24 个普通文件里再无 tests/ 目录、无 ctest/pytest；6 个目录不计）。
        # executed=1  : build() 里只裸跑有限终止的 ./archtest；'make test' 按上游
        #   设计永不退出，改在 test_package/test_ttyload.sh 里有界执行同一程序、
        #   另加 '-m' 单色选项（实物 '"$BIN" -m -i 1'）并加 4 条断言（合计实跑 2 项，全过）。
        self.output.info("UPSTREAM_TEST_RESULT=" + json.dumps({
            "framework": "makefile",
            "command": "./archtest",
            "discovered": 2,
            "executed": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
            "note": "upstream 'make test' = './ttyload -i 1' never terminates "
                    "(optstring i:hvmr:c: has no iteration limit), so it is run "
                    "bounded with 4 assertions in test_package/test_ttyload.sh",
        }, sort_keys=True))

    # ------------------------------------------------------------------ #
    def package(self):
        # Upstream 'install:' is just '/bin/cp ttyload $(INSTALLDIR)/ttyload'
        # -- one binary, no libraries, no headers.  Reproduced with Conan copy
        # so we do not depend on /bin/cp or on an absolute INSTALLDIR (R49).
        copy(self, "ttyload", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Application package: nothing to link against.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []
