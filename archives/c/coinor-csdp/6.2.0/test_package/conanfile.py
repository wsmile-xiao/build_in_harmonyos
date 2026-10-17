#!/usr/bin/env python3
"""Conan test_package — coinor-csdp 6.2.0（真跑打包产物：库消费者 + 2 个 CLI）。

断言合计 **15 项**（R34：真跑被测产物，非空壳），分两层：

库消费者 test_csdp_consumer.c（①–⑤，5 项，在 C 程序内断言，任一失败即非 0 退出）：
  ① read_prob() 载入上游夹具 theta1.dat-s 返回 0；
  ② 问题规模 n=50、k=104（CSDP 语义：n=矩阵维度、k=约束数，与夹具头 104/1/50 一致）；
  ③ easy_sdp() 求解返回 0（Success）；
  ④ primal 目标值 = 2.3000000e+01（|Δ| ≤ 1e-5，即上游 "six digits" 判据）；
  ⑤ dual   目标值 = 2.3000000e+01（|Δ| ≤ 1e-5）。
  数值锚点取上游 test/theta1.correct 的最优值（不是本机自测基线）。

test() 层（⑥–⑮，10 项）：
  ⑥ 库消费者退出码 0（①–⑤ 的总闸）；
  ⑦ csdp --version 退出码 0；
  ⑧ csdp --version 输出含 "6.2.0"（版本自报 == 配方版本）；
  ⑨ theta --version 退出码 0；
  ⑩ theta --version 输出含 "6.2.0"；
  ⑪ csdp <theta1.dat-s>（真实求解上游夹具）退出码 0；
  ⑫ 其输出含 "Success: SDP solved"；
  ⑬ 其输出含 "2.3000000e+01"（与上游 .correct 最优值一致）；
  ⑭ theta <g50>（上游 Lovasz theta 夹具）退出码 0；
  ⑮ 其输出含 "The Lovasz Theta Number is 2.3000000e+01"。

工作目录卫生：conan create 用**仓库内** test_package 文件夹就地跑（source folder
= build folder = 本仓库目录），因此消费者产物与全部输出重定向都落
tempfile.mkdtemp()（TMPDIR=工作区 tmp，仓库外），finally 删除——避免残留未跟踪
文件污染「工作区干净」前置（coinor-cbc 同款教训）。
消费者静态直链 libopenblas.a（与被测配方同款链接口径）：产物可裸跑，不依赖
conanrun 的 LD_LIBRARY_PATH。

OHOS：运行前对 ELF 自签 binary-sign-tool（coinor-cbc 同款口径），否则加载器
EPERM；重复自签幂等（.codesign 仍为 1 节）。
"""
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class CoinorCsdpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_csdp_consumer.c", "theta1.dat-s", "g50"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ── OHOS ELF 自签（coinor-cbc 同款口径）──────────────────────────────
    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not (os.path.isfile(signer) and os.path.isfile(readelf)):
            raise ConanException("required OHOS signing tools are missing")
        if not os.path.isfile(path):
            return
        output = path + ".signed"
        if os.path.lexists(output):
            os.unlink(output)
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True, timeout=120,
        )
        sections = subprocess.run(
            [readelf, "-SW", output], check=True, capture_output=True, text=True, timeout=60,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"Signed ELF has invalid .codesign count: {path}")
        os.chmod(output, (os.stat(output).st_mode & 0o777) | 0o055)
        os.replace(output, path)

    def test(self):
        if cross_building(self):
            self.output.warning("cross-building: cannot run packaged csdp here")
            return

        pkg = self.dependencies["coinor-csdp"].package_folder
        ob = self.dependencies["openblas"].package_folder
        src = self.source_folder
        csdp = os.path.join(pkg, "bin", "csdp")
        theta = os.path.join(pkg, "bin", "theta")
        for path in (csdp, theta):
            if not os.path.isfile(path):
                raise ConanException(f"packaged binary missing: {path}")
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(csdp)
            self._sign_ohos_elf(theta)

        problems = []
        tmp = tempfile.mkdtemp(prefix="csdp-tp-")  # 仓库外工作目录（卫生）
        try:
            # ── ①–⑤ 库消费者：编译 + 运行 ────────────────────────────────
            consumer = os.path.join(tmp, "test_csdp_consumer")
            cc = os.environ.get("CC", "clang")
            self.run(
                f"{cc} -O2 -fPIC -I'{pkg}/include' '{src}/test_csdp_consumer.c' "
                f"'{pkg}/lib/libsdp.a' '{ob}/lib/libopenblas.a' -lm -o '{consumer}'",
                env="conanbuild",
            )
            rc, text = self._run_to_file(
                f"'{consumer}' '{src}/theta1.dat-s'", os.path.join(tmp, "consumer.out"))
            self.output.info("[consumer]\n" + text.strip())
            self._assert(rc == 0, "⑥ 库消费者退出码 0（内部断言 ①–⑤ 全过）", problems)

            # ── ⑦–⑧ csdp 版本自报 ────────────────────────────────────────
            rc, text = self._run_to_file(f"'{csdp}' --version",
                                         os.path.join(tmp, "csdp-version.out"))
            self._assert(rc == 0, "⑦ csdp --version 退出码 0", problems)
            self._assert("6.2.0" in text, "⑧ csdp --version 输出含 6.2.0", problems)

            # ── ⑨–⑩ theta 版本自报 ───────────────────────────────────────
            rc, text = self._run_to_file(f"'{theta}' --version",
                                         os.path.join(tmp, "theta-version.out"))
            self._assert(rc == 0, "⑨ theta --version 退出码 0", problems)
            self._assert("6.2.0" in text, "⑩ theta --version 输出含 6.2.0", problems)

            # ── ⑪–⑬ CLI 真实求解上游夹具 theta1.dat-s ────────────────────
            rc, text = self._run_to_file(f"'{csdp}' '{src}/theta1.dat-s'",
                                         os.path.join(tmp, "csdp-solve.out"))
            self.output.info("[csdp theta1]\n" + text.strip())
            self._assert(rc == 0, "⑪ csdp theta1.dat-s 退出码 0", problems)
            self._assert("Success: SDP solved" in text,
                         "⑫ csdp 输出含 'Success: SDP solved'", problems)
            self._assert("2.3000000e+01" in text,
                         "⑬ csdp 输出目标值 2.3000000e+01（== 上游 .correct）", problems)

            # ── ⑭–⑮ CLI 求解上游 Lovasz theta 夹具 g50 ───────────────────
            rc, text = self._run_to_file(f"'{theta}' '{src}/g50'",
                                         os.path.join(tmp, "theta-g50.out"))
            self.output.info("[theta g50]\n" + text.strip())
            self._assert(rc == 0, "⑭ theta g50 退出码 0", problems)
            self._assert("The Lovasz Theta Number is 2.3000000e+01" in text,
                         "⑮ theta 输出 Lovasz theta = 2.3000000e+01（== 上游 .correct）",
                         problems)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        if problems:
            raise ConanException(f"test_package 断言失败 {len(problems)} 项: "
                                 + "; ".join(problems))
        self.output.info("[assert] 15/15 全部通过（库消费者 5 + test() 层 10）")

    def _assert(self, ok, desc, problems):
        self.output.info(f"[assert] {'✅' if ok else '❌'} {desc}")
        if not ok:
            problems.append(desc)

    def _run_to_file(self, cmd, out_path):
        """跑命令并把输出重定向到仓库外文件，返回 (rc, 输出文本)。"""
        rc = self.run(f"{cmd} > '{out_path}' 2>&1", env="conanrun", ignore_errors=True)
        with open(out_path, encoding="utf-8", errors="replace") as fh:
            return rc, fh.read()
