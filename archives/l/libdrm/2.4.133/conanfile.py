#!/usr/bin/env python3
"""Conan recipe — libdrm 2.4.133 (Meson).

Direct Rendering Manager library, MIT, https://dri.freedesktop.org/

R26: ships static libraries by default (system-name library isolation).
The full upstream test suite (10 tests) runs on a shared-library build
tree inside build(): symbols-check compares exported symbols against the
upstream whitelist, which only holds for shared objects — against static
archives GNU nm -gP exposes every internal global and the comparison is
meaningless (and the stock parser chokes on archive member headers).
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibdrmConan(ConanFile):
    name = "libdrm"
    version = "2.4.133"
    description = "Direct Rendering Manager library for Linux"
    license = "MIT"
    homepage = "https://dri.freedesktop.org/"
    url = "https://dri.freedesktop.org/libdrm/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # R26: System-name libraries default to static
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        self._inject_meson_archiver()

    def _inject_meson_archiver(self):
        """Name the SDK archiver explicitly; CI does not put it on PATH.

        MesonToolchain.generate() may or may not write an ``ar =`` line into
        the native file (depends on whether ``ar`` is in
        ``tools.build:compiler_executables`` conf).  Either way, we must
        ensure the full SDK path is present so Meson does not fall back to
        the bare name ``llvm-ar`` (which is not on PATH on CI workers).
        """
        compiler_exes = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = compiler_exes.get("ar")
        ranlib = compiler_exes.get("ranlib")
        if not ar:
            compiler = compiler_exes.get("c", "")
            bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
            candidate = os.path.join(bindir, "llvm-ar") if bindir else ""
            if candidate and os.path.isfile(candidate):
                ar = candidate
                ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                ranlib = ranlib_candidate if os.path.isfile(ranlib_candidate) else None
        if not ar:
            # Fallback: check known OHOS SDK locations
            for sdk_dir in [
                "/data/service/hnp/bin",
                "/usr/local/bin",
                "/usr/bin",
            ]:
                candidate = os.path.join(sdk_dir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(sdk_dir, "llvm-ranlib")
                    ranlib = ranlib_candidate if os.path.isfile(ranlib_candidate) else None
                    break
        if not ar:
            raise ConanException("Unable to locate an archiver for Meson")

        ar_path = ar.replace("\\", "/")
        ranlib_path = ranlib.replace("\\", "/") if ranlib else None

        # MesonToolchain may generate conan_meson_native.ini and/or
        # conan_meson_cross.ini depending on whether the build is native
        # or cross.  Patch every file that exists.
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            native_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(native_file):
                continue
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()

            # Case 1: an ar= line already exists → replace it
            if re.search(r"^ar\s*=", content, flags=re.MULTILINE):
                content = re.sub(
                    r"^ar\s*=.*$",
                    f"ar = '{ar_path}'",
                    content,
                    flags=re.MULTILINE,
                )
            # Case 2: [binaries] section exists but no ar= → insert after it
            elif "[binaries]" in content:
                content = content.replace(
                    "[binaries]\n",
                    f"[binaries]\nar = '{ar_path}'\n",
                    1,
                )
            # Case 3: no [binaries] section at all → append one
            else:
                content += f"\n[binaries]\nar = '{ar_path}'\n"

            # Handle ranlib the same way
            if ranlib_path:
                if re.search(r"^ranlib\s*=", content, flags=re.MULTILINE):
                    content = re.sub(
                        r"^ranlib\s*=.*$",
                        f"ranlib = '{ranlib_path}'",
                        content,
                        flags=re.MULTILINE,
                    )
                elif f"ar = '{ar_path}'\n" in content:
                    content = content.replace(
                        f"ar = '{ar_path}'\n",
                        f"ar = '{ar_path}'\nranlib = '{ranlib_path}'\n",
                        1,
                    )

            with open(native_file, "w", encoding="utf-8") as handle:
                handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

        if self.options.shared:
            meson.test()
            return

        # symbols-check 的导出符号白名单比对只对共享库有意义：静态库会把
        # 全部内部全局符号暴露给 nm，比对必然失真（上游脚本对 .a 归档成员
        # 头行也会解析崩溃）。因此在共享配置下重建并运行完整上游测试
        # （10 项全保留），随后恢复静态配置再打包（R26 默认静态）。
        self.run(f'meson configure "{self.build_folder}" -Ddefault_library=shared')
        meson.build()
        meson.test()
        self.run(f'meson configure "{self.build_folder}" -Ddefault_library=static')
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        # 产物为 libdrm.a 等；cpp_info.libs 须写不带 lib 前缀的链接名
        # 头文件两层布局：include/（xf86drm.h）与 include/libdrm/（drm.h 等），
        # 与上游 libdrm.pc 的 Cflags -I${includedir}/libdrm 对齐
        self.cpp_info.includedirs = ["include", "include/libdrm"]
        self.cpp_info.libs = [
            "drm",
            "drm_amdgpu",
            "drm_radeon",
            "drm_nouveau",
            "drm_freedreno",
            "drm_etnaviv",
        ]
