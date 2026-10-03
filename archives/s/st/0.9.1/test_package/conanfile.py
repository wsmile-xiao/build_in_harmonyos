#!/usr/bin/env python3
"""st test_package — 纯 Conan 消费者测试（跑打包出来的 st 二进制，R34 非空壳）。

返修-2（test_package 运行期装载）：已发布的 libxft/fontconfig 两枚依赖 .so 带**设备绑定**
.codesign，本机 ldso 拒载 ⇒ `st -v` rc=127。修法落在 test() 真跑二进制之前：剥段+自签。
（仅作用于本次测试的本地缓存视图，不改依赖包配方、不改判据。）
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run

# ── 返修-2 根因与修法（实测出处见 notes.md 对话 #3）──────────────────────────────
# CI build #65929 首错：[st -v] rc=127
#   Error loading shared library libXft.so.2 / libfontconfig.so.1（其余 7 件正常装载）
# 判别矩阵（同一二进制同一环境，只换这两件的字节）：
#   裸跑 errload=9 → LD_LIBRARY_PATH=依赖 9 目录 errload=0 打印 st 0.9.1
#   → 把**已发布原件**插到最前 errload=2（文案与 CI 逐字相同）
#   ⇒ 路径/环境/权限全部有效，变量只剩字节内容 ⇒ 内容级拒载（设备绑定签名）。
# 修法依据：知识条目 E517 `remove-then-resign-in-task-local-view` + E077 四步（剥段→改→重签→chmod）
#   + E135 + 经验库 12a「配方侧有签名工具就签、缺失降级直跑最稳」。
_REPAIR_TARGETS = (("libxft", "libXft.so.2"), ("fontconfig", "libfontconfig.so.1"))


class StTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    # ── 工具定位：**不写死任何本机绝对路径**（本仓 W4 会 grep 路径痕迹）──────────
    # ① 先走当前进程 PATH；② 再走 profile [conf] 提供的编译器所在目录（那两个工具与它同处一个工具箱）。
    def _tool(self, name):
        found = shutil.which(name)
        if found:
            return found
        executables = self.conf.get("tools.build:compiler_executables") or {}
        cc = executables.get("c") or executables.get("cpp")
        if cc:
            candidate = os.path.join(os.path.dirname(cc), name)
            if os.path.isfile(candidate):
                return candidate
        return None

    def _repair_dependency_signatures(self):
        """E517/E077：把被本机 ldso 拒载的两枚依赖 .so 就地「剥 .codesign + selfSign 重签」。

        幂等：已签件再走一遍得到完全相同的字节（实测 md5 不变），故本机已绿的缓存不受影响。
        工具缺失 ⇒ 降级直跑并打印告警（经验库 12a），不把「工具缺」伪装成绿。
        """
        objcopy = self._tool("llvm-objcopy")
        signer = self._tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning(
                "签名工具缺失（llvm-objcopy=%s, binary-sign-tool=%s）⇒ 降级直跑，不重签"
                % (objcopy, signer))
            return
        # 经验库 12a：签名器要剔除 LD_LIBRARY_PATH（构建环境会注入工具链运行时，劫持其 libc++）
        clean_env = {k: v for k, v in os.environ.items() if k != "LD_LIBRARY_PATH"}
        for ref, soname in _REPAIR_TARGETS:
            try:
                dep = self.dependencies[ref]
            except KeyError:
                self.output.warning("依赖 %s 不在图中 ⇒ 跳过重签" % ref)
                continue
            libdir = dep.cpp_info.libdir or os.path.join(dep.package_folder, "lib")
            # 软链（libfontconfig.so.1 → .1.17.0）要签**真实文件**；普通文件（libXft.so.2）签它自己
            target = os.path.realpath(os.path.join(libdir, soname))
            if not os.path.isfile(target):
                self.output.warning("未找到待签文件 %s ⇒ 跳过" % target)
                continue
            strip = subprocess.run([objcopy, "--remove-section", ".codesign", target],
                                   env=clean_env, capture_output=True, text=True)
            sign = subprocess.run(
                [signer, "sign", "-selfSign", "1", "-signAlg", "SHA256withECDSA",
                 "-inFile", target, "-outFile", target],
                env=clean_env, capture_output=True, text=True)
            if sign.returncode != 0:
                # 找得到工具却签不上 ⇒ 这就是第一条真实错误，红在这里，不留给装载器
                raise RuntimeError("重签失败（rc=%s）%s\nstdout=%s\nstderr=%s"
                                   % (sign.returncode, target, sign.stdout, sign.stderr))
            try:
                os.chmod(target, 0o755)  # E077 第四步：签名后权限可能收窄
            except OSError:
                pass
            self.output.info("已剥段+重签 %s（strip rc=%s / sign rc=0）" % (target, strip.returncode))

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["st"]
        bindir = pkg.cpp_info.bindirs[0] if pkg.cpp_info.bindirs else os.path.join(pkg.package_folder, "bin")
        self._repair_dependency_signatures()
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_st.py")
        # ST_BINDIR 交给测试脚本用（conanrun 注入依赖环境，路径显式传参）
        self.run('ST_BINDIR="%s" python3 "%s"' % (bindir, script), env="conanrun")
