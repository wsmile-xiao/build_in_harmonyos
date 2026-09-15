from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout


class CairoConan(ConanFile):
    name = "cairo"
    version = "1.18.4.1"
    exports_sources = "patches/*"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}


    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        # 设备到 gitlab/cairographics 下大 tarball 常超时。优先用预推到 ~/Download 的暂存件（免网络）；
        # 无暂存件则回退在线下载（conandata=cairographics.org 官方 release，比 gitlab 47MB 归档更稳）。
        import os
        staged = os.path.expanduser("~/Download/cairo-1.18.4.tar.xz")
        if os.path.isfile(staged):
            from conan.tools.files import unzip, check_sha256
            check_sha256(self, staged, self.conan_data["sources"]["sha256"])
            unzip(self, staged, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("pixman/0.46.4")
        self.requires("libpng/1.6.58")
        self.requires("freetype/2.14.3")
        # 2.18.1 的 libfontconfig.so 的 DT_NEEDED 烤着构建机的 conan cache 绝对路径
        # （指向 expat/2.8.2 —— 那版 expat 的 .so 无 SONAME），换机器必然加载失败。
        # 2.18.1.1 是同一份配方只改了 expat 的 pin 后重建的干净版本。
        # 注：requires 是 minor_mode（fontconfig/2.18.Z），故本次改动**不改变 cairo 的 package_id**，
        # 已发布的 cairo 二进制无需重建，只需新 recipe revision 让消费方解析到干净的 fontconfig。
        self.requires("fontconfig/2.18.1.1")
        self.requires("zlib/1.3.1.1")
        # X11 后端（gtk X11 后端需要 cairo-xlib surface）：
        # 制品仓 cairo 配方 xlib=disabled，本本地配方启用 xlib surface，
        # X 客户端库与 gtk X11 后端同源（libx11/6.4.0 等，均已发布 OHOS binary）
        # libx11 用 override 压掉 libxrender/0.9.12 配方的 libx11/1.8.13 传递 pin
        # （libxext/6.4.0 同族精确 pin 6.4.0，二者无法共存，统一 6.4.0 覆盖）
        self.requires("libx11/6.4.0", override=True)
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxrender/0.9.12", transitive_headers=True, transitive_libs=True)
        # 一并启用 glib（cairo-gobject）：本地 cairo 包自带
        # CAIRO_HAS_GOBJECT_FUNCTIONS 宏，gtk 配方的 cairo 头覆盖逻辑可跳过，
        # 避免 cairo-gobject（制品仓无 xlib）的头覆盖掉本包的 XLIB 宏
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def build_requirements(self):
        # 制品仓 cairo 配方依赖 CI 全局 meson；本地重建需显式 tool_requires（gtk 配方同款）
        self.tool_requires("meson/1.11.0")

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # 依赖全部经 conan pkg-config 提供：pixman-1 / libpng / freetype2 / fontconfig / zlib。
        # 找不到就报错，禁止 meson 偷偷下 wrap 子项目（自包含回退，非本路线）。
        tc.project_options["wrap_mode"] = "nodownload"
        # 启用（依赖已由 conan 提供）
        tc.project_options["png"] = "enabled"          # png + svg 表面
        tc.project_options["freetype"] = "enabled"
        tc.project_options["fontconfig"] = "enabled"
        tc.project_options["zlib"] = "enabled"         # script/ps/pdf/xml 表面
        # X11 后端：xlib surface 启用（gtk X11 后端依赖 cairo-xlib.pc）
        tc.project_options["xlib"] = "enabled"
        tc.project_options["xcb"] = "disabled"
        tc.project_options["xlib-xcb"] = "disabled"
        tc.project_options["quartz"] = "disabled"
        tc.project_options["dwrite"] = "disabled"
        tc.project_options["lzo"] = "disabled"
        tc.project_options["spectre"] = "disabled"     # libspectre
        tc.project_options["symbol-lookup"] = "disabled"  # binutils/libbfd
        tc.project_options["glib"] = "enabled"        # 本地重建启用 cairo-gobject（见 requirements 注释）
        tc.project_options["tests"] = "auto"
        tc.generate()
        # conan MesonToolchain 不把 tools.build:compiler_executables 的 ar/ranlib 写进 native file，
        # meson 便按裸名 llvm-ar 探归档器，而 clang 工具链在 /data/service/hnp/bin，PATH 上无 llvm-ar
        # 时 configure 失败。直接把 ar/ranlib 全路径注入 conan_meson_native.ini，不污染 PATH。
        import os as _os
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar = _ce.get("ar"); _rl = _ce.get("ranlib")
        # CI profile 仅提供 c/cpp，未给 ar/ranlib：从 c 编译器同目录推导 llvm-ar/llvm-ranlib 全路径。
        if not _ar:
            _cc = _ce.get("c") or ""
            _bindir = _os.path.dirname(_cc) if _os.path.sep in _cc else ""
            if _bindir:
                _cand = _os.path.join(_bindir, "llvm-ar")
                if _os.path.isfile(_cand):
                    _ar = _cand
                    _rlc = _os.path.join(_bindir, "llvm-ranlib")
                    if _os.path.isfile(_rlc):
                        _rl = _rlc
        _nf = _os.path.join(self.generators_folder, "conan_meson_native.ini")
        if _ar and _os.path.isfile(_nf):
            with open(_nf) as _f: _c = _f.read()
            if "\nar =" not in _c and "[binaries]" in _c:
                _ins = "[binaries]\nar = '%s'\n" % _ar
                if _rl: _ins += "ranlib = '%s'\n" % _rl
                _c = _c.replace("[binaries]\n", _ins, 1)
                with open(_nf, "w") as _f: _f.write(_c)

    def build(self):
        # CI 环境已全局提供 meson/ninja，无需再手动前置设备侧 usr/local/bin、hnp/bin 到 PATH。
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        self._sign_shared_libs()



    def _sign_shared_libs(self):
        # meson install 重写 rpath 会改动链接后的 .so → 链接器自签失效，OHOS XPM dlopen 报 Permission denied。
        # 剥旧 .codesign + binary-sign-tool -selfSign 1 重签（ML-0043 场景）。
        import glob, os
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        explicit_libs = ['cairo']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        # cairo 公开头装在 include/cairo/（cairo.h 等）。消费方 #include <cairo.h> 须 -I.../include/cairo。
        self.cpp_info.includedirs = ["include/cairo", "include"]
        self.cpp_info.set_property("cmake_file_name", "cairo")
        self.cpp_info.set_property("cmake_target_name", "cairo::cairo")
        pkg = "cairo" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ['m', 'pthread']
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
