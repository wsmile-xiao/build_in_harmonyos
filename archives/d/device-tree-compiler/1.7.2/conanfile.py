#!/usr/bin/env python3
"""Conan recipe — device-tree-compiler 1.7.2 (make)

DTC 是设备树编译器：解析/生成设备树源（dts）与扁平二进制（dtb），
配套工具集 dtc / fdtdump / fdtget / fdtput / fdtoverlay，并产出 libfdt。
本配方用 STATIC_BUILD=1 静态链接 libfdt.a，工具包无 .so 运行时依赖。"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class DeviceTreeCompilerConan(ConanFile):
    name = "device-tree-compiler"
    version = "1.7.2"
    description = "Device Tree Compiler: dts <-> dtb and libfdt (flattened device tree flattening/blobbing)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/devicetree-org/device-tree-compiler"
    url = "https://git.kernel.org/pub/scm/utils/dtc/dtc.git"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"])

    def build(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "device-tree-compiler supports Linux/OHOS-style POSIX platforms"
            )
        apply_conandata_patches(self)
        src = self.source_folder
        make = (
            "make -C {s} -j1 STATIC_BUILD=1 "
            "CC=clang AR=llvm-ar LD=clang "
            "EXTRA_CFLAGS=\"-fPIC -O2\" "
            "dtc fdtdump fdtget fdtput fdtoverlay libfdt"
        ).format(s=src)
        self.run(make, env="conanbuild")
        if can_run(self):
            self.output.info("Running upstream test suite: make check (mapped to build result)")
            test_log = os.path.join(self.build_folder, "dtc_tests.log")
            self.run(
                'echo "STATSZ_BYTE_TEST=$(stat -c %s "{s}/tests/lorem.txt")"; '
                'STATSZ="stat -c %s" make -C "{s}" check STATIC_BUILD=1 '
                "CC=clang AR=llvm-ar LD=clang "
                "EXTRA_CFLAGS=\"-fPIC -O2\" > \"{l}\" 2>&1; "
                'rc=$?; echo "UPSTREAM_MAKE_CHECK_RC=$rc"; '
                'echo "--- make check summary ---"; '
                'sed -n "/TEST SUMMARY/,+6p" "{l}"; '
                'echo "--- make check summary end ---"; '
                "if [ $rc -ne 0 ]; then"
                '   echo "--- first FAIL lines ---"; grep -n "FAIL" "{l}" | head -n 25; '
                '   echo "--- last FAIL lines ---"; grep -n "FAIL" "{l}" | tail -n 25; '
                '   echo "UPSTREAM_MAKE_CHECK_FAILED=1"; exit 1; '
                'fi; echo "UPSTREAM_MAKE_CHECK_OK=1"'.format(s=src, l=test_log),
                env="conanbuild",
            )

    def package(self):
        srcdir = self.source_folder
        libfdt = os.path.join(srcdir, "libfdt")
        copy(self, "GPL", srcdir, os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "BSD-2-Clause", srcdir, os.path.join(self.package_folder, "licenses"), keep_path=False)
        for tool in ("dtc", "fdtdump", "fdtget", "fdtput", "fdtoverlay"):
            copy(self, tool, srcdir, os.path.join(self.package_folder, "bin"), keep_path=False)
        for hdr in ("libfdt.h", "libfdt_env.h", "fdt.h"):
            copy(self, hdr, libfdt, os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "libfdt.a", libfdt, os.path.join(self.package_folder, "lib"), keep_path=False)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求可执行文件代码签名（desktop-file-utils/glib 同款方案）。
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            return
        for name in os.listdir(bindir):
            p = os.path.join(bindir, name)
            if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=p))
                self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=p))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["fdt"]