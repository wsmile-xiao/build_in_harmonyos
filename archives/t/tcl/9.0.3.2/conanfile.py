from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout


class TclConan(ConanFile):
    name = "tcl"
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
        # Conan 2.x: conandata.yml auto-exported; patches dir exported if present
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("tcl_cv_sys_version=Linux-6.6")
        tc.configure_args.append("--disable-zipfs")
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
        autotools.make(target="binaries libraries", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(target="install-binaries install-libraries install-headers")
        self._relocate_tclconfig()
        self._set_soname_and_resign(['libtcl9.0.so'])

    def _relocate_tclconfig(self):
        # 【手加，非 skill 生成】tclConfig.sh 里烤死了绝对路径：TCL_SRC_DIR/TCL_BUILD_* 指向已消失的
        # 构建缓存目录，TCL_*_SPEC 是 --prefix=/ 拼出的字面 //lib //include。消费方（如 tk，用
        # $(TCL_SRC_DIR)/generic 取头、-L//lib -ltclstub 链接）会拿到坏路径。重定位为 ${TCL_ROOT}
        # 相对（package_info 把 TCL_ROOT 设成消费方缓存里本包的实际目录）。
        import os
        cfg = os.path.join(self.package_folder, "lib", "tclConfig.sh")
        if not os.path.isfile(cfg):
            return
        with open(cfg, encoding="utf-8") as f:
            text = f.read()
        # 构建缓存绝对路径 → ${TCL_ROOT}（先长后短，避免短前缀先匹配）
        for _p, _r in sorted(
            [(self.build_folder, "${TCL_ROOT}/lib"), (self.source_folder, "${TCL_ROOT}")],
            key=lambda x: -len(x[0]),
        ):
            text = text.replace(_p, _r)
        # --prefix=/ 的字面 //lib //include
        text = text.replace("-I//include", "-I${TCL_ROOT}/include")
        text = text.replace("-L//lib", "-L${TCL_ROOT}/lib")
        text = text.replace("'//lib/", "'${TCL_ROOT}/lib/")
        text = text.replace("TCL_PREFIX='/'", "TCL_PREFIX='${TCL_ROOT}'")
        text = text.replace("TCL_EXEC_PREFIX='/'", "TCL_EXEC_PREFIX='${TCL_ROOT}'")
        with open(cfg, "w", encoding="utf-8") as f:
            f.write(text)
        # tk 用 $(TCL_SRC_DIR)/generic、/unix 取 tcl 头，而包里头装在 include/ → 建软链兜住
        for _sub in ("generic", "unix"):
            _link = os.path.join(self.package_folder, _sub)
            if not os.path.lexists(_link):
                os.symlink("include", _link)

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
        explicit_libs = ['tcl9.0']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "tcl")
        self.cpp_info.set_property("cmake_target_name", "tcl::tcl")
        pkg = "" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ['dl', 'm', 'pthread', 'z']
        # 消费方 source 重定位后的 tclConfig.sh 时，${TCL_ROOT} 展开为本包在其缓存的实际目录
        self.buildenv_info.define("TCL_ROOT", self.package_folder)
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
