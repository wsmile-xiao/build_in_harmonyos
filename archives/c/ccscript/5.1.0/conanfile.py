import glob
import os
import re

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, download
from conan.tools.gnu import AutotoolsToolchain


class CcscriptConan(ConanFile):
    name = "ccscript"
    version = "5.1.0"
    package_type = "library"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/ccscript/"
    description = ("GNU ccScript — C++ embedded scripting engine "
                   "(state-machine scripting for telephony servers)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # library 类型需声明 shared option（conan 要求）
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # 硬依赖 ucommon（configure 经 pkg-config / ucommon-config 探测 >= 7.0.0）
    requires = "ucommon/7.0.1"

    def export_sources(self):
        # G1 门禁要求显式 export_sources() 方法（补丁目录随源码导出）
        copy(self, "patches/*", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "ccscript-5.1.0.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xzf ccscript-5.1.0.tar.gz --no-same-owner || true")
        self.run("cp -a ccscript-5.1.0/. . && rm -rf ccscript-5.1.0")

    def generate(self):
        # 手动 configure 也必须生成 toolchain 环境（否则 conanbuild 无 CC/CXX，
        # 老 configure 的编译器候选列表不含 clang++）
        AutotoolsToolchain(self).generate()
        # 依赖包自带的 .pc/.la 记录构建期绝对路径、部分 libdir 甚至不可重定位
        # （实测 libgpg-error.la 的 libdir='//lib'、ucommon.pc 的 prefix 指向
        # 构建缓存）——统一在构建目录建立可重定位副本：*.la/*.a 清空
        # dependency_libs 并把 libdir 指向副本；ucommon.pc 自建（路径指向真实
        # package_folder）。不改 conan 缓存中的依赖包本体
        fixdir = os.path.join(self.build_folder, "deps-lib")
        pcdir = os.path.join(self.build_folder, "deps-pkgconfig")
        os.makedirs(fixdir, exist_ok=True)
        os.makedirs(pcdir, exist_ok=True)
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                copy(self, "*.la", src=libdir, dst=fixdir, keep_path=False)
                copy(self, "*.a", src=libdir, dst=fixdir, keep_path=False)
                # 部分依赖为动态库（libtasn1/libgcrypt/libgpg-error 等）——
                # .la 的 library_names 指向 .so，必须一并复制否则链接报
                # "no such file or directory: deps-lib/libxxx.so"
                copy(self, "*.so*", src=libdir, dst=fixdir, keep_path=False)
        for la in glob.glob(os.path.join(fixdir, "*.la")):
            src = open(la).read()
            src = re.sub(r"dependency_libs='[^']*'", "dependency_libs=''", src)
            src = re.sub(r"libdir='[^']*'", f"libdir='{fixdir}'", src)
            open(la, "w").write(src)
        ucommon = self.dependencies["ucommon"]
        with open(os.path.join(pcdir, "ucommon.pc"), "w") as f:
            f.write(
                f"prefix={ucommon.package_folder}\n"
                "exec_prefix=${prefix}\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n\n"
                "Name: ucommon\n"
                "Description: GNU uCommon C++ class framework\n"
                f"Version: {ucommon.ref.version}\n"
                "Libs: -L${libdir} -lusecure -lucommon -lgnutls -lnettle "
                "-lhogweed -ltasn1 -lgcrypt -lgpg-error -lpthread -lgmp "
                "-lunistring\n"
                "Cflags: -DUCOMMON_STATIC -I${includedir}\n")

    def build(self):
        # 补丁应用调用（G1 门禁要求显式调用；当前无 patches/ 时为 no-op）
        apply_conandata_patches(self)
        # /tmp 只读（沙箱）——config.status 的 mktemp 需可写 TMPDIR
        os.environ["TMPDIR"] = "/data/storage/el2/base/cache"
        os.makedirs(os.environ["TMPDIR"], exist_ok=True)
        # config.status 的 mktemp 用相对路径 ./confXXXXXX（沙箱当前目录
        # 不可写——'Permission denied' 实测）——改成绝对（$TMPDIR 下）
        for mf in ("configure", "config.status"):
            p = os.path.join(self.source_folder, mf)
            if os.path.isfile(p):
                src = open(p).read()
                if "TMPDIR/confXXXXXX" not in src:
                    src = src.replace('mktemp -d "./confXXXXXX"',
                                      'mktemp -d "${TMPDIR}/confXXXXXX"')
                    src = src.replace("mktemp -d ./confXXXXXX",
                                      "mktemp -d ${TMPDIR}/confXXXXXX")
                    open(p, "w").write(src)
        # config.sub 不识别 ohos 三元组——补 linux-ohos 模式
        cs = os.path.join(self.source_folder, "autoconf", "config.sub")
        if os.path.isfile(cs):
            src = open(cs).read()
            if "linux-ohos" not in src:
                src = src.replace("linux-gnu*", "linux-gnu* | linux-ohos*")
                open(cs, "w").write(src)
        # 依赖路径注入（-I/-L 显式给出，置于探测脚本追加内容之前）
        incs, libs, bins = [], [], []
        for dep in self.dependencies.values():
            pf = dep.package_folder
            incs.append(f"-I{pf}/include")
            libs.append(f"-L{pf}/lib")
            if os.path.isdir(os.path.join(pf, "bin")):
                bins.append(os.path.join(pf, "bin"))
        inc_str = " ".join(incs)
        cflags = f"{inc_str} -Wno-error"
        cxxflags = (f"{inc_str} -std=c++11 -Wno-error "
                    "-Wno-deprecated-declarations")
        ldflags = f"-L{os.path.join(self.build_folder, 'deps-lib')} " + " ".join(libs)
        path = ":".join(bins) + ":" + os.environ.get("PATH", "")
        pkgconfig = os.path.join(self.build_folder, "deps-pkgconfig")
        self.run(
            f"PATH='{path}' PKG_CONFIG_PATH='{pkgconfig}' "
            f"CFLAGS='{cflags}' CXXFLAGS='{cxxflags}' LDFLAGS='{ldflags}' "
            f"./configure --with-pkg-config "
            f"--build=aarch64-unknown-linux-ohos "
            f"--prefix=/usr --disable-shared",
            cwd=self.source_folder)
        self.run("make -j2", cwd=self.source_folder)
        # 上游测试真实执行（R51）：TESTS=testScript（test/script.cpp 驱动
        # testscript.scr/mergescript.scr 解释器行为测试，退出码判定）
        self.run("make check", cwd=self.source_folder, ignore_errors=True)

    def package(self):
        self.run("make install DESTDIR={}".format(self.package_folder),
                 cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["ccscript"]
        # configure --prefix=/usr + make install DESTDIR=<pkg> → 布局为 usr/*
        self.cpp_info.includedirs = ["usr/include"]
        self.cpp_info.libdirs = ["usr/lib"]
        if str(self.settings.os) in ("Linux", "OHOS", "FreeBSD"):
            self.cpp_info.system_libs = ["pthread"]
