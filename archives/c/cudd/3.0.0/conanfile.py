#!/usr/bin/env python3
"""Conan recipe for cudd 3.0.0 (ivmai/cudd).

CUDD 是 BDD（二元决策图）操纵库：libcudd 核心 + 可选 dddmp（BDD 转储）+
cplusplus 封装。纯 C/C++，零第三方依赖（W0 预检通过）。

OHOS 适配要点：
- 预生成 configure 的官方 tag tarball；显式 --build/--host=
  aarch64-unknown-linux-gnu（build==host 原生，跳过 config.guess 写盘探针，
  沿用 libmatheval 教训）。
- --enable-dddmp --enable-obj：打开两个可选子库，否则 dddmp/cplusplus 的
  上游测试脚本被门控关闭（默认 no）。
- 上游测试体系完整且随包分发：3 个 check_PROGRAMS（nanotrav/testobj+testmulti/
  testdddmp）+ 3 个 TAP 脚本（test_ntrv 13 点 / test_obj 2 点 / test_dddmp
  7 点，共 22 个断言），测试数据（.blif/.out/.bdd 等）经 dist_check_DATA
  随 tarball 分发。build() 内 make check 全量实跑。
- 顶层 all 依赖 html/index.html + doc/cudd.pdf，两者在无 doxygen/pdflatex
  时为空规则，不阻碍构建。
- OHOS 适配补丁（仅改上游测试脚手架，不改库源码/断言语义）：
  1) test_*.test.in 的 mkfifo 习语改普通临时文件（HMFS 禁命名管道）；
  2) automake TAP driver 的 fd3 日志通道改 gawk 原生重定向（OHOS /bin/sh
     不把 >2 的 fd 传给子进程，gawk 的 `cat >&3` 与 `exec 2>&3` 均报
     Bad file descriptor，check-TESTS 整体失败）。
"""
from conan import ConanFile
from conan.tools.files import copy, get
import os


class CuddConan(ConanFile):
    name = "cudd"
    version = "3.0.0"
    description = "CUDD - Colorado University Decision Diagram package (BDD manipulation)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ivmai/cudd"
    url = ""  # CI fills this
    topics = ("bdd", "decision-diagram", "formal-verification")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # HMFS 上 mkfifo Operation not permitted（CI #43926 实测；早期 worker
        # 偶发可用导致 rcn25 抖动 PASS/FAIL）。test_*.test.in 的比对用
        # "sed > fifo & sed > fifo & diff fifo fifo" 命名管道习语，改成顺序
        # 写普通临时文件再 diff，语义完全等价（diff 只在两个 sed 完成后读）。
        import re
        for rel in ("cplusplus/test_obj.test.in", "cudd/test_cudd.test.in",
                    "mtr/test_mtr.test.in", "nanotrav/test_ntrv.test.in"):
            path = os.path.join(self.source_folder, rel)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            assert "mkfifo" in text, f"{rel} 结构已变更，需同步 fifo 替换"
            text = re.sub(r"^[ \t]*mkfifo[^\n]*\n", "", text, flags=re.M)
            text = re.sub(r"^[ \t]*# Create FIFOs[^\n]*\n", "", text, flags=re.M)
            text = text.replace("_fifo &\\", "_fifo ;\\")
            text = re.sub(r"\brm ((?:\./)?\w+/tst_fifo (?:\./)?\w+/out_fifo)",
                          r"rm -f \1", text)
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
        # automake 的 TAP driver（build-aux/tap-driver.sh）用 `} 3>"$log_file"`
        # 开 fd3，再由 gawk `print | "cat >&3"` 与内层 subshell `exec 2>&3`
        # 写日志。OHOS 的 /bin/sh（dash 系）把 >2 的 fd 标为非可继承，子进程
        # 拿不到 fd3 → `sh: >&3: bad file descriptor` → gawk broken pipe →
        # `tap-driver.sh: fatal: I/O or internal error` → check-TESTS 整体失败
        # （CI #44892 / #44912，worker 011/036；同一提交在 worker-012
        # #43953 通过，属跨 worker 抖动）。改为 gawk 原生重定向 —— 这正是
        # 脚本自身 TODO 里标注的优化点：`| "cat >&3"` → `>> log_file`
        # （log_file 已由 -v 传入），`exec 2>&3` → `exec 2>>"$log_file"`，
        # 彻底不再依赖 fd3，行为等价（日志内容与 trs 判定不变）。
        driver = os.path.join(self.source_folder, "build-aux", "tap-driver.sh")
        with open(driver, encoding="utf-8") as fh:
            dtext = fh.read()
        assert dtext.count('| "cat >&3"') == 2 and "exec 2>&3" in dtext, \
            "build-aux/tap-driver.sh 结构已变更，需同步 fd3 补丁"
        dtext = dtext.replace('| "cat >&3"', ">> log_file")
        dtext = dtext.replace("exec 2>&3", 'exec 2>>"$log_file"')
        with open(driver, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(dtext)

    def build(self):
        src = self.source_folder
        triple = "aarch64-unknown-linux-gnu"
        # 设备默认 TMPDIR(HMDFS) 临时文件权限受限，config.status 的
        # confg*/subs*.awk 机制会 Permission denied；指到可写可执行的
        # build 目录（libmatheval 同款教训，cuba/cracklib CI 实测复现）。
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp
        # 真正的根因（CI #43778 在 TMPDIR 修复后仍复现）：config.status 用
        # (umask 077 && mktemp -d ./confXXXXXX) 在 cwd 建临时目录，随后往里写
        # subs*.awk 被 HMFS 拒绝（700 目录写受限；conf 目录不走 TMPDIR）。
        # configure 生成的 config.status 从其 here-doc 继承同样文本，把
        # configure 里的 umask 077 全部放宽为 022 即同步修复。
        configure_path = os.path.join(src, "configure")
        with open(configure_path, encoding="utf-8") as fh:
            configure_text = fh.read()
        if "umask 077" in configure_text:
            with open(configure_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(configure_text.replace("umask 077", "umask 022"))
        shared = "--enable-shared" if self.options.shared else "--disable-shared"
        static = "--disable-static" if self.options.shared else "--enable-static"
        self.run(
            f"./configure --build={triple} --host={triple} {shared} {static} "
            f"--enable-dddmp --enable-obj --prefix=/__pkg_prefix__",
            cwd=src,
        )
        self.run("make -j4", cwd=src)
        # 层1：上游 TAP 测试套件实跑（3 脚本 / 22 断言）
        # 诊断：make check 失败时倾倒日志。logTail 只留尾部 ~4000 字符，
        # 最有价值的 nanotrav/differences 必须最后打印（CI #43916 与 #43838
        # 的 rcn25 结果翻转，疑似 FIFO 管道竞态，需看 diff 内容定性）。
        self.run(
            "make check || { "
            "echo '==== test-suite.log ===='; cat test-suite.log 2>/dev/null; "
            "echo '==== nanotrav/test-suite.log ===='; cat nanotrav/test-suite.log 2>/dev/null; "
            "echo '==== nanotrav/differences (printed last, survives logTail) ===='; "
            "cat nanotrav/differences 2>/dev/null; "
            "exit 1; }",
            cwd=src,
        )

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "cudd.h", src=os.path.join(self.source_folder, "cudd"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "dddmp.h", src=os.path.join(self.source_folder, "dddmp"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "cuddObj.hh", src=os.path.join(self.source_folder, "cplusplus"),
             dst=os.path.join(self.package_folder, "include"))
        for pat in ("*.a", "*.so", "*.so.*"):
            copy(self, pat, src=os.path.join(self.source_folder, "cudd", ".libs"),
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["cudd"]
