#!/usr/bin/env python3
"""Conan test_package — pdf2svg 0.2.4

L1 test: pdf2svg 是命令行工具（无可链接库），test_pdf2svg.sh 真实执行**已安装的**
`bin/pdf2svg`，对 6 项可观测行为做端到端断言（用法输出 → 单页转换 → `all` 多页
转换 → 打开失败 → 页标签不存在 → 两页输出不同）。R34：二进制即被测 API。

夹具 PDF 由本文件用**纯 Python**写出（`_write_fixture_pdf`，含精确计算的
xref 字节偏移），内容是纯矢量（矩形/折线，无字体）——这样渲染路径不经过
fontconfig/freetype 的字体匹配，CI worker 上没有字体也不会影响断言。

运行时寻库（HMBS [stale_runtime_library]）：OHOS loader 可能忽略
LD_LIBRARY_PATH，所以除了把各依赖包 libdir 交给 conanrun 环境之外，还从
**已安装的 bin/pdf2svg 的 DT_NEEDED 出发做 BFS**，把真正会被加载到的依赖
.so 的绝对路径经 LD_PRELOAD 注入。不采用「依赖包 libdir 里的 .so 全部
preload」的做法：闭包外的库（例如 glib 附带的 libgirepository-2.0.so.0）
若其某个 DT_NEEDED 在本次依赖图里不存在，LD_PRELOAD 会让进程直接起不来。

脚本用 HMBS 注入的 SHELL/CONFIG_SHELL（POSIX sh）执行，不硬编码
/data/service/hnp/bin/bash（HMBS [shell_getcwd]）；scratch 目录由本文件传入
（OHOS `/tmp` 是 erofs 只读，E002）。
"""

import os
import shutil
import struct

from conan import ConanFile
from conan.errors import ConanException

# 夹具 PDF 的两页内容流：纯路径操作（S 描边 / f 填充），不含任何文字。
_CONTENT_PAGE1 = (
    b"1 0 0 RG 4 w\n"
    b"20 20 m 180 20 l 180 180 l 20 180 l h S\n"
    b"0 0 1 rg\n"
    b"60 60 80 80 re f\n"
)
_CONTENT_PAGE2 = (
    b"0 1 0 rg\n"
    b"30 30 m 170 30 l 100 170 l h f\n"
)


class Pdf2svgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ── 夹具 PDF（纯 Python 生成，偏移自算） ────────────────────────
    def _write_fixture_pdf(self, path):
        """写一个 2 页、纯矢量、无字体的最小合法 PDF。

        xref 表里每个对象的字节偏移在这里**算出来**而不是手写常量，
        所以不会因为改内容流而失配（poppler 对坏 xref 会尝试重建并打印
        Syntax Warning，那种"能打开"是假象，不能作为夹具正确的依据）。
        """
        bodies = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
            b"/Contents 4 0 R /Resources << >> >>",
            b"<< /Length %d >>\nstream\n" % len(_CONTENT_PAGE1)
            + _CONTENT_PAGE1 + b"endstream",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
            b"/Contents 6 0 R /Resources << >> >>",
            b"<< /Length %d >>\nstream\n" % len(_CONTENT_PAGE2)
            + _CONTENT_PAGE2 + b"endstream",
        ]
        out = bytearray(b"%PDF-1.4\n")
        offsets = []
        for index, body in enumerate(bodies, start=1):
            offsets.append(len(out))
            out += b"%d 0 obj\n" % index + body + b"\nendobj\n"
        xref_offset = len(out)
        out += b"xref\n0 %d\n" % (len(bodies) + 1)
        out += b"0000000000 65535 f \n"
        for offset in offsets:
            out += b"%010d 00000 n \n" % offset
        out += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (len(bodies) + 1)
        out += b"startxref\n%d\n%%%%EOF\n" % xref_offset
        with open(path, "wb") as handle:
            handle.write(bytes(out))

    # ── 运行期 .so 闭包（纯 Python ELF DT_NEEDED 解析） ─────────────
    @staticmethod
    def _elf_dynamic(data):
        """返回 (soname, [needed...])；非 ELF64-LE 或解析失败时返回 (None, [])。

        只读 section header 里的 .dynamic（SHT_DYNAMIC = 6）与其 sh_link
        指向的字符串表，不需要 section 名字，也就不依赖 .shstrtab 完整。
        """
        if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
            return None, []
        if len(data) < 0x40:
            return None, []
        shoff, = struct.unpack_from("<Q", data, 0x28)
        shentsize, shnum, _shstrndx = struct.unpack_from("<HHH", data, 0x3A)
        if not shnum or shoff + shnum * shentsize > len(data):
            return None, []
        sections = [struct.unpack_from("<IIQQQQIIQQ", data, shoff + i * shentsize)
                    for i in range(shnum)]
        dynamic = None
        for section in sections:
            if section[1] == 6:
                dynamic = section
                break
        if dynamic is None or dynamic[6] >= len(sections):
            return None, []
        strtab = sections[dynamic[6]][4]
        soname = None
        needed = []
        for index in range(dynamic[5] // 16):
            tag, value = struct.unpack_from("<QQ", data, dynamic[4] + index * 16)
            if tag == 0:
                break
            if tag not in (1, 14):
                continue
            end = data.index(b"\0", strtab + value)
            text = data[strtab + value:end].decode("utf-8", "replace")
            if tag == 14:
                soname = text
            else:
                needed.append(text)
        return soname, needed

    @classmethod
    def _elf_needed(cls, path):
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except OSError:
            return []
        return cls._elf_dynamic(data)[1]

    def _soname_index(self):
        """扫各依赖包 libdir，建 SONAME -> .so 绝对路径索引。

        conan 缓存里的库是 `.so` → `.so.N` → `.so.N.M.K` 符号链接链，
        HMFS 对 symlink 物化不可靠（E050），只取非符号链接的实体文件；
        loader 按 SONAME 登记，效果等价（同 xeyes/1.3.1）。
        """
        index = {}
        for dependency in self.dependencies.values():
            libdirs = []
            try:
                libdirs.extend(dependency.cpp_info.aggregated_components().libdirs)
            except Exception:
                pass
            package_folder = getattr(dependency, "package_folder", None)
            if package_folder:
                fallback = os.path.join(package_folder, "lib")
                if os.path.isdir(fallback):
                    libdirs.append(fallback)
            for libdir in libdirs:
                if not libdir or not os.path.isdir(libdir):
                    continue
                for entry in sorted(os.listdir(libdir)):
                    if ".so" not in entry:
                        continue
                    candidate = os.path.join(libdir, entry)
                    if not os.path.isfile(candidate) or os.path.islink(candidate):
                        continue
                    try:
                        with open(candidate, "rb") as handle:
                            soname = self._elf_dynamic(handle.read())[0]
                    except OSError:
                        continue
                    index.setdefault(soname or entry, candidate)
        return index

    def _runtime_preload(self, binary):
        """从被测二进制出发做 DT_NEEDED BFS，返回按发现顺序的 .so 路径列表。

        解析不到的 SONAME 就是 OHOS 系统库（libc.so / libc++_shared.so 等），
        交给系统 loader，不进 LD_PRELOAD。
        """
        index = self._soname_index()
        seen = set()
        order = []
        queue = [binary]
        while queue:
            for soname in self._elf_needed(queue.pop(0)):
                if soname in seen:
                    continue
                seen.add(soname)
                resolved = index.get(soname)
                if resolved is None:
                    continue
                order.append((soname, resolved))
                queue.append(resolved)
        return order

    def test(self):
        dependency = self.dependencies["pdf2svg"]
        binary = os.path.join(dependency.package_folder, "bin", "pdf2svg")
        if not os.path.isfile(binary):
            raise ConanException("pdf2svg binary missing: %s" % binary)

        work = os.path.join(self.build_folder, "pdf2svg-scratch")
        os.makedirs(work, exist_ok=True)
        self._write_fixture_pdf(os.path.join(work, "fixture.pdf"))

        closure = self._runtime_preload(binary)
        preload = ":".join(path for _soname, path in closure)
        self.output.info("runtime closure (%d libs): %s" % (
            len(closure), ", ".join(soname for soname, _p in closure)))
        if not preload:
            raise ConanException("runtime .so closure is empty — dependency scan failed")

        shell = (os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL")
                 or shutil.which("sh") or "/bin/sh")
        script = os.path.join(self.source_folder, "test_pdf2svg.sh")
        self.run('"{}" "{}" "{}" "{}" "{}"'.format(
            shell, script, binary, preload, work), env="conanrun")
        # HMBS_TEST_PACKAGE_RESULT 由 test_pdf2svg.sh 在真实断言结束后打印。
        # 上游无测试套件（tarball 无 tests/，Makefile.am 无 TESTS/check 目标），
        # 因此这里补一条 HMBS_UPSTREAM_TEST_RESULT 说明"无上游用例"，
        # 与 MANIFEST.yml 的 upstream_tests_exist: false 一致。
        print('HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
              '"framework":"none",'
              '"command":"make check (no check target)",'
              '"discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,'
              '"reason":"pdf2svg 0.2.4 上游无测试套件：tarball 无 tests/ 目录，'
              'Makefile.am 仅 bin_PROGRAMS = pdf2svg（无 TESTS/check_PROGRAMS/check-local），'
              '无 meson.build"}')
