#!/usr/bin/env python3
"""test_package for klibc-dash — 消费者视角验证包内 bin/sh（R34：实质依赖被测包产物）。

- build()：静态校验包内 bin/sh 存在、是 OHOS 可执行签名 ELF（.codesign，E077）、
  且为静态自包含（无 PT_INTERP，不依赖 OHOS musl 动态加载器）。
- test()：用系统 bash 作为启动器，由**被测包内的 sh** 解释执行 test_package/test_dash.sh
  （OHOS /system/bin/sh(mksh) 无法 exec ELF，故不能直接用系统 shell 起 ELF）。
"""
import os
import struct

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class KlibcDashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _test_data(self, name):
        for base in (os.path.dirname(os.path.abspath(__file__)), os.getcwd()):
            p = os.path.join(base, name)
            if os.path.isfile(p):
                return p
        raise ConanException(f"klibc-dash test_package: missing test data {name}")

    def _packaged_sh(self):
        dep = self.dependencies["klibc-dash"].cpp_info
        if not dep.bindirs:
            raise ConanException("klibc-dash package declares no bindirs")
        sh = os.path.join(dep.bindirs[0], "sh")
        if not os.path.isfile(sh):
            raise ConanException(f"klibc-dash package bin/sh missing: {sh}")
        return sh

    @staticmethod
    def _has_pt_interp(path):
        """解析 ELF64 程序头，判断是否存在 PT_INTERP（动态加载器）。"""
        with open(path, "rb") as fh:
            hdr = fh.read(64)
        if hdr[:4] != b"\x7fELF" or hdr[4] != 2:
            return None  # 非 ELF64：交由上层判定
        e_phoff = struct.unpack_from("<Q", hdr, 32)[0]
        e_phentsize = struct.unpack_from("<H", hdr, 54)[0]
        e_phnum = struct.unpack_from("<H", hdr, 56)[0]
        with open(path, "rb") as fh:
            fh.seek(e_phoff)
            phdrs = fh.read(e_phentsize * e_phnum)
        for i in range(e_phnum):
            p_type = struct.unpack_from("<I", phdrs, i * e_phentsize)[0]
            if p_type == 3:  # PT_INTERP
                return True
        return False

    def build(self):
        sh = self._packaged_sh()
        with open(sh, "rb") as fh:
            data = fh.read()
        if data[:4] != b"\x7fELF":
            raise ConanException(f"klibc-dash bin/sh is not an ELF binary: {sh}")
        if b".codesign" not in data:
            raise ConanException(
                "klibc-dash bin/sh lacks .codesign; OHOS kernel refuses to exec it (E077)"
            )
        self.output.info("OHOS check: .codesign section present in bin/sh")
        interp = self._has_pt_interp(sh)
        if interp:
            raise ConanException(
                "klibc-dash bin/sh has PT_INTERP; expected static self-contained binary"
            )
        self.output.info("OHOS check: bin/sh is static (no PT_INTERP)")
        if not os.access(sh, os.X_OK):
            raise ConanException(f"klibc-dash bin/sh is not executable: {sh}")

    def test(self):
        sh = self._packaged_sh()
        self.output.info(f"testing packaged shell: {sh}")
        if cross_building(self):
            self.output.info("cross-building: 已由 build() 完成静态校验，跳过执行")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        runner = self._test_data("run_tests.sh")
        script = self._test_data("test_dash.sh")
        self.run(f'"{bash}" "{runner}" "{sh}" "{script}"')
