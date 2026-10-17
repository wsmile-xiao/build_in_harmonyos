#!/usr/bin/env python3
"""Conan recipe — sassc 3.6.2 (libsass 官方命令行编译器).

sassc 是 libsass（Sass 编译器 C++ 库）的 CLI 封装：纯 Makefile 构建（单源
sassc.c），静态链接 libsass.a 产出 bin/sassc。依赖链 sassc → libsass/3.6.5
（main/ohpcd 已发布，零外部依赖）→ 无。

OHOS 适配（0001 补丁 + 构建对接）：
- SASS_LIBSASS_PATH 指向 libsass conan 包（含 lib/libsass.a + include/sass
  头，正好是上游 Makefile 期望的布局）
- 0001 补丁：去掉 macOS 专用 -Wl,-undefined,error（lld 报 unknown argument）；
  去掉 $(SASSC_EXE) 对 libsass 源码树的 make -C 依赖、install 的
  libsass-install（libsass 由 conan 包提供，不再源码构建）
- LDLIBS 覆盖 -lstdc++ → -lc++（OHOS 用 libc++，系统无 libstdc++）
- 可执行文件 OHOS codesign（E077）
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SasscConan(ConanFile):
    name = "sassc"
    version = "3.6.2"
    description = "sassc — command line compiler for SCSS/Sass (libsass CLI)"
    license = "MIT"
    homepage = "https://github.com/sass/sassc"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libsass/3.6.5 已在 main/ohpcd 发布，产物（lib/libsass.a + include/sass）
        # 正好满足 sassc Makefile 的 SASS_LIBSASS_PATH 布局，无需再适配。
        self.requires("libsass/3.6.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compilers(self):
        tc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = tc.get("c") or "clang"
        cxx = tc.get("cpp") or tc.get("cxx") or "clang++"
        return cc, cxx

    def _make_cmd(self, prefix, target=""):
        cc, cxx = self._compilers()
        libsass_pkg = self.dependencies["libsass"].package_folder
        return ('make {target} CC="{cc}" CXX="{cxx}" SASS_LIBSASS_PATH="{lp}" '
                'LDLIBS="-lm -lc++ -ldl" PREFIX="{pkg}" DESTDIR=""').format(
                    target=target, cc=cc, cxx=cxx, lp=libsass_pkg, pkg=prefix)

    def build(self):
        apply_conandata_patches(self)
        # 构建 bin/sassc（静态链接 libsass.a；-lstdc++ 覆盖为 -lc++）
        self.run(self._make_cmd(""), cwd=self.source_folder, env="conanbuild")

    def package(self):
        # make install 把 bin/sassc 装到 package_folder/bin（0001 已去掉
        # libsass-install；install 规则用 $(INSTALL) -D 自动建 bin/）
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        self.run(self._make_cmd(self.package_folder, "install"),
                 cwd=self.source_folder, env="conanbuild")
        self._sign_binary()

    def _sign_binary(self):
        # OHOS 可执行文件需 codesign（E077，同 glib/dee 的共享库签名模式）
        exe = os.path.join(self.package_folder, "bin", "sassc")
        if not os.path.isfile(exe):
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip codesign (cross/SDK env)")
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.isfile(objcopy):
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=exe))
        self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=exe))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
