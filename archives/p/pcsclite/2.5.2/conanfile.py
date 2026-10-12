#!/usr/bin/env python3
"""Conan recipe — pcsclite 2.5.2 (pcsc-lite, PC/SC smart-card middleware).

Upstream: https://github.com/LudovicRousseau/PCSC (tag 2.5.2, sha256-verified).

IMPORTANT — build system note:
  pcsc-lite 2.5.2 upstream has MIGRATED from autotools to Meson (the tarball
  contains meson.build/meson.options, NO configure.ac). This recipe therefore
  uses MesonToolchain, mirroring the repo precedent archives/a/aml/1.0.0.

Delivered on HarmonyOS PC (arm64, OHOS aarch64):
  - lib/libpcsclite.so.1 (SCard* facade, dlopen delegate) +
    lib/libpcsclite_real.so.1 (client core) [+ libpcscspy.so.0 spy shim],
    or the static counterparts (libpcsclite.a = real client impl, no dlopen)
  - include/PCSC/{winscard,pcsclite,ifdhandler,reader,wintypes,debuglog}.h
  - lib/pkgconfig/libpcsclite.pc

Deliberately NOT built (-Dpcscd=false, see patches/0001+0002):
  - pcscd daemon: needs pthread_cancel(3), which OHOS musl libc does not
    provide (ld.lld: undefined symbol: pthread_cancel, from eventhandler.c);
    its udev/libusb/systemd/polkit integration is equally unavailable on OHOS.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, rmdir
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class PcscliteConan(ConanFile):
    name = "pcsclite"
    version = "2.5.2"
    description = ("pcsc-lite — PC/SC smart card middleware: SCard* client "
                   "library and headers (winscard API)")
    license = "BSD-3-Clause"
    homepage = "https://pcsc-lite.apdu.fr/"
    url = "https://github.com/LudovicRousseau/PCSC"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external runtime requirements: libc + pthreads (+ libdl stub) only.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # OHOS 裁剪面：pcscd 守护进程（musl 无 pthread_cancel）及其
        # udev/libusb/systemd/polkit 集成全部关闭，只交付客户端库+头文件
        tc.project_options["pcscd"] = "false"
        tc.project_options["libudev"] = "false"
        tc.project_options["libusb"] = "false"
        tc.project_options["libsystemd"] = "false"
        tc.project_options["polkit"] = "false"
        tc.project_options["usb"] = "false"
        tc.project_options["serial"] = "false"
        tc.generate()
        # conan MesonToolchain 不把 tools.build:compiler_executables 的 ar/ranlib 写进 native file，
        # meson 便按裸名 llvm-ar 探归档器，而 clang 工具链在 /data/service/hnp/bin，PATH 上无 llvm-ar
        # 时 configure 失败。直接把 ar/ranlib 全路径注入 conan_meson_native.ini，不污染 PATH。
        # （同款先例：cairo/1.18.4、pixman/0.46.4、aml/1.0.0）
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar = _ce.get("ar"); _rl = _ce.get("ranlib")
        # CI profile 仅提供 c/cpp，未给 ar/ranlib：从 c 编译器同目录推导 llvm-ar/llvm-ranlib 全路径。
        if not _ar:
            _cc = _ce.get("c") or ""
            _bindir = os.path.dirname(_cc) if os.path.sep in _cc else ""
            if _bindir:
                _cand = os.path.join(_bindir, "llvm-ar")
                if os.path.isfile(_cand):
                    _ar = _cand
                    _rlc = os.path.join(_bindir, "llvm-ranlib")
                    if os.path.isfile(_rlc):
                        _rl = _rlc
        _nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if _ar and os.path.isfile(_nf):
            with open(_nf) as _f:
                _c = _f.read()
            if "\nar =" not in _c and "[binaries]" in _c:
                _ins = "[binaries]\nar = '%s'\n" % _ar
                if _rl:
                    _ins += "ranlib = '%s'\n" % _rl
                _c = _c.replace("[binaries]\n", _ins, 1)
                with open(_nf, "w") as _f:
                    _f.write(_c)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        # 上游许可证（BSD-3-Clause 三条款文本，COPYING）
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        # 裁掉非 OHOS 消费面：bin/pcsc-spy（perl 脚本）、share/{doc,man,metainfo}
        # —— daemon/spy 附件与 OHOS 库消费无关，且 bin/ 内无可执行二进制
        rmdir(self, os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        # 头文件安装于 include/PCSC/（与上游 libpcsclite.pc 的 subdirs=PCSC 一致），
        # 消费者 #include <winscard.h>；winscard.h 内部 #include <pcsclite.h> 同目录可解析
        self.cpp_info.includedirs = ["include/PCSC"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["pcsclite"]
        # meson 依赖闭包：threads + dl（musl 下均为 libc 内建/stub）
        self.cpp_info.system_libs = ["pthread", "dl"]
        self.cpp_info.set_property("pkg_config_name", "libpcsclite")
