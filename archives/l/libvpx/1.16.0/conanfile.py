#!/usr/bin/env python3
"""Conan recipe — libvpx 1.16.0 (libvpx 自带手写 configure + make)"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class LibvpxConan(ConanFile):
    name = "libvpx"
    version = "1.16.0"
    package_type = "library"
    license = "BSD-3-Clause"
    homepage = "https://www.webmproject.org/code/"
    url = "https://github.com/webmproject/libvpx"
    description = (
        "VP8/VP9 视频编解码库（WebM Project）。BSD-3-Clause，可与 LGPL 的 FFmpeg 组合而不传染许可。"
    )
    topics = ("vp8", "vp9", "webm", "video", "codec")
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    _HNP_BIN = "/data/service/hnp/bin"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        # 【与普通 autotools 库的关键差异】不生成 AutotoolsToolchain。
        # libvpx 的 configure 与 FFmpeg 同类：手写 shell 脚本（仓内无 configure.ac），
        # 只认 --prefix / --libdir / --target= 及自有 --enable/--disable 开关，
        # 连 --includedir 都没有；遇未知选项走 build/make/configure.sh 的 die_unknown 直接退出。
        # 故全部参数在 build() 里按 libvpx 自己的选项名显式拼。
        pass

    def _cc(self, key, fallback):
        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return exes.get(key) or os.path.join(self._HNP_BIN, fallback)

    def _jobs(self):
        return self.conf.get("tools.build:jobs", check_type=int) or (os.cpu_count() or 4)

    def build(self):
        apply_conandata_patches(self)

        # ① 清 env 污染：设备 .zshrc 会全局导出 CFLAGS/LDFLAGS/PKG_CONFIG_PATH 等，
        #    漏进 configure 会链到 ~/usr/local 里的同名库。
        for _var in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "LIBS",
                     "PKG_CONFIG_PATH", "PKG_CONFIG_LIBDIR",
                     "LD_LIBRARY_PATH", "CMAKE_PREFIX_PATH"):
            os.environ.pop(_var, None)

        # ② HMDFS 上默认 TMPDIR 不可写，configure 的 conftest 建文件会 Permission denied。
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp

        # ③ PATH 必须含 hnp bin：libvpx 的 configure 按**裸名**调 diff/perl 等
        #    （configure:195 `if ! diff --version`、:199 `perl --version`），而 conan 的 self.run
        #    走 /bin/sh、PATH 未必含 /data/service/hnp/bin → 报 "diff missing: Try installing
        #    diffutils via your package manager."（设备上 diff 其实存在，是 GNU diffutils 3.10）。
        os.environ["PATH"] = self._HNP_BIN + os.pathsep + os.environ.get("PATH", "")

        # ④ 工具链：libvpx 的 configure 写作 `CC=${CC:-${CROSS}gcc}`（build/make/configure.sh:745），
        #    导出 CC 等即可覆盖；否则它按 arm64-linux-gcc 目标去找不存在的 aarch64-linux-gnu-gcc。
        os.environ["CROSS"] = ""
        os.environ["CC"] = self._cc("c", "clang")
        os.environ["CXX"] = self._cc("cpp", "clang++")
        os.environ["LD"] = self._cc("c", "clang")
        os.environ["AS"] = self._cc("c", "clang")
        os.environ["AR"] = os.path.join(self._HNP_BIN, "llvm-ar")
        os.environ["NM"] = os.path.join(self._HNP_BIN, "llvm-nm")
        os.environ["RANLIB"] = os.path.join(self._HNP_BIN, "llvm-ranlib")
        os.environ["STRIP"] = os.path.join(self._HNP_BIN, "llvm-strip")

        pkg = self.package_folder
        args = [
            # libvpx 只有这两个路径选项；头文件固定装到 <prefix>/include/vpx/
            "--prefix=" + pkg,
            "--libdir=" + os.path.join(pkg, "lib"),
            # aarch64 Linux 目标；OHOS 内核接口与 linux 一致，libc 为 musl
            "--target=arm64-linux-gcc",
            # 产物形态：默认 static-only，共享库须显式开（FFmpeg 按 soname 链 libvpx）
            "--enable-shared",
            "--disable-static",
            "--enable-pic",
            # 编解码器：VP8/VP9 双向
            "--enable-vp8",
            "--enable-vp9",
            "--enable-multithread",
            # 裁剪：示例/工具/文档/单测都不进包（单测另需下载数百 MB 测试数据）
            "--disable-examples",
            "--disable-tools",
            "--disable-docs",
            "--disable-install-docs",
            "--disable-unit-tests",
            "--disable-dependency-tracking",
        ]
        _configure = os.path.join(self.source_folder, "configure")
        _args = " ".join('"{}"'.format(a) for a in args)
        os.makedirs(self.build_folder, exist_ok=True)
        # out-of-tree 构建：cwd 为 build_folder，configure 用源码目录绝对路径
        self.run('"{}" {}'.format(_configure, _args), cwd=self.build_folder)
        self.run("make -j{}".format(self._jobs()), cwd=self.build_folder)

    def package(self):
        self.run("make install", cwd=self.build_folder)
        for _lic in ("LICENSE", "PATENTS"):
            copy(self, _lic, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 与被 exec 的可执行文件都有代码签名。
        # libvpx 的 install 用 `install` 复制产物（build/make/Makefile），复制会破坏链接器自签，
        # 故统一重签 lib/ 下 .so 与 bin/ 下真实 ELF。
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = os.path.join(self._HNP_BIN, "llvm-objcopy")
        signer = os.path.join(self._HNP_BIN, "binary-sign-tool")
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["vpx"]
        self.cpp_info.set_property("pkg_config_name", "vpx")
        self.cpp_info.set_property("cmake_file_name", "libvpx")
        self.cpp_info.set_property("cmake_target_name", "libvpx::libvpx")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
