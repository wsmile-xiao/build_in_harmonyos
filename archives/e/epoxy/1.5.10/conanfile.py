#!/usr/bin/env python3
"""Conan recipe — epoxy 1.5.10 (meson, GL/EGL function-pointer dispatch library).

OHOS 适配要点：
  - 无 X11/GLX：meson 传 -Dx11=false -Dglx=no；EGL 头/库来自 OHOS SDK sysroot。
  - 运行时 dlopen 名称补丁（0001/0002）：OHOS 只有无版本号的 libEGL.so /
    libGLESv2.so / libGLESv3.so，且无桌面 GL。
  - 共享库按 HarmonyOS 要求 codesign（与 atk/pango 同款逻辑）。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class EpoxyConan(ConanFile):
    name = "epoxy"
    version = "1.5.10"
    description = "Modern libepoxy — GL/EGL function-pointer dispatch library (gtk+ dependency)"
    license = "MIT"
    homepage = "https://github.com/anholt/libepoxy"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        # R39: 官方源 download.gnome.org 的 tar.xz，basename 带 .tar.xz 扩展名，
        # get() 按扩展名正确解压（无需显式 filename，E276 仅针对 codeload 无扩展名场景）。
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
        )

    def generate(self):
        # Fix: OHOS SDK lld needs libxml2.so.16 from SDK llvm/lib dir (same as harfbuzz/atk).
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc and os.path.sep in cc:
            cc_real = os.path.realpath(cc)
            llvm_dir = os.path.dirname(os.path.dirname(cc_real))
            llvm_lib = os.path.join(llvm_dir, "lib")
            if os.path.isdir(llvm_lib):
                current = os.environ.get("LD_LIBRARY_PATH", "")
                os.environ["LD_LIBRARY_PATH"] = llvm_lib + (":" + current if current else "")
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # OHOS 无 X11/GLX；GLX 需要 <GL/glx.h> 而 OHOS sysroot 没有。
        tc.project_options["x11"] = "false"
        tc.project_options["glx"] = "no"
        # EGL 由 OHOS SDK sysroot 提供，auto 即可（非 windows/darwin → 启用）。
        tc.project_options["egl"] = "auto"
        # 上游测试套件需 X11/真机 GL 上下文，构建阶段不跑（test_package 真实验证 API）。
        tc.project_options["tests"] = "false"
        tc.project_options["docs"] = "false"
        tc.generate()
        self._inject_meson_binaries()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if self.settings.os == "OHOS":
            self._sign_shared_libs()

    def _inject_meson_binaries(self):
        """MesonToolchain 不写 ar/ranlib/pkg-config，meson 依赖它们做库/依赖探测。"""
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        cc = ce.get("c") or ""
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        if not ar and bindir:
            for name in ("llvm-ar", "ar"):
                cand = os.path.join(bindir, name)
                if os.path.isfile(cand):
                    ar = cand
                    break
        if not rl and bindir:
            for name in ("llvm-ranlib", "ranlib"):
                cand = os.path.join(bindir, name)
                if os.path.isfile(cand):
                    rl = cand
                    break
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            with open(nf, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            extras = []
            if ar and "\nar =" not in content:
                extras.append(f"ar = '{ar}'")
            if rl and "\nranlib =" not in content:
                extras.append(f"ranlib = '{rl}'")
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                extras.append(f"pkg-config = '{pkg_config}'")
            if not extras:
                continue
            content = content.replace(
                "[binaries]\n", "[binaries]\n" + "\n".join(extras) + "\n", 1
            )
            with open(nf, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        candidates_objcopy = [
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "",
        ]
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            candidates_objcopy.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates_objcopy if p and os.path.isfile(p)), None)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign")
            return
        for so in sos:
            if os.path.islink(so):
                continue
            if objcopy:
                self.run(f'{objcopy} --remove-section .codesign "{so}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{so}" -outFile "{so}" -selfSign 1')

    def package_info(self):
        self.cpp_info.libs = ["epoxy"]
        self.cpp_info.set_property("cmake_file_name", "epoxy")
        self.cpp_info.set_property("cmake_target_name", "epoxy::epoxy")
        self.cpp_info.set_property("pkg_config_name", "epoxy")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl"]
