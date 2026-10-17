#!/usr/bin/env python3
"""Conan recipe — ol (Otus Lisp) 2.7 (plain GNUmakefile)

Otus Lisp 是纯函数式、可嵌入的 Scheme 方言解释器。一次 release 构建产出：

  bin/ol        解释器（src/repl.S 把 repl fasl 内嵌进可执行文件）
  bin/olvm      剥离符号的独立虚拟机
  lib/libol.so  可嵌入的 VM 共享库（-DOLVM_NOMAIN -shared -fPIC）
  include/ol/   ol.h（嵌入 API）、vm.h（构建期由 src/olvm.c 生成）
  lib/ol/       Ol 标准库（libraries/**.scm|*.lisp）与 repl fasl

OHOS 适配要点：
  * 上游 ``make install`` 依赖 coreutils 的 install(1)，OHOS 未提供该工具，
    因此 package() 自行落盘（内容与上游 install 目标一致）。
  * 上游 olvm 目标在链接后执行 ``strip``；剥离后内核以 EPERM 拒绝执行
    （rc=126 "Operation not permitted"），故 package() 对 bin/ 下 ELF 统一
    用 binary-sign-tool 重新自签名（见 notes.md）。
  * 运行期默认 OL_HOME 为编译期 ``PREFIX/lib/ol``（PREFIX 取上游默认 /usr），
    package_info() 通过 runenv/buildenv 导出 OL_HOME=<包>/lib/ol 使其可重定位。
"""
import gzip
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


# 上游 ``extras/check.mk`` 把 ``%.bin.ok`` 规则整段注释掉（第 154 行起），
# 因此 ``tests/*.bin`` 用例在任何平台上都不会被执行——`tmp/check.log` 里没有它的
# 执行记录。这类用例既不是 PASS 也不是本包的 SKIP，按「上游默认不执行」申报。
UPSTREAM_DISABLED_TESTS = {"tests/fasl-binary.bin"}

# configure.mk 用 `HAVE_* ?=` 做编译探测；在命令行显式给出这四个值可以跳过
# 「每次子 make 都要跑 5 次 clang 探测」的开销（OHOS 上设备实测四项全为 1）。
UPSTREAM_FEATURE_FLAGS = ("HAVE_SOCKETS=1 HAVE_DLOPEN=1 HAVE_SECCOMP=1 "
                          "HAVE_MEMFD_CREATE=1")


class OlConan(ConanFile):
    name = "ol"
    version = "2.7"
    description = ("Otus Lisp (Ol): purely functional, embeddable Scheme dialect — "
                   "interpreter, olvm shared library and standard library")
    license = "LGPL-3.0-or-later OR MIT"
    homepage = "https://github.com/yuriy-chumak/ol"
    url = "https://github.com/yuriy-chumak/ol"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ol supports Linux/OHOS-style POSIX platforms, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ build

    def _compiler(self):
        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp.get("c") or "clang"

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler()
        # 上游 GNUmakefile 自行拼装 CFLAGS（-std=gnu99、HAVE_* 特性探测、发布优化）；
        # GNU make 的命令行变量优先级高于 makefile 内的 `CFLAGS +=`，所以传 CFLAGS=
        # 会**整段覆盖**上游 flags —— 这里只传 CC、UNAME 与编译期 PREFIX。
        #
        # UNAME=Linux：鸿蒙 `uname -s` 返回 "HarmonyOS"（HongMeng Kernel 的 sysname），
        # 会跳过上游 `ifeq ($(UNAME),Linux)` 分支，丢掉 `-Xlinker --export-dynamic`，
        # 于是运行期 `(dlsym (dlopen) "OLVM_ffi")` 取不到符号、otus/ffi 与 tests/ffi
        # 全部失败。OHOS 就是 Linux ABI（ELF + musl + lld），用上游 `UNAME ?=` 的
        # 覆盖入口显式声明，不改上游源码。
        self.run(f'make release -j1 CC="{cc}" UNAME=Linux PREFIX="/usr" '
                 f'{UPSTREAM_FEATURE_FLAGS}',
                 cwd=self.source_folder)
        self._run_upstream_tests(cc)

    # 上游 test runner 的四个分组目标（等价于 `make check` = regression-tests + check-reference：
    # language / rosettacode / ffi / doc-reference）。逐组单独落盘、再按固定顺序拼接：
    # 表格格式（每行 `| ok | ok |`）与串行 `make check` 完全一致，但四组可以并行跑，
    # 把 CI 墙钟时间从 ~1 小时压到 ~20 分钟（CI 的 conan create 默认 3600s 会在
    # 串行 `make check` 上超时，见 PR 正文的编排参数说明）。
    _UPSTREAM_GROUPS = ("language-tests", "rosettacode-tests", "ffi-tests", "check-reference")

    def _run_upstream_tests(self, cc):
        """build() 内运行上游测试套件，并解析真实计数。

        上游 test runner 的退出码不可信：language/rosettacode 的 ``tests`` 目标
        只在失败时把文件写进 FAILMARK、最后用 echo 收尾，**恒返回 0**；只有
        doc/reference 的 check-reference 会真正 exit 1。因此这里显式记录每个分组的 RC、
        逐行解析「测试名行 ↔ 结果单元格」的对应关系，并在任何失败、零用例或
        **出现未申报的静默未执行用例**时让 conan create 失败。
        """
        log = os.path.join(self.source_folder, "upstream-check.log")
        flags = f'CC="{cc}" UNAME=Linux PREFIX="/usr" {UPSTREAM_FEATURE_FLAGS}'
        # 每组一个**独立的源码树副本**：四个 make 实例并发时不再共享 tmp/、ol/olvm、
        # tests/ffi/src.inc 等中间产物，消除并发竞态（CI #46152 上 ffi 组曾因共享树 rc=2 失败）。
        base = os.path.dirname(self.source_folder)
        parts = []
        for g in self._UPSTREAM_GROUPS:
            copy_dir = os.path.join(base, f"ol-test-{g}")
            self.run(f'rm -rf "{copy_dir}" && cp -a "{self.source_folder}" "{copy_dir}"')
            parts.append((g, copy_dir, os.path.join(copy_dir, f"upstream-{g}.log")))
        parallel = " ".join(
            f'( cd "{d}" && make -j1 {flags} {g} > "{l}" 2>&1; '
            f'echo "UPSTREAM_GROUP_{g}_RC=$?" >> "{l}" ) &'
            for g, d, l in parts
        ) + " wait"
        self.output.info("running upstream test suite in 4 isolated parallel groups: "
                         + ", ".join(self._UPSTREAM_GROUPS))
        self.run(parallel, cwd=self.source_folder, env="conanbuild")
        # ③ 按固定顺序拼接成一份 upstream-check.log（与串行 make check 同格式）
        group_rcs = {}
        with open(log, "w", encoding="utf-8") as out:
            for g, _d, part in parts:
                chunk = open(part, encoding="utf-8", errors="replace").read()
                for ln in chunk.splitlines():
                    if ln.startswith(f"UPSTREAM_GROUP_{g}_RC="):
                        group_rcs[g] = int(ln.split("=", 1)[1])
                out.write(chunk)
            rc_overall = next((v for v in group_rcs.values() if v), 0)
            out.write(f"UPSTREAM_MAKE_CHECK_RC={rc_overall}\n")

        with open(log, encoding="utf-8", errors="replace") as f:
            content = f.read()
        lines = content.splitlines()

        # 收集「测试名行」与「已出结果的行」：表格里参考手册那一段是
        # `|doc/reference/x.md ...| ok | ok |` 同行出结果，其余分组的结果单元格
        # 在下一行（中间可能被上游 make 的 warning 打断）。
        declared, resolved = [], []
        for ln in lines:
            if ln.startswith("|") and re.search(r"\.(scm|bin|md)\b", ln):
                name = ln[1:].split(" ")[0]
                if name and name not in ("Test", "dbg.", "rel."):
                    declared.append(name)
                    if "| ok |" in ln or "|fail" in ln:
                        resolved.append(name)
            elif ("| ok |" in ln or "|fail" in ln) and declared and declared[-1] not in resolved:
                resolved.append(declared[-1])

        ok_cells = content.count("| ok |")
        fail_cells = content.count("|fail")
        groups = [ln for ln in lines if ln.startswith("# ")]
        rc = 0
        for ln in lines:
            if ln.startswith("UPSTREAM_MAKE_CHECK_RC="):
                rc = int(ln.split("=", 1)[1])
        unrun = [n for n in declared if n not in resolved]
        summary = (f"upstream check: rc={rc} group_rcs={group_rcs} groups={len(groups)} "
                   f"test_rows={len(declared)} result_rows={len(resolved)} "
                   f"fail_rows={fail_cells} ok_cells={ok_cells} unrun={unrun}")
        self.output.info(summary)

        problems = []
        if fail_cells or "FAILED!" in content:
            problems.append("存在失败用例（日志含 FAILED!/fail 单元格）")
        if rc != 0:
            problems.append(f"make check 退出码 {rc}")
        if not groups:
            problems.append("未发现测试分组（日志无 '# <GROUP>' 头）")
        if not resolved:
            problems.append("零结果行（测试未真正执行）")
        unexpected = [n for n in unrun if n not in UPSTREAM_DISABLED_TESTS]
        if unexpected:
            problems.append(f"存在未申报的未执行用例：{unexpected}")
        if problems:
            for g, _d, part in parts:
                if group_rcs.get(g):
                    self.output.error(f"---- {g} 组日志尾部（RC={group_rcs[g]}）----")
                    self.run(f'tail -n 60 "{part}"')
            raise ConanException(f"上游测试未全部通过：{'; '.join(problems)}；日志见 {log}")

    # ---------------------------------------------------------------- package

    def package(self):
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

        # 上游 make install 用 coreutils install(1) 落盘，OHOS 无该工具 → 自行落盘
        for tool in ("ol", "olvm"):
            copy(self, tool, self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "libol.so", self.source_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", os.path.join(self.source_folder, "includes", "ol"),
             os.path.join(self.package_folder, "include", "ol"))

        # Ol 标准库 + REPL fasl（运行期 OL_HOME 指向 <prefix>/lib/ol）
        ol_home = os.path.join(self.package_folder, "lib", "ol")
        copy(self, "*", os.path.join(self.source_folder, "libraries"), ol_home)
        copy(self, "repl", self.source_folder, ol_home)

        # man page：上游 install 用 gzip 压缩，这里用 mtime=0 保证可复现
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(man_dir, exist_ok=True)
        with open(os.path.join(self.source_folder, "ol.1"), "rb") as f:
            with open(os.path.join(man_dir, "ol.1.gz"), "wb") as out:
                out.write(gzip.compress(f.read(), mtime=0))

        self._sign_binaries()

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        """鸿蒙 PC 要求可执行文件带有效代码签名。

        上游 olvm 目标链接后 strip，签名节被剥离 → 执行报 EPERM（rc=126）。
        这里对 bin/ 下的 ELF 统一重新自签名；libol.so **不重签**（hnp clang
        产物自带链接器签名，对 .so 重签会让本机 musl 加载器 SIGSEGV）。

        ⚠️ 必须清空 LD_LIBRARY_PATH：conanbuild 环境把 OHOS 目标 sysroot 的
        `.../llvm/lib/aarch64-linux-ohos` 放在最前，那里有**目标机** libc++.so，
        会遮蔽 binary-sign-tool 需要的宿主 libc++，表现为
        `Error loading shared library libc++.so` + 一串 `Error relocating ... symbol not found`。
        """
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        # 优先用 PATH 上的同名工具，退回 hnp 固定安装路径（OHOS 设备与 CI worker）。
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            # 不静默跳过：OHOS 上缺少签名工具会让 strip 后的 bin/olvm 无法执行，
            # 属必须暴露的环境缺陷；非 OHOS 宿主不需要签名（仅供 Linux 上验证配方）。
            if str(self.settings.os) == "OHOS":
                raise ConanException(
                    "OHOS 构建缺少 llvm-objcopy/binary-sign-tool：strip 后的 bin/olvm 将无法执行"
                )
            self.output.warning("缺少 llvm-objcopy/binary-sign-tool，跳过 ELF 重新签名（非 OHOS 宿主）")
            return
        for name in sorted(os.listdir(bindir)):
            path = os.path.join(bindir, name)
            if not os.path.isfile(path) or os.path.islink(path) or not self._is_elf(path):
                continue
            # 上游链接器签名已随 strip 失效，先删旧段再重签（binary-sign-tool 不能覆盖已有段）；
            # 没有旧段时 objcopy 报错属预期，故吞掉该步的输出与退出码。
            self.run(f'LD_LIBRARY_PATH= {objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'LD_LIBRARY_PATH= {signer} sign -inFile "{path}" -outFile "{path}" -selfSign 1')

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["ol"]
        # 编译期 PREFIX 是上游默认 /usr；用环境变量把运行期库路径指向包内，
        # 使包在缓存/任意前缀下都可重定位使用。
        ol_home = os.path.join(self.package_folder, "lib", "ol")
        self.runenv_info.define_path("OL_HOME", ol_home)
        self.buildenv_info.define_path("OL_HOME", ol_home)
