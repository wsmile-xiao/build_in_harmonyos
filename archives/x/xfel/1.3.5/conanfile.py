#!/usr/bin/env python3
"""Conan recipe — xfel 1.3.5 (Tiny FEL tools for Allwinner SoC) for HarmonyOS (arm64).

上游：https://github.com/xboot/xfel （作者 Jianjun Jiang / xboot 项目）
xfel 通过 USB OTG 进入全志 SoC 的 FEL 模式，做初始烧录/内存读写/SPI 存储访问。
单一构建产物是可执行文件 **xfel**：

* ``bin/xfel`` —— 命令行工具（``xfel version`` / ``hexdump`` / ``read32`` /
  ``write32`` / ``read`` / ``write`` / ``exec`` / ``reset`` / ``sid`` / ``jtag`` /
  ``ddr`` / ``sign`` / ``spinor`` / ``spinand`` / ``extra``）

R38：包内含可执行文件 → ``package_type = "application"``，并在软件级目录声明
``archives/x/xfel/commands.json``。

第三方依赖：唯一强制依赖是 **libusb-1.0**（上游 ``Makefile`` 用
``pkg-config --libs libusb-1.0`` 探测；``main.c`` ``#include <libusb.h>``）。
适配改为消费制品仓的 ``libusb/1.0.27``，W0 可消费性证据见 notes.md。
libusb 在 OHOS 上**不是**系统同名库（``/lib``、``/lib64`` 下无 libusb-1.0.so），
故保持默认动态链接（R26 不适用），运行期搜索路径用 ``-Wl,-rpath`` 固定。

构建系统：上游只有 GNU Makefile（``make``，无 configure/CMake/meson）。
``Makefile`` 把工具链**硬编码**为 ``CC := $(CROSS)gcc``，OHOS 上无 gcc →
按 R33 由 Conan 的 ``tools.build:compiler_executables`` 注入 CC，其余构建变量
（``INCDIRS`` / ``LIBS``）由本配方按 libusb 依赖包位置显式传入。

OHOS 平台适配（唯一补丁 ``patches/0001-main.c.patch``）：
``main.c`` 调用 ``libusb_init()`` 后**不检查返回值**，随后把可能为 NULL 的
context 交给 ``libusb_get_device_list()``。在 OHOS（受限 ``/dev/bus``、
``sysfs_get_device_list`` 返回 EACCES）下 ``libusb_init()`` 返回 -1，于是
所有子命令在 **libusb 枚举前** 就空指针解引用 → SIGSEGV(139)。补丁改为检查
返回值并给出 ``ERROR: Can't initialize libusb`` 后正常退出，设备命令退化为
可预期的 rc=255，不再崩溃。

上游**没有自动化测试套件**（无 tests/、无 ctest/CTest、Makefile 无 check/test
目标、无 CI 配置文件）。其唯一真实入口是 CLI 本身，故本配方在 ``build()`` 内
执行完整的 CLI 入口矩阵并校验行为（上游测试统计见 notes.md / reports/）。
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class XfelConan(ConanFile):
    name = "xfel"
    version = "1.3.5"
    description = ("Tiny FEL tools for Allwinner SOC — flashes/debugs Allwinner "
                   "SoCs over USB OTG FEL mode (xfel command line tool)")
    license = "MIT"
    homepage = "https://github.com/xboot/xfel"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    _CHECK_TIMEOUT = 20

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 唯一强制第三方依赖（W0: conan download 配方 rc=0 / 二进制 rc=0，见 notes.md）
        self.requires("libusb/1.0.27")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── build ────────────────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        self.run(self._make_command(), cwd=self.source_folder)
        self._run_upstream_checks()

    def _make_command(self):
        """`make all`，所有变量均由 Conan 提供（R33：不读裸 shell 变量）。

        Makefile 把 ``CC`` 硬编码为 ``$(CROSS)gcc``；GNU Make 的命令行变量赋值
        优先级高于 makefile 内的 ``:=``，故此处直接覆盖 ``CC``/``INCDIRS``/``LIBS``，
        无需修改 Makefile。``AS``/``LD``/``AR``/``OC``/``OD`` 未被使用
        （源树 ``.``/``chips`` 下无 .S 文件，SRCDIRS 不含 payloads/）。
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"

        libusb = self.dependencies["libusb"]
        # libusb 包把 include/libusb-1.0 作为 include dir，而 main.c 写的是
        # #include <libusb.h>，所以 -I 必须指向 include/libusb-1.0。
        usb_include = os.path.join(libusb.package_folder, str(libusb.cpp_info.includedirs[0]))
        usb_libdir = os.path.join(libusb.package_folder, str(libusb.cpp_info.libdirs[0]))

        return (
            f'make CC="{cc}"'
            f' INCDIRS="-I. -I{usb_include}"'
            f' LIBS="-L{usb_libdir} -lusb-1.0 -Wl,-rpath,{usb_libdir}"'
            f" -j1"
        )

    # ── upstream verification ────────────────────────────────────────────────
    def _run_env(self):
        """运行环境：把 libusb 包目录也导出到 LD_LIBRARY_PATH。

        二进制本身带 rpath 指向 libusb 包目录；再用 LD_LIBRARY_PATH 兜底，
        以覆盖 rpath 被忽略的环境。
        """
        env = dict(os.environ)
        libusb = self.dependencies["libusb"]
        libdir = os.path.join(libusb.package_folder, str(libusb.cpp_info.libdirs[0]))
        old = env.get("LD_LIBRARY_PATH")
        env["LD_LIBRARY_PATH"] = libdir + (os.pathsep + old if old else "")
        return env

    def _run_check(self, argv, expect_rc, expect_re, cwd=None, timeout=None):
        """运行一条上游 CLI 入口；返回 (ok, detail)。"""
        try:
            proc = subprocess.run(
                argv,
                cwd=cwd or self.source_folder,
                env=self._run_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout or self._CHECK_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return False, f"timeout after {timeout or self._CHECK_TIMEOUT}s"

        out = proc.stdout.decode("utf-8", "replace")
        first = out.splitlines()[0] if out.splitlines() else ""
        if proc.returncode in (139, -11):
            return False, f"exit {proc.returncode} (SIGSEGV) — 适配回归"
        if proc.returncode != expect_rc:
            return False, f"exit {proc.returncode}, expected {expect_rc} ({first[:80]!r})"
        if expect_re and not any(expect_re in line for line in out.splitlines()):
            return False, f"missing {expect_re!r} in output ({first[:80]!r})"
        return True, f"exit {proc.returncode} ({first[:60]})"

    def _upstream_entries(self):
        """上游真实入口 = CLI 本身（上游无自动化测试套件）。

        xfel 在 libusb 枚举 + fel_init() **之后**才分发子命令，因此无 FEL 硬件
        （或无 USB 访问权限）时所有设备类命令走同一条失败路径：
        rc=255 且打印 ``ERROR: ...``。usage 类命令（无参 / -h / --help）在
        libusb 初始化之前返回，可完整验证。
        """
        xfel = os.path.join(self.source_folder, "xfel")
        usage = "xfel(v1.3.5)"
        dev = "ERROR: "
        return [
            # usage 类：libusb 之前返回，rc=0
            ("usage/no-arg", [], 0, usage),
            ("usage/-h", ["-h"], 0, usage),
            ("usage/--help", ["--help"], 0, usage),
            # 设备类：无 FEL 硬件时统一 rc=255 且打印 ERROR（不再 SIGSEGV）
            ("cmd/version", ["version"], 255, dev),
            ("cmd/hexdump", ["hexdump", "0x1000", "16"], 255, dev),
            ("cmd/dump", ["dump", "0x1000", "16"], 255, dev),
            ("cmd/read32", ["read32", "0x1000"], 255, dev),
            ("cmd/write32", ["write32", "0x1000", "0x1234"], 255, dev),
            ("cmd/read", ["read", "0x1000", "16", "out.bin"], 255, dev),
            ("cmd/write", ["write", "0x1000", "in.bin"], 255, dev),
            ("cmd/exec", ["exec", "0x1000"], 255, dev),
            ("cmd/reset", ["reset"], 255, dev),
            ("cmd/sid", ["sid"], 255, dev),
            ("cmd/jtag", ["jtag"], 255, dev),
            ("cmd/ddr", ["ddr"], 255, dev),
            ("cmd/sign", ["sign", "00" * 33, "00" * 32, "sig.bin"], 255, dev),
            ("cmd/spinor", ["spinor"], 255, dev),
            ("cmd/spinor-erase", ["spinor", "erase", "0", "0x1000"], 255, dev),
            ("cmd/spinor-read", ["spinor", "read", "0", "16", "nor.bin"], 255, dev),
            ("cmd/spinor-write", ["spinor", "write", "0", "in.bin"], 255, dev),
            ("cmd/spinand", ["spinand"], 255, dev),
            ("cmd/spinand-erase", ["spinand", "erase", "0", "0x1000"], 255, dev),
            ("cmd/spinand-read", ["spinand", "read", "0", "16", "nand.bin"], 255, dev),
            ("cmd/spinand-write", ["spinand", "write", "0", "in.bin"], 255, dev),
            ("cmd/spinand-splwrite",
             ["spinand", "splwrite", "0x800", "0", "in.bin"], 255, dev),
            ("cmd/extra", ["extra"], 255, dev),
            ("cmd/unknown", ["not-a-real-command"], 255, dev),
        ]

    def _run_upstream_checks(self):
        # 独立 scratch 目录承载 in.bin 等夹具，跑完即删，不残留源码树
        scratch = os.path.join(self.source_folder, "xfel-checkwork")
        os.makedirs(scratch, exist_ok=True)
        with open(os.path.join(scratch, "in.bin"), "wb") as handle:
            handle.write(b"xfel-cli-fixture\n")

        xfel = os.path.join(self.source_folder, "xfel")
        failed, executed = [], 0
        try:
            for name, args, expect_rc, expect_re in self._upstream_entries():
                ok, detail = self._run_check([xfel] + args, expect_rc, expect_re, cwd=scratch)
                executed += 1
                self.output.info(f"  upstream entry [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
                if not ok:
                    failed.append(f"{name} -> {detail}")
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

        total = len(self._upstream_entries())
        upstream = {
            "status": "failed" if failed else "passed",
            "framework": "upstream-cli-entry-matrix (upstream ships no automated tests)",
            "command": "xfel {usage | <subcommand> ...}",
            "discovered": total,
            "executed": executed,
            "passed": executed - len(failed),
            "failed": len(failed),
            "skipped": 0,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        )
        if failed:
            raise ConanException("Upstream CLI entry checks failed: " + "; ".join(failed))

    # ── package ──────────────────────────────────────────────────────────────
    def package(self):
        # 不使用上游 `make install`：它把 /usr/local/bin、/etc/udev/rules.d、
        # /usr/share/licenses 这些绝对路径直接写进构建机（OHOS 亦无 udev）。
        src = self.source_folder
        copy(self, "xfel", src, os.path.join(self.package_folder, "bin"))
        copy(self, "99-xfel.rules", src, os.path.join(self.package_folder, "share", "xfel"))
        copy(self, "LICENSE", src, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 纯命令行工具：只提供可执行文件与附带数据（R38 → commands.json）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share/xfel"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
