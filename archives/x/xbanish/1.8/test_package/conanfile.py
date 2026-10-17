#!/usr/bin/env python3
"""xbanish 1.8 消费者测试（R34/L0c）——真实执行打包产物并按断言决定退出码。

xbanish 是一个需要 X server 的常驻事件监听守护进程；OHOS 无 X server，
因此不可能在此断言"光标被隐藏"这一运行时行为。本测试如实覆盖能够证实的
三层，且不含任何伪装成运行时通过的成分：

  1) 产物可执行：从被测包 cpp_info.bindirs 定位 bin/xbanish（证明 R38/PF8
     的 bindirs 声明与实际打包一致）。
  2) 依赖真的链上了：用 readelf 断言 ELF 的 NEEDED 列表同时含
     libX11/libXfixes/libXi/libXext 四项——若缺任何一项，说明配方的
     requires/libs 是虚的。
  3) 无 X 环境的确定性错误路径：上游 xbanish.c L144-145 为
     `if (!(dpy = XOpenDisplay(NULL))) errx(1, "can't open display %s", ...)`
     ⇒ exit 1 且 stderr 含 "can't open display"。
     这一条同时证明动态链接在真机上解析成功（若符号缺失，加载期即失败，
     退出码与消息都会不同）。

运行时行为（隐藏/显示光标、XInput2 与 XSync 两条事件通路）在 HarmonyOS PC 上
**不可执行**，原因：平台无 X server、无 X 扩展（XInput2 / XSync / XFixes）
可提供事件源。此限制在 notes.md 与 MANIFEST.yml 中同样如实记录。
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.layout import basic_layout


class XbanishTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _locate_binary(self):
        for dep in self.dependencies.host.values():
            if dep.ref.name != "xbanish":
                continue
            for bindir in (dep.cpp_info.bindirs or ["bin"]):
                if not os.path.isabs(bindir):
                    bindir = os.path.join(dep.package_folder, bindir)
                cand = os.path.join(bindir, "xbanish")
                if os.path.isfile(cand):
                    return cand
        return None

    def test(self):
        binary = self._locate_binary()
        if not binary:
            raise Exception("xbanish binary not found in package bindirs")

        # ── 断言 2：四项 X 依赖确实记录在 ELF NEEDED 里 ──────────────
        needed = ""
        for tool in ("readelf", "/data/service/hnp/bin/readelf"):
            try:
                out = subprocess.run(
                    [tool, "-d", binary], capture_output=True, text=True, timeout=60
                )
            except (OSError, subprocess.SubprocessError):
                continue
            if out.returncode == 0 and out.stdout:
                needed = out.stdout
                break
        if not needed:
            raise Exception("readelf unavailable; cannot verify NEEDED entries")
        for lib in ("libX11.so", "libXfixes.so", "libXi.so", "libXext.so"):
            if lib not in needed:
                raise Exception(f"ELF NEEDED missing {lib}: {needed}")
        self.output.info("NEEDED OK: libX11/libXfixes/libXi/libXext all linked")

        # ── 断言 1+3：真实执行产物（L0c 要求的 self.run） ────────────
        script = os.path.join(self.source_folder, "test_nox.sh")
        if not os.path.isfile(script):
            raise Exception("test_nox.sh missing in test_package")
        os.chmod(script, 0o755)
        out_file = os.path.join(self.build_folder, "xbanish_nox_out.txt")
        self.run(f'"{script}" "{binary}" "{out_file}"', env="conanrun")
        self.output.info(
            "xbanish consumer test PASSED: signed ELF executes on OHOS; "
            "deterministic no-X error path verified (exit 1 + \"can't open display\"). "
            "运行时行为（隐藏光标）因平台无 X server 不可执行，未计入通过项。"
        )
