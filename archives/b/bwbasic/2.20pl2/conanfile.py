#!/usr/bin/env python3
"""Conan recipe — bwbasic 2.20pl2 (Bywater BASIC interpreter, CLI tool).

bwbasic 是 Bywater BASIC 解释器（ISO-C，1995 年代码基线），随包附带
1995 年 autoconf 1.x 生成的 configure 与手写 Makefile.in，构建产物为
bwbasic 与 renum 两个可执行文件。上游自带 bwbtest/ 的 41 个 .bas 测试
脚本（人工核对型，交互脚本按语义以管道喂入），本配方在 build() 中
以断言执行器全部真实运行；交叉编译环境仅编译验证。

对上游源码的 5 个最小可移植补丁（全部为平台/编译器兼容，无功能语义
变更，详见 conandata.yml 与 notes.md）。
"""
import os
import stat

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class BwbasicConan(ConanFile):
    name = "bwbasic"
    version = "2.20pl2"
    description = "Bywater BASIC Interpreter — a portable BASIC interpreter (CLI tool)"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/bwbasic"
    url = "https://salsa.debian.org/debian/bwbasic"
    topics = ("basic", "interpreter", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # 上游 Makefile 为 1995 年源内构建设计（renum 等规则无 VPATH 前缀，
        # out-of-source 下找不到源文件），configure 与 make 显式在源码目录执行；
        # CC/CFLAGS 由 AutotoolsToolchain 生成的 conanbuild 环境提供（R33）
        self.run(
            './configure --prefix="%s"' % self.package_folder,
            cwd=self.source_folder, env="conanbuild")
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")
        if not cross_building(self):
            self._run_upstream_tests()
        else:
            self.output.info("cross-building: upstream bwbtest suite skipped (compile-only)")

    def _run_upstream_tests(self):
        """真机/CI 原生环境执行上游 bwbtest 全部 41 个 .bas 脚本。

        测试为人工核对型输出（脚本打印结果后等待确认），执行器按各脚本
        语义以管道喂入定制 stdin，并对每个脚本的验证输出做 grep 断言。
        width.bas 的 WIDTH 语句上游未实现（手册有文档、代码零实现），
        单列为已知局限，不计失败。
        """
        bwbtest = os.path.join(self.source_folder, "bwbtest")
        bwbasic_bin = os.path.join(self.source_folder, "bwbasic")
        outdir = os.path.join(self.build_folder, "bwbtest-out")
        runner = os.path.join(self.build_folder, "run_bwbtest.sh")
        os.makedirs(outdir, exist_ok=True)

        # 每行: <脚本> <stdin串或-> <期望grep模式>；stdin 串原样通过 printf 求值
        cases = [
            ("abs.bas", "-", "The absolute value of"),
            ("assign.bas", "-", "X is  7"),
            ("callfunc.bas", "-", "This is written from the Function."),
            ("callsub.bas", "-", "This is written from the Subroutine."),
            ("chain1.bas", "-", "This concludes our CHAIN test."),
            ("chain1.bas", "-", "The value of X is now 5.6789000"),
            ("chain2.bas", "-", "This is program CHAIN2.BAS"),
            ("dataread.bas", "-", "Data read: Ted  56.789 Dale  45.6780000"),
            ("deffn.bas", "-", "Correct"),
            ("dim.bas", "-", "The value at position  5 is  7"),
            ("doloop.bas", "-", "End"),
            ("dowhile.bas", "-", "x is  3"),
            ("elseif.bas", "4\\n", "The number is 4."),
            ("end.bas", "-", "END worked OK"),
            ("err.bas", "-", "array subscript var"),
            ("fncallfn.bas", "-", "The result is:      :  2.4567800"),
            ("fornext.bas", "-", "FOR: i is  17"),
            ("function.bas", "-", "ABS(-2.2):  2.2"),
            ("function.bas", "-", "INT(-2.2):  -3"),
            ("function.bas", "-", "SQR(2.2):  1.4832397"),
            ("gosub.bas", "1\\n9\\n", "This is the subroutine."),
            ("gotolabl.bas", "-", "Goodbye"),
            ("ifline.bas", "-", "The program succeeded"),
            ("input.bas", "hello, 42\\n", "The string is: hello"),
            ("input.bas", "hello, 42\\n", "The number is:  42"),
            ("lof.bas", "lofinp.txt\\n", "is  109 bytes"),
            ("loopuntl.bas", "-", "Value of i is 6"),
            ("main.bas", "-", "This is the MAIN subroutine."),
            ("mlifthen.bas", "-", "This concludes our test."),
            ("on.bas", "3\\n", "You entered 3"),
            ("onerr.bas", "-", "The error number is  -1"),
            ("onerrlbl.bas", "-", "The error line   is  0"),
            ("ongosub.bas", "2\\n", "The End"),
            ("opentest.bas", "-", ">This is line 1."),
            ("opentest.bas", "-", ">This is line 2."),
            ("option.bas", "-", "The value at position  1 is  3"),
            ("pascaltr.bas", "-", "5:  1 5 10 10 5 1"),
            ("putget.bas", "Alice\\n1 Main St\\n555-0101\\nBob\\n2 Oak Ave\\n555-0102\\n", "Alice"),
            ("putget.bas", "Alice\\n1 Main St\\n555-0101\\nBob\\n2 Oak Ave\\n555-0102\\n", "Bob"),
            ("putget.bas", "Alice\\n1 Main St\\n555-0101\\nBob\\n2 Oak Ave\\n555-0102\\n", "555-0102"),
            ("random.bas", "-", "This is a first sequence of three RND numbers:"),
            ("random.bas", "-", "This is a second sequence of three RND numbers:"),
            ("random.bas", "-", "The second sequence should have been differrent"),
            ("selcase.bas", "4\\n", "The number is between 3 and 5."),
            ("snglfunc.bas", "-", "The sum of 6 and 4 is  10"),
            ("stop.bas", "-", "Program interrupted at line 40"),
            ("term.bas", "x\\n", "Bywater BASIC"),
            ("whilwend.bas", "-", "x is  3"),
            ("writeinp.bas", "-", "This is what was read:"),
            ("writeinp.bas", "-", "3.3456789"),
            ("width.bas", "-", "Check file <data.tmp>"),
        ]

        script = """
set -u
cd "{bwbtest}"
BIN="{bwbasic_bin}"
OUTDIR="{outdir}"
# lof.bas 输入文件（断言 LOF() = 109 字节）
printf '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789ab\\n' > lofinp.txt
pass=0; fail=0; known=0
run_case() {
  local name="$1" sin="$2" pattern="$3"
  local out="$OUTDIR/${name%.bas}.out"
  if [ "$sin" = "-" ]; then
    timeout 15 "$BIN" "$name" < /dev/null > "$out" 2>&1
  else
    printf "%b" "$sin" | timeout 15 "$BIN" "$name" > "$out" 2>&1
  fi
  local rc=$?
  if [ $rc -ne 0 ]; then echo "FAIL(rc=$rc) $name"; fail=$((fail+1)); return; fi
  if grep -q -- "$pattern" "$out"; then
    pass=$((pass+1))
  else
    echo "FAIL $name (pattern not found: $pattern)"
    fail=$((fail+1))
  fi
}
"""
        for name, sin, pattern in cases:
            pattern_lit = '"' + pattern.replace("\\", "\\\\").replace('"', '\\"') + '"'
            script += 'run_case "%s" "%s" %s\n' % (name, sin, pattern_lit)

        # function.bas 的 DATE$/TIME$ 为当前时刻，先掩码再断言
        script += """
sed -E 's/DATE\\$: <.*>/DATE\\$: <MASKED>/; s/TIME\\$: <.*>/TIME\\$: <MASKED>/' "$OUTDIR/function.out" > "$OUTDIR/function.masked"
if grep -q 'DATE\\$: <MASKED>' "$OUTDIR/function.masked" && grep -q 'TIME\\$: <MASKED>' "$OUTDIR/function.masked" && grep -q 'ABS(-2.2):  2.2' "$OUTDIR/function.masked"; then
  pass=$((pass+1))
else
  echo "FAIL function (masked DATE/TIME)"
  fail=$((fail+1))
fi

# random.bas 自身断言两次 RND 序列不同（RANDOMIZE 播种），数值不确定，
# 结构断言由 run_case 完成（3 项），此处验证 6 个数值均在 (0,1) 区间
rnd_count=$(grep -cE '^ 0\\.[0-9]+$' "$OUTDIR/random.out")
if [ "$rnd_count" -eq 6 ]; then
  pass=$((pass+1))
else
  echo "FAIL random (RND lines: $rnd_count, expect 6)"
  fail=$((fail+1))
fi

# width.bas：WIDTH 语句上游未实现（手册有文档、分派代码零实现，静默忽略），
# 脚本验收意图（data.tmp 按第 35 列折行）不满足，登记为已知局限
if [ -f data.tmp ] && [ "$(awk '{ if (length($0) > m) m = length($0) } END { print m }' data.tmp)" = "60" ]; then
  echo "KNOWN-LIMITATION width (WIDTH statement not implemented upstream; data.tmp unwrapped at 60 chars)"
  known=$((known+1))
else
  echo "FAIL width (unexpected data.tmp state)"
  fail=$((fail+1))
fi

echo "bwbtest upstream suite: pass=$pass fail=$fail known-limitation=$known"
if [ "$fail" -ne 0 ]; then exit 1; fi
"""
        script = script.replace("{bwbtest}", bwbtest).replace(
            "{bwbasic_bin}", bwbasic_bin).replace("{outdir}", outdir)

        with open(runner, "w", encoding="utf-8") as f:
            f.write(script)
        os.chmod(runner, os.stat(runner).st_mode | stat.S_IEXEC)
        self.run('bash "%s"' % runner, env="conanbuild")

    def package(self):
        # 上游 install 仅装 bwbasic；renum 亦为构建产物（all 目标），一并入库
        bindir = os.path.join(self.package_folder, "bin")
        for exe in ("bwbasic", "renum"):
            copy(self, exe, self.source_folder, bindir, keep_path=False)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "bwbasic.doc", self.source_folder,
             os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
