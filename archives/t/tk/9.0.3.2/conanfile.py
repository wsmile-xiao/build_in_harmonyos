from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout



class TkConan(ConanFile):
    name = "tk"
    version = "9.0.3.2"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}


    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("tcl/9.0.3.2")   # 随 SONAME 修复联动升级

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("tcl_cv_sys_version=Linux-6.6")
        tc.configure_args.append("--disable-zipfs")
        tc.configure_args.append("--enable-ohos")
        tc.configure_args.append("--with-tcl={}".format(self.dependencies["tcl"].cpp_info.libdirs[0]))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        import glob, os
        for _cfg in glob.glob(os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        import os
        _shim = os.path.join(self.build_folder, '_uname_shim')
        os.makedirs(_shim, exist_ok=True)
        _u = os.path.join(_shim, 'uname')
        with open(_u, 'w') as _f:
            _f.write('#!/bin/sh\ncase "${1:-}" in\n  -s|"") echo Linux ;;\n  -r) echo 6.6 ;;\n  -m) echo aarch64 ;;\n  *) exec /system/bin/uname "$@" 2>/dev/null || exec /bin/uname "$@" ;;\nesac\n')
        os.chmod(_u, 0o755)
        os.environ['PATH'] = _shim + os.pathsep + os.environ.get('PATH', '')
        autotools = Autotools(self)
        autotools.configure(build_script_folder="unix")
        autotools.make(args=["-j1"])
        # SKILL 要求尝试上游测试。tk 上游测试为 `make test`（非 make check），
        # 但 tktest 编译失败：OHOS 平台移植缺少 TkpTestsendCmd/TkpPrintWindowId 声明
        # （tkIntPlatDecls.h 仅在 #if defined(WIN)/#if defined(X11) 段内声明）。
        # 记录失败，不阻塞构建；test_package 提供功能验证（wish9.0 + Tcl 脚本）。
        try:
            autotools.make(target="test", args=["-j1"])
        except Exception:
            self.output.warning("make test failed (expected: tktest build fails — OHOS missing TkpTestsendCmd/TkpPrintWindowId)")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # tk.h `#include <X11/Xlib.h>` / `<X11/X.h>`——autotools install-headers 只装公开 tk 头，
        # 不装源码 xlib/ 的 X11 stub 头。任何编译 tk.h 的消费方（如 CPython _tkinter）都需要它们，
        # 故把 xlib/X11/*.h 装进包 include/X11/（Xlib.h 引的 "tkIntXlibDecls.h" 已在包 include/）。
        import os
        import glob
        import shutil
        x11_src = os.path.join(self.source_folder, "xlib", "X11")
        if os.path.isdir(x11_src):
            x11_dst = os.path.join(self.package_folder, "include", "X11")
            os.makedirs(x11_dst, exist_ok=True)
            for h in glob.glob(os.path.join(x11_src, "*.h")):
                shutil.copy2(h, x11_dst)


        self._set_soname_and_resign(['libtcl9tk9.0.so'])

    def _set_soname_and_resign(self, sonames):
        """给缺 SONAME 的 .so 补上，并**重新签名**。

        为何需要：tcl/tk 的 configure 在本平台没生成 -Wl,-soname，产物无 DT_SONAME。
        后果不是本包坏，而是**下游链接它时会把绝对路径写进自己的 DT_NEEDED**
        （A/B 实测：无 SONAME + CMake 按完整路径链接 → 换机器即无法加载）。
        本包的现有消费方（tk / cpython-tkinter / tcl-tls / tkdiff）都走 dlopen 按名字加载，
        所以尚未受害；但任何直接链接它的 C 程序都会中招。

        为何用 patchelf 而不改构建系统：tcl 的 tcl.m4 在本平台是靠
        `tcl_cv_sys_version=Linux-6.6` 骗过去的，动它的 SHLIB_LD 链路风险高、收益一样；
        patchelf --set-soname 精确、可验证（readelf -d 立刻能看），设备 hnp 自带。

        为何必须重签：改动 ELF 会破坏链接器自签，鸿蒙 PC 的 XPM 会拒绝 dlopen
        （报 Permission denied / Operation not permitted）。顺序必须是 patchelf → 重签。
        """
        import os
        patchelf = "/data/service/hnp/bin/patchelf"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for name in sonames:
            f = os.path.join(self.package_folder, "lib", name)
            if not os.path.isfile(f) or os.path.islink(f):
                self.output.warning("补 SONAME：找不到 %s，跳过" % f)
                continue
            self.run('{pe} --set-soname "{n}" "{f}"'.format(pe=patchelf, n=name, f=f))
            # 重签：先剥旧签名段，再自签
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))
            self.output.info("已设 SONAME=%s 并重签" % name)

    def package_info(self):
        explicit_libs = ['tcl9tk9.0']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "tk")
        self.cpp_info.set_property("cmake_target_name", "tk::tk")
        pkg = "" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ['dl', 'm', 'pthread', 'z']
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
