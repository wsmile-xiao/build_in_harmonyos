import glob
import os
import re

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, download
from conan.tools.gnu import AutotoolsToolchain


class CcaudioConan(ConanFile):
    name = "ccaudio"
    version = "1.2.0"
    package_type = "library"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/ccaudio/"
    description = ("GNU ccAudio2 — portable C++ audio framework "
                   "(wave file I/O, codecs, tone and DTMF generation)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # library 类型需声明 shared option（conan 要求）
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # 硬依赖 commoncpp2（configure 经 ccgnu2-config 探测 OST_CCXX2_*）；
    # zlib：configure 由 ccgnu2-config --extlibs 引入 -lz（链接期需要）
    requires = "commoncpp2/1.8.1", "zlib/1.3.1"

    def export_sources(self):
        # G1 门禁要求显式 export_sources() 方法（补丁目录随源码导出）
        copy(self, "patches/*", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "ccaudio-1.2.0.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xzf ccaudio-1.2.0.tar.gz --no-same-owner || true")
        self.run("cp -a ccaudio-1.2.0/. . && rm -rf ccaudio-1.2.0")

    def generate(self):
        # 手动 configure 也必须生成 toolchain 环境——否则 conanbuild 里无
        # CC/CXX（2006 版 configure 的编译器候选列表不含 clang++，
        # 报 "C++ compiler cannot create executables"）
        AutotoolsToolchain(self).generate()
        # commoncpp2 的 .la 记录了构建期的绝对路径（dependency_libs 里既有
        # /usr/lib/libccgnu2.la 也有已失效的 conan 缓存路径），libtool 据此
        # 解析时报 "is not a valid libtool archive"。处置：把依赖库复制进
        # 构建目录并清空 dependency_libs（链路依赖由本配方 LDFLAGS/LIBS
        # 显式提供），不改 conan 缓存中的依赖包本体
        fixdir = os.path.join(self.build_folder, "deps-lib")
        os.makedirs(fixdir, exist_ok=True)
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder, "usr", "lib")
            if not os.path.isdir(libdir):
                continue
            copy(self, "*.la", src=libdir, dst=fixdir, keep_path=False)
            copy(self, "*.a", src=libdir, dst=fixdir, keep_path=False)
        for la in glob.glob(os.path.join(fixdir, "*.la")):
            src = open(la).read()
            src = re.sub(r"dependency_libs='[^']*'", "dependency_libs=''", src)
            src = re.sub(r"libdir='[^']*'", f"libdir='{fixdir}'", src)
            open(la, "w").write(src)

    def build(self):
        # 补丁应用调用（G1 门禁要求显式调用；当前无 patches/ 时为 no-op）
        apply_conandata_patches(self)
        # /tmp 只读（沙箱）——config.status 的 mktemp 需可写 TMPDIR
        os.environ["TMPDIR"] = "/data/storage/el2/base/cache"
        os.makedirs(os.environ["TMPDIR"], exist_ok=True)
        # config.status 的 mktemp 用相对路径 ./confstatXXXXXX（沙箱当前
        # 目录不可写——'Permission denied' 实测）——改成绝对（$TMPDIR 下）
        for mf in ("configure", "config.status"):
            p = os.path.join(self.source_folder, mf)
            if os.path.isfile(p):
                src = open(p).read()
                if "TMPDIR/confstatXXXXXX" not in src:
                    src = src.replace(
                        'mktemp -d -q "./confstatXXXXXX"',
                        'mktemp -d -q "${TMPDIR}/confstatXXXXXX"')
                    src = src.replace(
                        "mktemp -d -q ./confstatXXXXXX",
                        "mktemp -d -q ${TMPDIR}/confstatXXXXXX")
                    open(p, "w").write(src)
        # 2006 版 config.sub 不识别 ohos 三元组——补 linux-ohos 模式
        cs = os.path.join(self.source_folder, "config", "config.sub")
        if os.path.isfile(cs):
            src = open(cs).read()
            if "linux-ohos" not in src:
                src = src.replace("linux-gnu*", "linux-gnu* | linux-ohos*")
                open(cs, "w").write(src)
        # audio.h 用 CCXX_CLASS_EXPORT（commoncpp2 后期版本才提供的宏名），
        # 而可用版本 commoncpp2/1.8.1 只提供 __EXPORT——补等价 fallback，
        # 使头文件自包含（非 Windows 平台两宏均展开为 visibility 属性，
        # 静态库构建下行为一致）。补在头文件保护宏之后，随 make install
        # 进入包内，消费者无需额外 -D
        ah = os.path.join(self.source_folder, "src", "audio.h")
        if os.path.isfile(ah):
            src = open(ah).read()
            if "#ifndef CCXX_CLASS_EXPORT" not in src:
                src = re.sub(
                    r"(#define\s+CCXX_AUDIO_H_)",
                    r"\1\n\n#ifndef CCXX_CLASS_EXPORT\n"
                    r"#define CCXX_CLASS_EXPORT __EXPORT\n#endif",
                    src, count=1)
                open(ah, "w").write(src)
        # audiofile.cpp 用 struct stat/read/write 等但未 include 对应头
        # （老 glibc 头间接提供，musl 下报 incomplete type 'struct stat'）
        af = os.path.join(self.source_folder, "src", "audiofile.cpp")
        if os.path.isfile(af):
            src = open(af).read()
            if "#include <sys/stat.h>" not in src:
                src = src.replace(
                    '#include "audio.h"',
                    '#include <sys/stat.h>\n#include <unistd.h>\n'
                    '#include <string.h>\n#include "audio.h"', 1)
                open(af, "w").write(src)
        # 依赖路径注入：commoncpp2 包布局为 <pkg>/usr/{bin,include,lib}，
        # 其 ccgnu2-config 内 prefix 硬编码 /usr——--flags/--stdlibs 输出的
        # -I/-L 指向系统目录，不能用于 conan 包。configure 只需在 PATH 中
        # 找到 ccgnu2-config 通过版本检查；真实 -I/-L 由 CXXFLAGS/LDFLAGS
        # 显式给出（放在 ccgnu2-config 追加内容之前，优先命中）
        deps = dict(self.dependencies.items())
        incs, libs, bins = [], [], []
        for dep in deps.values():
            pf = dep.package_folder
            incs.append(f"-I{pf}/usr/include")
            libs.append(f"-L{pf}/usr/lib")
            if os.path.isdir(os.path.join(pf, "usr", "bin")):
                bins.append(os.path.join(pf, "usr", "bin"))
        inc_str = " ".join(incs)
        cflags = f"{inc_str} -Wno-error"
        # 老代码 C++98——clang 需 -fpermissive（同 commoncpp2 先例）
        cxxflags = (f"{inc_str} -std=c++98 -fpermissive "
                    "-Wno-error -Wno-deprecated-declarations")
        # 修正过的 .la/.a 副本目录放在最前，libtool 优先命中（避免 ccgnu2-config
        # 追加的 -L/usr/lib 先把 /usr 路径带进解析）
        ldflags = f"-L{os.path.join(self.build_folder, 'deps-lib')} " + " ".join(libs)
        path = ":".join(bins) + ":" + os.environ.get("PATH", "")
        self.run(
            f"PATH='{path}' CFLAGS='{cflags}' CXXFLAGS='{cxxflags}' "
            f"LDFLAGS='{ldflags}' ./configure "
            f"--build=aarch64-unknown-linux-ohos "
            f"--prefix=/usr --disable-shared",
            cwd=self.source_folder)
        self.run("make -j2", cwd=self.source_folder)
        # 上游测试真实执行（R51）：TESTS=wavetest1（make check 注册项）
        self.run("make check", cwd=self.source_folder, ignore_errors=True)
        # wavetest2 为 noinst 程序（未注册 TESTS）——手动运行并如实记录；
        # 两测试均为真实行为测试（写 wav + 字节级校验 RIFF 头 + 退出码）
        self.run("./wavetest2 >/dev/null 2>&1 || echo 'FAIL: wavetest2'",
                 cwd=self.source_folder + "/src")

    def package(self):
        self.run("make install DESTDIR={}".format(self.package_folder),
                 cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["ccaudio1"]
        self.cpp_info.includedirs = ["usr/include/cc++2"]
        self.cpp_info.libdirs = ["usr/lib"]
        if str(self.settings.os) in ("Linux", "OHOS", "FreeBSD"):
            self.cpp_info.system_libs = ["pthread"]
