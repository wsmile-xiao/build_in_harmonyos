#!/usr/bin/env python3
"""Conan test_package — gsettings-qt5 1.1.1（Qt5 消费方验证）。

验证内容（实质性调用被测包 API，R34）：
  1. 走下游真实消费路径 pkg_check_modules(gsettings-qt)（用被测包自己的
     lib/pkgconfig/gsettings-qt.pc，而非 PkgConfigDeps 生成的同名文件），
     编译 + 链接 + 运行一个 QGSettings 客户端；
  2. 用包内 glib 工具 glib-compile-schemas 编译测试 schema，在
     GSETTINGS_BACKEND=memory 下完成 get/set/trySet/reset/keys/defaultValue/
     choices/changed 信号的真实读写验证；
  3. 校验包安装的 pkg-config 元数据与库的 DT_SONAME。
"""

import os
import shutil
import stat
import struct
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

SCHEMA_FILE = "com.ubports.gsettings.adt.gschema.xml"


class GsettingsQt5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # 测试 schema 编译工具（OHOS 侧系统无 glib-compile-schemas）。
        self.tool_requires("glib/2.88.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        tc.cache_variables["GSETTINGS_QT_PC_DIR"] = os.path.join(
            package_folder, "lib", "pkgconfig"
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._compile_test_schema()
        if str(self.settings.os) == "OHOS":
            self._sign(self._test_binary())

    def _test_binary(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanInvalidConfiguration("no bindir produced for the test binary")
        return os.path.join(bindirs[0], "test_gsettings_qt5")

    def _compile_test_schema(self):
        target = os.path.join(self.build_folder, SCHEMA_FILE)
        shutil.copy(os.path.join(self.recipe_folder, SCHEMA_FILE), target)
        self.run(
            "glib-compile-schemas {}".format(self.build_folder),
            env="conanbuild",
            ignore_errors=False,
        )

    def _sign(self, path):
        original_mode = stat.S_IMODE(os.stat(path).st_mode)
        signer = shutil.which("binary-sign-tool")
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool not found; required to execute OHOS ELF binaries"
            )
        with tempfile.TemporaryDirectory(
            prefix=".conan-sign-", dir=os.path.dirname(path)
        ) as temp_dir:
            unsigned = os.path.join(temp_dir, "unsigned")
            signed = os.path.join(temp_dir, "signed")
            shutil.copy2(path, unsigned)
            subprocess.run(
                [signer, "sign", "-inFile", unsigned, "-outFile", signed,
                 "-selfSign", "1"],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            os.replace(signed, path)
            os.chmod(path, original_mode)

    def test(self):
        self._check_pkg_config_metadata()
        self._check_soname()
        if not can_run(self):
            self.output.info("Skipping execution: cross-build without emulator")
            return
        os.environ["GSETTINGS_SCHEMA_DIR"] = self.build_folder
        os.environ["GSETTINGS_BACKEND"] = "memory"
        self.run(self._test_binary(), env="conanrun", ignore_errors=False)

    def _package_folder(self):
        return self.dependencies[self.tested_reference_str].package_folder

    def _check_pkg_config_metadata(self):
        """校验包内 pkg-config 元数据（下游 kylin-calendar 的 pkg_check_modules
        消费入口）。"""
        pc_file = os.path.join(
            self._package_folder(), "lib", "pkgconfig", "gsettings-qt.pc"
        )
        if not os.path.isfile(pc_file):
            raise ConanInvalidConfiguration(f"pkg-config file missing: {pc_file}")
        with open(pc_file, encoding="utf-8") as handle:
            content = handle.read()
        for expected in ("Requires: gio-2.0", "Libs:", "-lgsettings-qt"):
            if expected not in content:
                raise ConanInvalidConfiguration(
                    "gsettings-qt.pc does not declare {!r}".format(expected)
                )
        if "/qt5/QGSettings" not in content:
            raise ConanInvalidConfiguration(
                "gsettings-qt.pc Cflags does not point at the qt5/QGSettings dir"
            )
        self.output.info("pkg-config metadata verified: {}".format(pc_file))

    def _check_soname(self):
        """HarmonyOS L5a 门禁：验证库携带 DT_SONAME（下游链接器按名寻址）。
        上游 src/CMakeLists.txt 的 SOVERSION=1 会正常传播为
        'libgsettings-qt.so.1'；解析 ELF .dynamic 段验证（纯 Python，
        无 readelf 依赖）。"""
        if str(self.settings.os) != "OHOS":
            self.output.info("SONAME check skipped (non-OHOS)")
            return
        lib = os.path.join(self._package_folder(), "lib", "libgsettings-qt.so")
        with open(lib, "rb") as handle:
            elf = handle.read()
        soname = self._elf_soname(elf)
        if not soname or not soname.startswith("libgsettings-qt.so"):
            raise ConanInvalidConfiguration(
                "DT_SONAME missing or wrong in libgsettings-qt.so: {!r}".format(soname)
            )
        self.output.info("DT_SONAME verified: {}".format(soname))

    @staticmethod
    def _elf_soname(elf):
        """Parse DT_SONAME from an ELF64 little-endian binary (pure Python)."""
        if elf[:4] != b"\x7fELF" or elf[4] != 2:
            return None
        e_phoff = struct.unpack_from("<Q", elf, 0x20)[0]
        e_phentsize = struct.unpack_from("<H", elf, 0x36)[0]
        e_phnum = struct.unpack_from("<H", elf, 0x38)[0]
        loads = []
        dyn_off = dyn_size = None
        for i in range(e_phnum):
            off = e_phoff + i * e_phentsize
            p_type = struct.unpack_from("<I", elf, off)[0]
            p_offset = struct.unpack_from("<Q", elf, off + 8)[0]
            p_vaddr = struct.unpack_from("<Q", elf, off + 16)[0]
            p_filesz = struct.unpack_from("<Q", elf, off + 32)[0]
            if p_type == 2:  # PT_DYNAMIC
                dyn_off, dyn_size = p_offset, p_filesz
            elif p_type == 1:  # PT_LOAD
                loads.append((p_vaddr, p_offset, p_filesz))
        if dyn_off is None:
            return None
        strtab_vaddr = None
        soname_off = None
        for i in range(dyn_size // 16):
            d_tag, d_val = struct.unpack_from("<qQ", elf, dyn_off + i * 16)
            if d_tag == 0:  # DT_NULL
                break
            if d_tag == 5:  # DT_STRTAB
                strtab_vaddr = d_val
            elif d_tag == 14:  # DT_SONAME
                soname_off = d_val
        if strtab_vaddr is None or soname_off is None:
            return None
        for vaddr, offset, size in loads:
            if vaddr <= strtab_vaddr < vaddr + size:
                base = offset + (strtab_vaddr - vaddr)
                end = elf.index(b"\x00", base + soname_off)
                return elf[base + soname_off:end].decode("utf-8", "replace")
        return None
