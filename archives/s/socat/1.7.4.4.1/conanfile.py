from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SocatConan(ConanFile):
    name = "socat"
    version = "1.7.4.4.1"
    description = "Socat — multipurpose relay for bidirectional data transfer"
    license = "GPL-2.0"
    homepage = "http://www.dest-unreach.org/socat/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"OS {self.settings.os} not supported")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS libc 不导出传统全局 `_res`（也不提供 __res_state() 访问器），
        # 但 OHOS sysroot **有** <resolv.h>。socat 的 configure.ac:79 用
        # AC_HEADER_RESOLV()，只判断头文件是否存在 → HAVE_RESOLV_H=1，
        # 随后 xio-ip.c 在 `#if HAVE_RESOLV_H` 下直接使用 `_res.options`：
        #     xio-ip.c:119:11: error: use of undeclared identifier '_res'
        #
        # 同族问题见知识库 **E516**（OHOS libc omits _res/__res_state）：glibc 提供
        # 全局 `_res` 与 `__res_state()`，OHOS/bionic 系则没有。
        # 本包不使用可选依赖，采用「向 configure 声明该头不可用」的最小修法：
        # 强制 ac_cv_header_resolv_h=no → HAVE_RESOLV_H 不定义 → 跳过整段
        # `_res` 代码路径（该路径仅提供 res-debug/res-recurse 等**已废弃**的
        # resolver 调优选项），域名解析本身仍由 getaddrinfo() 正常提供。
        #
        # 实测（1.7.4.4）：置 no 后 xio-ip.c 编译 rc=0；不置则报上述错误。
        # 对照：--disable-res-deprecated 无效（它只关 WITH_RES_DEPRECATED，
        # 不关 HAVE_RESOLV_H，`_res` 仍被引用）。
        tc.configure_args.append("ac_cv_header_resolv_h=no")
        # 同族第二处：OHOS sysroot **有** <sys/stropts.h>（内容仅 `#include <stropts.h>`），
        # 而 <stropts.h> 定义了 `I_LIST`，于是 filan.c:452 的 `#ifdef I_LIST` 块被激活：
        #     filan.c:457: if (!isastream(fd)) {
        # 但 OHOS libc 既不声明也不导出 `isastream()`，链接期报：
        #     ld.lld: error: undefined symbol: isastream
        #     >>> referenced by filan.c  >>> filan.o:(filan_stat) in archive libxio.a
        # 该块用于打印 STREAMS 模块信息（SunOS 遗留），与 socat 的核心中继功能无关。
        # 同样以「声明该头不可用」收口：ac_cv_header_sys_stropts_h=no →
        # HAVE_SYS_STROPTS_H 不定义 → sysincludes.h 不引入 <sys/stropts.h> →
        # I_LIST 未定义 → 整段跳过。
        # 实测：置 no 后 filan.c 预处理不再出现 isastream，全量 `make` rc=0。
        tc.configure_args.append("ac_cv_header_sys_stropts_h=no")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
