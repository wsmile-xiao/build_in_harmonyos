from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class CairommConan(ConanFile):
    name = "cairomm"
    version = "1.18.0"
    description = "C++ wrapper for the cairo graphics library"
    license = "LGPL-2.0-or-later"
    homepage = "https://www.cairographics.org/cairomm/"
    url = ""

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # cairomm meson.build: sigc++-3.0 >= 3.0.0（libsigc/3.0.6，pkg-config sigc++-3.0）
        # cairo >= 1.14.0（cairo/1.18.4，pkg-config cairo）
        self.requires("cairo/1.18.4")
        self.requires("libsigc/3.0.6")
        # R03 运行期修复：本地 fontconfig/2.18.1 二进制损坏（libfontconfig.so.1 的
        # DT_NEEDED 烤死构建机 conan cache 绝对路径，本机无 expat9fb72708ad085），
        # 2.18.1.1 为同配方干净重建（cairo 注释：requires minor_mode 不改变 package_id，
        # 已发布 cairo 二进制无需重建）。override 强制全图解析干净 fontconfig/2.18.1.1。
        self.requires("fontconfig/2.18.1.1", override=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # 优先用预推到 ~/Download 的暂存件（免网络，R03 已核验 sha1/sha256/大小/归档根）；
        # 无暂存件则回退在线下载（cairographics.org 官方 release）。
        import os
        staged = os.path.expanduser("~/Download/cairomm-1.18.0.tar.xz")
        if os.path.isfile(staged):
            from conan.tools.files import unzip, check_sha256
            check_sha256(self, staged, self.conan_data["sources"]["sha256"])
            unzip(self, staged, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # 依赖全部经 conan pkg-config 提供：sigc++-3.0 / cairo。
        tc.project_options["wrap_mode"] = "nodownload"
        # 测试需 Boost Test + fontconfig（上游 can_test 门），禁用；示例/文档/维护模式均关。
        tc.project_options["build-examples"] = "false"
        tc.project_options["build-tests"] = "false"
        tc.project_options["build-documentation"] = "false"
        tc.project_options["maintainer-mode"] = "false"
        tc.generate()
        # conan MesonToolchain 不把 tools.build:compiler_executables 的 ar/ranlib 写进
        # native file，meson 按裸名 llvm-ar 探归档器会失败；直接注入全路径（同 cairo 配方）。
        import os as _os
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar = _ce.get("ar"); _rl = _ce.get("ranlib")
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
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # meson install 重写 rpath 会改动链接后的 .so → 链接器自签失效，OHOS dlopen 报
        # Permission denied。剥旧 .codesign + binary-sign-tool -selfSign 1 重签（ML-0043 场景）。
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
        # 上游库名 libcairomm-1.16.so.1.4.0；公开头 include/cairomm-1.16/cairomm/，
        # 构建期生成的 cairommconfig.h 在 lib/cairomm-1.16/include（mm 系列惯例）。
        self.cpp_info.libs = ["cairomm-1.16"]
        self.cpp_info.includedirs = ["include/cairomm-1.16", "lib/cairomm-1.16/include"]
        self.cpp_info.set_property("cmake_file_name", "cairomm")
        self.cpp_info.set_property("cmake_target_name", "cairomm::cairomm")
        self.cpp_info.set_property("pkg_config_name", "cairomm-1.16")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
