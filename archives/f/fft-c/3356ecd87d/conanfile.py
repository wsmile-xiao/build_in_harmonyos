#!/usr/bin/env python3
"""Conan recipe — fft-c 3356ecd87d.

上游 adis300/fft-c 是一个纯 C 单文件库（fft.c + fft.h，FFTPACK 的易用封装），
无任何构建系统（仅一个供演示用的 Makefile 目标 `example`）。本配方直接用
OHOS 工具链编译 fft.c 产出库，并携带 0001-fix-fft-backward-double-scaling.patch
修复上游 fft_backward 的 ×n 双重缩放 bug（见 patches/conandata 注释与
reports/upstream_test_ledger.md）。

R38：纯库类型（无 bin 产物），不需要 commands.json。
"""
import os
import shlex

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class FftcConan(ConanFile):
    name = "fft-c"
    version = "3356ecd87d"
    description = "User-friendly wrapper around FFTPACK real FFT routines"
    license = "MIT"
    homepage = "https://github.com/adis300/fft-c"
    url = "https://github.com/adis300/fft-c"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URL 无 .tar.gz 扩展名，必须显式给 filename 让 conan
        # 按扩展名识别归档类型（否则按 zip 解压报 BadZipFile，aes-stream 同款）。
        src = dict(self.conan_data["sources"])
        src.setdefault("filename", "fft-c-3356ecd87d.tar.gz")
        get(self, **src, strip_root=True, verify=True)

    def build(self):
        apply_conandata_patches(self)
        cc = self._resolve_compiler()
        cflags = self._cflags()
        src_dir = self.source_folder
        obj = os.path.join(self.build_folder, "fft.o")
        cmd = [cc, "-c"] + cflags + ["-I" + src_dir,
                                     os.path.join(src_dir, "fft.c"), "-o", obj]
        self.run(" ".join(shlex.quote(t) for t in cmd), cwd=self.build_folder)

        ar = self._resolve_tool(self._conf_tools().get("ar"), "llvm-ar")
        static_lib = os.path.join(self.build_folder, "libfft_c.a")
        self.run("{} rcs {} {}".format(shlex.quote(str(ar)), shlex.quote(static_lib),
                                       shlex.quote(obj)), cwd=self.build_folder)
        if self.options.shared:
            ld = self._resolve_tool(self._conf_tools().get("c"), "clang")
            shared_lib = os.path.join(self.build_folder, "libfft_c.so")
            # 必须带 -Wl,-soname：无 DT_SONAME 时下游链接器会把本库绝对路径写进
            # 消费方 DT_NEEDED，烤死包目录哈希（L5a 门禁直接拦截）。
            self.run("{} -shared -fPIC -Wl,-soname,libfft_c.so -o {} {}".format(
                shlex.quote(str(ld)), shlex.quote(shared_lib), shlex.quote(obj)),
                cwd=self.build_folder)

    def package(self):
        copy(self, "fft.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        for lib in ("libfft_c.a", "libfft_c.so"):
            for base in (self.build_folder,):
                p = os.path.join(base, lib)
                if os.path.exists(p):
                    copy(self, lib, src=base,
                         dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        self._sign_binaries()

    def package_info(self):
        self.cpp_info.libs = ["fft_c"]
        self.cpp_info.set_property("cmake_file_name", "fft_c")
        self.cpp_info.set_property("cmake_target_name", "fft_c::fft_c")

    # ---- helpers ----

    def _resolve_compiler(self):
        compilers = self._conf_tools()
        return self._resolve_tool(compilers.get("c") or compilers.get("cc"), "clang")

    def _resolve_tool(self, tool, fallback):
        if tool:
            return str(tool)
        return fallback

    def _conf_tools(self):
        return self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict) or {}

    def _cflags(self):
        flags = ["-O2", "-fPIC"]
        if self.settings.build_type == "Debug":
            flags = ["-O0", "-g", "-fPIC"]
        for f in self.conf.get("tools.build:cflags", default=[], check_type=list) or []:
            flags.append(str(f))
        return flags

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM：dlopen 的 .so 需要代码签名（内容哈希存 .codesign 节）。
        # 两个工具只在 OHOS 设备 /data/service/hnp/bin 下存在；非 OHOS 直接返回。
        if self.settings.os != "OHOS":
            return
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "*.so"))
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))