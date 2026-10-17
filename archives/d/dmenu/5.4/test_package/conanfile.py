#!/usr/bin/env python3
"""Conan test_package — dmenu 5.4 (application: run CLI binaries, assert behavior).

上游测试清点（R51，证据见本目录 MANIFEST.yml）：dmenu 5.4 上游无测试套件
（无 tests/ 目录、无 make check/test 目标，Makefile 目标仅
all/dmenu/stest/clean/dist/install/uninstall）⇒ N_static=0，
按规则以消费者测试补位：真实执行被测包安装的 dmenu 与 stest 二进制并断言行为。
"""
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile


class DmenuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if str(self.settings.os) != "OHOS":
            self.run("sh test.sh", env="conanrun")
            return

        # ① 聚合 host 依赖 lib 目录：归档依赖包（libx11/libxft/fontconfig 族）
        #    cpp_info 未声明 libdirs，conanrun.sh 不注入 LD_LIBRARY_PATH（首轮 CI 红）。
        libdirs = []
        for dep in self.dependencies.host.values():
            pf = dep.package_folder
            if not pf:
                continue
            for sub in ("lib", "lib64"):
                d = os.path.join(str(pf), sub)
                if os.path.isdir(d):
                    libdirs.append(d)

        # ② 重签 stage：制品仓预构建 .so 的签名属于发布机，测试机装载器
        #    报 "Error loading shared library"（#12032 评论流 CIW-2 定性 + 本地
        #    交叉加载复现：制品版 libXft.so.2 重签前拒载、重签后可加载）。
        #    全部依赖 .so 复制到归档树外的临时 stage 目录统一去签+自签，
        #    不触碰 conan 缓存；stage 目录用 ~/tmp（CI worker 的 /tmp 只读）。
        stage = None
        try:
            if libdirs:
                base = os.path.join(os.path.expanduser("~"), "tmp")
                os.makedirs(base, exist_ok=True)
                stage = tempfile.mkdtemp(prefix="dmenu-deps-", dir=base)
                signer = self._signer()
                objcopy = shutil.which("llvm-objcopy") or "llvm-objcopy"
                for d in libdirs:
                    for name in sorted(os.listdir(d)):
                        src = os.path.join(d, name)
                        if ".so" not in name or not os.path.isfile(src):
                            continue
                        dst = os.path.join(stage, name)
                        shutil.copy2(src, dst)
                        subprocess.run([objcopy, "--remove-section", ".codesign", dst],
                                       check=False)
                        signed = dst + ".signed"
                        subprocess.run([signer, "sign", "-inFile", dst, "-outFile", signed,
                                        "-selfSign", "1"], check=True)
                        os.replace(signed, dst)
                ldp = ":".join([stage] + libdirs)
            else:
                ldp = ""
            prefix = ('export LD_LIBRARY_PATH="%s"; ' % ldp) if ldp else ""
            self.run(prefix + "sh test.sh", env="conanrun")
        finally:
            if stage:
                shutil.rmtree(stage, ignore_errors=True)

    def _signer(self):
        """binary-sign-tool 不在 CI PATH（PATH 无 hnp/bin），按已知安装位置候选。"""
        for c in (shutil.which("binary-sign-tool"),
                  "/data/service/hnp/bin/binary-sign-tool",
                  "/data/app/bin/binary-sign-tool"):
            if c and os.path.isfile(c):
                return c
        raise ConanException(
            "OHOS consumer test needs binary-sign-tool (looked in PATH and hnp bins)")
