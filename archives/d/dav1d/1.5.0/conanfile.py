#!/usr/bin/env python3
"""Conan recipe — dav1d 1.5.0 (meson)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout


class Dav1dConan(ConanFile):
    name = "dav1d"
    version = "1.5.0"
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
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # 禁止 meson 偷偷下 wrap 子项目：依赖一律走 conan，缺了就当场报错而非静默换实现。
        tc.project_options["wrap_mode"] = "nodownload"
        # musl 上必须用 gnu 方言，不能用严格 c99：
        # meson 的 has_function 检测用 `-std=c99` 编译，严格 C99 不自动定义
        # _POSIX_C_SOURCE，而 clock_gettime 是 POSIX 而非 ISO C，
        # musl 的 time.h 就**不声明它** → 检测失败 → dav1d 的 meson.build 直接
        # `error('clock_gettime not found')`。
        # glibc 默认开 _DEFAULT_SOURCE 所以看不到这个问题，musl 严格得多。
        # 实测：设备 libc 里 clock_gettime 与 __clock_gettime64 两个符号都在，
        # 手写程序带不带 _GNU_SOURCE 都能编链 —— 缺的只是**声明**，不是实现。
        tc.project_options["c_std"] = "gnu99"
        tc.project_options["enable_tools"] = "false"
        tc.project_options["enable_tests"] = "false"
        tc.project_options["enable_examples"] = "false"
        tc.generate()
        self._inject_meson_archiver()

    def _inject_meson_archiver(self):
        # 【OHOS 必需】conan 的 MesonToolchain 不把 tools.build:compiler_executables 里的 ar/ranlib
        # 写进 native file，meson 便按**裸名** llvm-ar 探归档器；而 clang 工具链在 /data/service/hnp/bin，
        # PATH 上没有 llvm-ar 时 meson configure 直接失败。这里把 ar/ranlib 全路径注入
        # conan_meson_native.ini，不污染 PATH。（cairo 1.18.4 实证）
        import os
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar, _rl = _ce.get("ar"), _ce.get("ranlib")
        # profile 通常只给 c/cpp：从 c 编译器同目录推导 llvm-ar / llvm-ranlib 全路径。
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
        if not (_ar and os.path.isfile(_nf)):
            return
        with open(_nf, encoding="utf-8") as _f:
            _c = _f.read()
        if "\nar =" in _c or "[binaries]" not in _c:
            return
        _ins = "[binaries]\nar = '%s'\n" % _ar
        if _rl:
            _ins += "ranlib = '%s'\n" % _rl
        with open(_nf, "w", encoding="utf-8") as _f:
            _f.write(_c.replace("[binaries]\n", _ins, 1))

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
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
        explicit_libs = ['dav1d']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "dav1d")
        self.cpp_info.set_property("cmake_target_name", "dav1d::dav1d")
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
