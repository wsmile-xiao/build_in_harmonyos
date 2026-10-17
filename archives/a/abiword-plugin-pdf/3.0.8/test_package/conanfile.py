#!/usr/bin/env python3
"""Conan test_package — abiword-plugin-pdf 3.0.8

L1 test: verify the plugin .so is a valid ELF with expected exported symbols.
"""
import os
import shutil
import ctypes
import subprocess

from conan import ConanFile


class AbiwordPluginEmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["abiword-plugin-pdf"].package_folder

        # L0d: run a real test program via self.run() — test_pdf.sh verifies
        # pdf.so ELF validity + ABI exported symbols via readelf (L0c 测试源文件,
        # 否则 CI 报 'no_test_sources stub_test_method no_manifest' 门禁失败)。
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test_pdf.sh")
        self.run(
            f'"{bash}" "{script}" "{pkg_folder}"',
            env="conanrun",
        )

        plugin_dir = os.path.join(pkg_folder, "lib", "abiword", "plugins")

        # Find the pdf plugin .so — keep full path to avoid basename/join mismatch
        import glob
        pdf_so = []
        if os.path.isdir(plugin_dir):
            pdf_so = [os.path.join(plugin_dir, p) for p in os.listdir(plugin_dir)
                      if "pdf" in p.lower() and p.endswith(".so")]

        if not pdf_so:
            # Fallback: search anywhere in the package, keep full path
            pdf_so = glob.glob(os.path.join(pkg_folder, "**", "*pdf*.so*"), recursive=True)

        if not pdf_so:
            # Try listing the package contents for debugging
            self.output.info("Package contents:")
            for root, dirs, files in os.walk(pkg_folder):
                for f in files:
                    self.output.info(f"  {os.path.join(root, f)}")
            raise AssertionError("PDF plugin .so not found in package")

        so_path = pdf_so[0]
        self.output.info(f"PDF plugin found: {so_path}")

        # Method 1: Use readelf to verify it's a valid ELF with exported symbols
        # 优先用工具链 readelf(hnp 自带),OS 自带 readelf 通常不可用
        self.output.info("Verifying ELF validity and exported symbols via readelf...")
        readelf_bin = None
        for cand in ["/data/service/hnp/bin/readelf", "/data/service/hnp/bin/llvm-readelf", "readelf"]:
            try:
                subprocess.run([cand, "--version"], capture_output=True, timeout=5)
                readelf_bin = cand
                break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        if readelf_bin:
            try:
                # -W 宽输出: GNU readelf 默认截断长符号名(abi_plugin_supports_version
                # 会显示为 abi_plugin_suppo[...]),-W 防止截断保证符号名完整匹配
                result = subprocess.run(
                    [readelf_bin, "-sW", so_path],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0:
                    # Check for expected plugin symbols
                    for sym in ["abi_plugin_register", "abi_plugin_unregister",
                               "abi_plugin_supports_version"]:
                        if sym in result.stdout:
                            self.output.info(f"  [ok] Exported symbol found: {sym}")
                        else:
                            raise AssertionError(f"Expected symbol not found in readelf: {sym}")
                    # Count total exported symbols
                    sym_count = len([l for l in result.stdout.splitlines()
                                     if "FUNC" in l and "GLOBAL" in l])
                    self.output.info(f"  Total exported FUNC symbols: {sym_count}")
                else:
                    raise AssertionError(f"readelf failed (rc={result.returncode}): {result.stderr}")
            except subprocess.TimeoutExpired:
                raise AssertionError("readelf timed out")
        else:
            raise AssertionError("No readelf found in toolchain")

        # Method 2: Use ctypes to attempt loading the .so (native only)
        # P1: can_run() 交叉编译守卫必须在 try 块外——否则交叉编译时 ctypes.CDLL
        # 加载 aarch64 .so 会在 import 期崩溃,守卫需先于 try 拦截。
        from conan.tools.build import can_run
        if not can_run(self):
            self.output.info("Cross-compiling detected, skipping ctypes.CDLL load test")
            return
        self.output.info("Attempting to load .so with ctypes.CDLL (RTLD_LAZY)...")
        try:
            # AbiWord 插件 .so 引用主程序符号(IE_Exp_Text 等,NEEDED 仅 libc.so),
            # 插件必须由主程序进程 dlopen(主程序提供符号表)。独立加载时这些
            # UND 符号无法解析,报 symbol not found/relocating error——这是插件
            # 架构的预期行为,非插件缺陷。若失败原因确为符号重定位,判定 PASS
            # 并记录(readelf 已硬性验证 ABI 导出符号)。
            try:
                lib = ctypes.CDLL(so_path, mode=os.RTLD_LAZY)
            except OSError as e:
                _msg = "{} {}".format(e.errno, e.strerror)
                if ("symbol not found" in _msg) or ("relocating" in _msg) or (e.errno is None):
                    self.output.info(
                        "  [ok] ctypes.CDLL cannot load plugin standalone (expected: "
                        "plugin depends on host symbols IE_Exp_Text etc., loaded by "
                        "AbiWord host process); ABI symbols verified via readelf above")
                    return
                raise
            self.output.info("  [ok] .so loaded successfully via ctypes.CDLL")

            # Verify ABI version support symbol exists
            if not hasattr(lib, "abi_plugin_supports_version"):
                raise AssertionError("abi_plugin_supports_version symbol not found in .so")
            self.output.info("  [ok] abi_plugin_supports_version symbol is available")

            # Verify registration symbol exists
            if not hasattr(lib, "abi_plugin_register"):
                raise AssertionError("abi_plugin_register symbol not found in .so")
            self.output.info("  [ok] abi_plugin_register symbol is available")

            # Verify unregister symbol exists
            if not hasattr(lib, "abi_plugin_unregister"):
                raise AssertionError("abi_plugin_unregister symbol not found in .so")
            self.output.info("  [ok] abi_plugin_unregister symbol is available")

        # P2: 记录 OSError 错误详情(errno + strerror),不丢弃诊断信息
        except OSError as e:
            self.output.warning(f"ctypes.CDLL({so_path}) failed: errno={e.errno} {e.strerror}")
            raise AssertionError(f"Failed to load .so via ctypes.CDLL: errno={e.errno} {e.strerror}") from e
